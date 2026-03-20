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
    evaluation_criteria = forms.CharField(
        widget=forms.Textarea,
        label="Criterios de evaluación",
        help_text="Describe cómo se evaluarán las propuestas para este desafío. Usa una línea por criterio.",
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


class ApplicationSubmissionForm(forms.Form):
    problem_understanding = forms.CharField(
        widget=forms.Textarea,
        label="Entendimiento del problema",
    )
    proposed_solution = forms.CharField(
        widget=forms.Textarea,
        label="Solución propuesta",
    )
    capabilities_evidence = forms.CharField(
        widget=forms.Textarea,
        label="Capacidades y evidencia",
    )
    execution_plan = forms.CharField(
        widget=forms.Textarea,
        label="Plan de ejecución",
    )

    def to_command(self) -> SubmitApplicationCommand:
        return SubmitApplicationCommand(
            problem_understanding=self.cleaned_data["problem_understanding"],
            proposed_solution=self.cleaned_data["proposed_solution"],
            capabilities_evidence=self.cleaned_data["capabilities_evidence"],
            execution_plan=self.cleaned_data["execution_plan"],
        )
