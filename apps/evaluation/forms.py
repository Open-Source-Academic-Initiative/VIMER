from django import forms
from django.db.models import Case, IntegerField, Value, When
from django.contrib.auth import get_user_model

from apps.evaluation.application.commands import (
    AssignChallengeEvaluationRolesCommand,
    AwardDecisionCommand,
    CriterionAssessmentInput,
    EvaluateApplicationCommand,
)
from apps.evaluation.application.queries import (
    build_challenge_application_evaluation_summaries,
)
from apps.evaluation.models import ApplicationCriterionEvaluation
from apps.evaluation.models import ChallengeEvaluationRoleAssignment
from apps.marketplace.models import Application, Challenge


class ChallengeEvaluationRoleAssignmentForm(forms.Form):
    evaluator_users = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.none(),
        label="Evaluadores designados",
    )
    adjudicator_user = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        label="Adjudicador designado",
    )
    observer_users = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.none(),
        label="Observadores de evaluación",
        required=False,
    )

    def __init__(self, *args, challenge: Challenge, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge = challenge
        member_queryset = challenge.publisher.members.order_by("username")
        current_assignments = challenge.evaluation_role_assignments.all()
        evaluator_ids = list(
            current_assignments.filter(
                role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR
            ).values_list("user_id", flat=True)
        )
        adjudicator_id = current_assignments.filter(
            role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR
        ).values_list("user_id", flat=True).first()
        observer_ids = list(
            current_assignments.filter(
                role=ChallengeEvaluationRoleAssignment.Role.OBSERVER
            ).values_list("user_id", flat=True)
        )

        self.fields["evaluator_users"].queryset = member_queryset
        self.fields["adjudicator_user"].queryset = member_queryset
        self.fields["observer_users"].queryset = member_queryset
        self.fields["evaluator_users"].initial = evaluator_ids
        self.fields["adjudicator_user"].initial = adjudicator_id
        self.fields["observer_users"].initial = observer_ids
        self.fields["observer_users"].help_text = (
            "Los observadores pueden seguir el proceso, pero no evaluar ni adjudicar."
        )

    def to_command(self) -> AssignChallengeEvaluationRolesCommand:
        return AssignChallengeEvaluationRolesCommand(
            evaluator_user_ids=tuple(
                self.cleaned_data["evaluator_users"].values_list("pk", flat=True)
            ),
            adjudicator_user_id=self.cleaned_data["adjudicator_user"].pk,
            observer_user_ids=tuple(
                self.cleaned_data["observer_users"].values_list("pk", flat=True)
            ),
        )


class AwardDecisionForm(forms.Form):
    winning_application = forms.ModelChoiceField(
        queryset=Application.objects.none(),
        label="Propuesta ganadora",
    )
    comment = forms.CharField(
        widget=forms.Textarea,
        label="Comentario de adjudicación",
    )

    def __init__(self, *args, challenge: Challenge, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge = challenge
        self.evaluation_summaries = build_challenge_application_evaluation_summaries(
            challenge
        )
        self.eligible_application_ids = [
            application.pk
            for application in self.evaluation_summaries
            if application.evaluation_summary.is_complete
        ]
        eligible_queryset = challenge.applications.none()
        if self.eligible_application_ids:
            eligible_queryset = (
                challenge.applications.select_related("applicant")
                .filter(pk__in=self.eligible_application_ids)
                .order_by(
                    Case(
                        *[
                            When(pk=application_id, then=Value(position))
                            for position, application_id in enumerate(
                                self.eligible_application_ids,
                                start=1,
                            )
                        ],
                        output_field=IntegerField(),
                    )
                )
            )
        self.fields["winning_application"].queryset = eligible_queryset
        self.fields["winning_application"].help_text = (
            "Solo aparecen propuestas con todos los criterios evaluados y se listan según el ranking actual."
        )

    def to_command(self) -> AwardDecisionCommand:
        return AwardDecisionCommand(
            winning_application_id=self.cleaned_data["winning_application"].pk,
            comment=self.cleaned_data["comment"],
        )


class ApplicationCriterionEvaluationForm(forms.Form):
    def __init__(self, *args, challenge: Challenge, application: Application, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge = challenge
        self.application = application
        self.challenge.sync_evaluation_criteria_items()
        criteria = challenge.evaluation_criteria_items.order_by("position")
        existing_evaluations = {
            evaluation.criterion_id: evaluation
            for evaluation in application.criterion_evaluations.select_related("criterion")
        }

        for criterion in criteria:
            existing = existing_evaluations.get(criterion.pk)
            score_field_name = f"score_{criterion.pk}"
            comment_field_name = f"comment_{criterion.pk}"
            self.fields[score_field_name] = forms.ChoiceField(
                choices=ApplicationCriterionEvaluation.Score.choices,
                label=f"{criterion.label} - puntaje",
                initial=str(existing.score) if existing else "",
            )
            self.fields[comment_field_name] = forms.CharField(
                widget=forms.Textarea,
                label=f"{criterion.label} - comentario",
                initial=existing.comment if existing else "",
            )

    def criteria(self):
        return self.challenge.evaluation_criteria_items.order_by("position")

    def to_command(self) -> EvaluateApplicationCommand:
        assessments = []
        for criterion in self.criteria():
            assessments.append(
                CriterionAssessmentInput(
                    criterion_id=criterion.pk,
                    score=int(self.cleaned_data[f"score_{criterion.pk}"]),
                    comment=self.cleaned_data[f"comment_{criterion.pk}"],
                )
            )

        return EvaluateApplicationCommand(
            application_id=self.application.pk,
            assessments=tuple(assessments),
        )
