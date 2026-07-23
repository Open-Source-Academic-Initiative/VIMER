from django import forms
from django.db.models import Case, IntegerField, Value, When
from django.contrib.auth import get_user_model

from apps.evaluation.domain.blind_references import (
    build_challenge_application_blind_reference_map,
)
from apps.evaluation.application.commands import (
    AssignChallengeEvaluationRolesCommand,
    AwardDecisionCommand,
    CriterionAssessmentInput,
    EvaluateApplicationCommand,
)
from apps.evaluation.application.queries import (
    build_challenge_application_evaluation_summaries,
    build_pending_award_messages,
)
from apps.evaluation.models import (
    ApplicationCriterionEvaluation,
    AwardDecision,
    ChallengeEvaluationRoleAssignment,
)
from apps.marketplace.models import Application, Challenge


class BlindApplicationChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, blind_reference_map: dict[int, str], **kwargs):
        self.blind_reference_map = blind_reference_map
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        return self.blind_reference_map.get(obj.pk, f"Propuesta #{obj.pk}")


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
        member_queryset = (
            get_user_model()
            .objects.operational_members_of(challenge.publisher_id)
            .order_by("username")
        )
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
    exceptional_reason = forms.ChoiceField(
        choices=(("", "---------"), *AwardDecision.ExceptionalReason.choices),
        required=False,
        label="Motivo estructurado de adjudicación excepcional",
    )
    confirm_exceptional_selection = forms.BooleanField(
        required=False,
        label="Confirmo que deseo adjudicar fuera del mejor lugar disponible",
    )
    confirm_award = forms.BooleanField(
        required=True,
        label=(
            "Confirmo que revisé el ranking, la propuesta seleccionada y que "
            "la decisión quedará registrada"
        ),
    )
    comment = forms.CharField(
        widget=forms.Textarea,
        label="Comentario de adjudicación",
    )

    def __init__(self, *args, challenge: Challenge, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge = challenge
        self.evaluation_summaries = build_challenge_application_evaluation_summaries(
            challenge,
            reveal_applicant_identity=False,
        )
        self.complete_evaluation_summaries = tuple(
            application
            for application in self.evaluation_summaries
            if application.evaluation_summary.is_complete
        )
        self.pending_evaluation_summaries = tuple(
            application
            for application in self.evaluation_summaries
            if not application.evaluation_summary.is_complete
        )
        self.best_available_summaries = tuple(
            application
            for application in self.complete_evaluation_summaries
            if application.evaluation_summary.ranking_position == 1
        )
        self.pending_award_messages = build_pending_award_messages(
            self.evaluation_summaries
        )
        self.is_award_blocked = bool(self.pending_award_messages)
        blind_reference_map = build_challenge_application_blind_reference_map(challenge)
        self.eligible_application_ids = [
            application.pk
            for application in self.complete_evaluation_summaries
        ]
        self.best_available_application_ids = {
            application.pk for application in self.best_available_summaries
        }
        self.summary_by_application_id = {
            application.pk: application.evaluation_summary
            for application in self.evaluation_summaries
        }
        eligible_queryset = challenge.applications.none()
        if self.eligible_application_ids:
            eligible_queryset = (
                challenge.applications.submitted().filter(
                    pk__in=self.eligible_application_ids
                )
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
        self.fields["winning_application"] = BlindApplicationChoiceField(
            queryset=eligible_queryset,
            label="Propuesta ganadora",
            blind_reference_map=blind_reference_map,
        )
        self.order_fields(
            [
                "winning_application",
                "exceptional_reason",
                "confirm_exceptional_selection",
                "comment",
                "confirm_award",
            ]
        )
        self.fields["winning_application"].help_text = (
            "Solo aparecen propuestas con cobertura completa. La adjudicación seguirá usando referencias ciegas hasta que se registre la decisión."
        )
        self.fields["exceptional_reason"].help_text = (
            "Solo es obligatorio si decides adjudicar una propuesta fuera del mejor lugar disponible."
        )
        self.fields["confirm_exceptional_selection"].help_text = (
            "Debes marcarlo para confirmar una adjudicación excepcional fuera del mejor lugar disponible."
        )

    def clean(self):
        cleaned_data = super().clean()
        winning_application = cleaned_data.get("winning_application")

        if self.pending_award_messages:
            for message in self.pending_award_messages:
                self.add_error(None, message)
            return cleaned_data

        if not self.complete_evaluation_summaries:
            self.add_error(
                None,
                "No hay propuestas con cobertura completa disponibles para adjudicar.",
            )
            return cleaned_data

        if winning_application is None:
            return cleaned_data

        if winning_application.pk not in self.best_available_application_ids:
            if not cleaned_data.get("confirm_exceptional_selection"):
                self.add_error(
                    "confirm_exceptional_selection",
                    (
                        "Debes confirmar explícitamente que deseas adjudicar fuera "
                        "del mejor lugar disponible."
                    ),
                )
            if not cleaned_data.get("exceptional_reason"):
                self.add_error(
                    "exceptional_reason",
                    (
                        "Debes registrar un motivo estructurado para adjudicar "
                        "fuera del mejor lugar disponible."
                    ),
                )

        return cleaned_data

    def to_command(self) -> AwardDecisionCommand:
        return AwardDecisionCommand(
            winning_application_id=self.cleaned_data["winning_application"].pk,
            comment=self.cleaned_data["comment"],
            exceptional_reason=self.cleaned_data["exceptional_reason"],
            confirm_exceptional_selection=self.cleaned_data[
                "confirm_exceptional_selection"
            ],
        )


class ApplicationCriterionEvaluationForm(forms.Form):
    def __init__(
        self,
        *args,
        challenge: Challenge,
        application: Application,
        evaluator,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.challenge = challenge
        self.application = application
        self.evaluator = evaluator
        criteria = challenge.evaluation_criteria_items.order_by("position")
        existing_evaluations = {
            evaluation.criterion_id: evaluation
            for evaluation in application.criterion_evaluations.select_related("criterion").filter(
                evaluated_by=evaluator
            )
        }

        for criterion in criteria:
            existing = existing_evaluations.get(criterion.pk)
            score_field_name = f"score_{criterion.pk}"
            comment_field_name = f"comment_{criterion.pk}"
            self.fields[score_field_name] = forms.ChoiceField(
                choices=ApplicationCriterionEvaluation.Score.choices,
                label=f"{criterion.label} - puntaje",
                initial=str(existing.score) if existing else "",
                widget=forms.Select(
                    attrs={
                        "aria-describedby": (
                            f"id_{score_field_name}_help "
                            f"id_{score_field_name}_errors"
                        )
                    }
                ),
            )
            self.fields[score_field_name].help_text = (
                f"Peso: {criterion.weight} %."
            )
            if (
                criterion.criterion_type
                == criterion.CriterionType.ECONOMIC
                and application.offered_amount is not None
            ):
                self.fields[score_field_name].help_text += (
                    " Oferta estructurada: "
                    f"{application.offered_amount} {application.offer_currency}; "
                    "presupuesto máximo: "
                    f"{challenge.budget_amount} {challenge.budget_currency}."
                )
            self.fields[comment_field_name] = forms.CharField(
                widget=forms.Textarea(
                    attrs={
                        "aria-describedby": (
                            f"id_{comment_field_name}_help "
                            f"id_{comment_field_name}_errors"
                        )
                    }
                ),
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
