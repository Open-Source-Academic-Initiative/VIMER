from django import forms

from apps.marketplace.application.commands import SubmitApplicationCommand


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
