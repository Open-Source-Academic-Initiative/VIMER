from django import forms

from apps.marketplace.application.commands import (
    SaveApplicationDraftCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.challenge_forms import MultipleFileField


class ApplicationSubmissionForm(forms.Form):
    problem_understanding = forms.CharField(
        widget=forms.Textarea,
        label="Entendimiento del problema",
        required=False,
    )
    proposed_solution = forms.CharField(
        widget=forms.Textarea,
        label="Solución propuesta",
        required=False,
    )
    capabilities_evidence = forms.CharField(
        widget=forms.Textarea,
        label="Capacidades y evidencia",
        required=False,
    )
    execution_plan = forms.CharField(
        widget=forms.Textarea,
        label="Plan de ejecución",
        required=False,
    )
    attachments = MultipleFileField(
        required=False,
        label="Adjuntos de la propuesta (PDF, JPG o PNG)",
    )

    def __init__(self, *args, submission_intent: str = "submit", **kwargs):
        super().__init__(*args, **kwargs)
        self.submission_intent = submission_intent

    def clean(self):
        cleaned_data = super().clean()
        if self.submission_intent != "submit":
            return cleaned_data

        for field_name in (
            "problem_understanding",
            "proposed_solution",
            "capabilities_evidence",
            "execution_plan",
        ):
            if not (cleaned_data.get(field_name) or "").strip():
                self.add_error(
                    field_name,
                    "Este campo es obligatorio para enviar la propuesta.",
                )
        return cleaned_data

    def to_draft_command(self) -> SaveApplicationDraftCommand:
        return SaveApplicationDraftCommand(
            problem_understanding=self.cleaned_data["problem_understanding"],
            proposed_solution=self.cleaned_data["proposed_solution"],
            capabilities_evidence=self.cleaned_data["capabilities_evidence"],
            execution_plan=self.cleaned_data["execution_plan"],
            attachments=tuple(self.cleaned_data.get("attachments") or ()),
        )

    def to_command(self) -> SubmitApplicationCommand:
        return SubmitApplicationCommand(
            problem_understanding=self.cleaned_data["problem_understanding"],
            proposed_solution=self.cleaned_data["proposed_solution"],
            capabilities_evidence=self.cleaned_data["capabilities_evidence"],
            execution_plan=self.cleaned_data["execution_plan"],
            attachments=tuple(self.cleaned_data.get("attachments") or ()),
        )
