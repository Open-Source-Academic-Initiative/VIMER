from django import forms

from apps.evaluation.application.commands import (
    AwardDecisionCommand,
    CriterionAssessmentInput,
    EvaluateApplicationCommand,
)
from apps.evaluation.application.queries import (
    build_challenge_application_evaluation_summaries,
)
from apps.evaluation.models import ApplicationCriterionEvaluation
from apps.marketplace.models import Application, Challenge


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
        self.fields["winning_application"].queryset = challenge.applications.select_related(
            "applicant"
        ).filter(
            pk__in=self.eligible_application_ids
        )
        self.fields["winning_application"].help_text = (
            "Solo aparecen propuestas con todos los criterios evaluados."
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
