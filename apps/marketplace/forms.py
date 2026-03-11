from django import forms

from apps.marketplace.application.commands import (
    PublishChallengeCommand,
    SubmitApplicationCommand,
)


class ChallengePublicationForm(forms.Form):
    title = forms.CharField(max_length=255, label="Título del Desafío")
    description = forms.CharField(
        widget=forms.Textarea,
        label="Descripción del Reto / Necesidad",
    )

    def to_command(self) -> PublishChallengeCommand:
        return PublishChallengeCommand(
            title=self.cleaned_data["title"],
            description=self.cleaned_data["description"],
        )


class ApplicationSubmissionForm(forms.Form):
    proposal_text = forms.CharField(
        widget=forms.Textarea,
        label="Propuesta Tecnológica / Solución",
    )

    def to_command(self) -> SubmitApplicationCommand:
        return SubmitApplicationCommand(
            proposal_text=self.cleaned_data["proposal_text"],
        )
