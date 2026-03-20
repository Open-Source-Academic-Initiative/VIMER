from django import forms

from apps.evaluation.application.commands import AwardDecisionCommand
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
        self.fields["winning_application"].queryset = challenge.applications.select_related(
            "applicant"
        )

    def to_command(self) -> AwardDecisionCommand:
        return AwardDecisionCommand(
            winning_application_id=self.cleaned_data["winning_application"].pk,
            comment=self.cleaned_data["comment"],
        )
