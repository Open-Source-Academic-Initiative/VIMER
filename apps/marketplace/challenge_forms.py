from django import forms

from apps.marketplace.application.commands import PublishChallengeCommand


class ChallengePublicationForm(forms.Form):
    title = forms.CharField(max_length=255, label="Título del Desafío")
    description = forms.CharField(
        widget=forms.Textarea,
        label="Descripción del Reto / Necesidad",
    )
    evaluation_criteria = forms.CharField(
        widget=forms.Textarea,
        label="Criterios de evaluación",
        help_text=(
            "Describe cómo se evaluarán las propuestas para este desafío. "
            "Usa una línea por criterio."
        ),
    )
    application_deadline = forms.DateField(
        required=False,
        label="Fecha límite para recibir propuestas",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def to_command(self) -> PublishChallengeCommand:
        return PublishChallengeCommand(
            title=self.cleaned_data["title"],
            description=self.cleaned_data["description"],
            evaluation_criteria=self.cleaned_data["evaluation_criteria"],
            application_deadline=self.cleaned_data.get("application_deadline"),
        )
