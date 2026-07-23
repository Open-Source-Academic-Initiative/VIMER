from django import forms

from apps.marketplace.application.commands import (
    SaveApplicationDraftCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.challenge_forms import MultipleFileField
from apps.marketplace.models import Challenge


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
    offered_amount = forms.DecimalField(
        required=False,
        min_value=0.01,
        max_digits=18,
        decimal_places=2,
        label="Valor total ofertado",
    )
    offer_currency = forms.ChoiceField(
        choices=(("", "---------"), *Challenge.Currency.choices),
        required=False,
        label="Moneda de la oferta",
    )
    estimated_duration_days = forms.IntegerField(
        required=False,
        min_value=1,
        label="Duración estimada de ejecución (días)",
    )
    confirm_submission = forms.BooleanField(
        required=False,
        label=(
            "Confirmo que revisé la propuesta y entiendo que el envío será "
            "inmutable"
        ),
    )
    attachments = MultipleFileField(
        required=False,
        label="Adjuntos de la propuesta (PDF, JPG o PNG)",
    )

    def __init__(
        self,
        *args,
        challenge=None,
        submission_intent: str = "submit",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.challenge = challenge
        self.submission_intent = submission_intent
        if challenge is not None and challenge.budget_amount is not None:
            self.fields["offered_amount"].help_text = (
                f"Debe ser igual o inferior a {challenge.budget_amount} "
                f"{challenge.budget_currency}."
            )
            self.fields["offer_currency"].initial = challenge.budget_currency

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
        if self.challenge is not None and self.challenge.budget_amount is not None:
            offered_amount = cleaned_data.get("offered_amount")
            offer_currency = cleaned_data.get("offer_currency")
            if offered_amount is None:
                self.add_error(
                    "offered_amount",
                    "Debes indicar el valor total de la oferta.",
                )
            elif offered_amount > self.challenge.budget_amount:
                self.add_error(
                    "offered_amount",
                    "El valor total ofertado no puede superar el presupuesto máximo del desafío.",
                )
            if offer_currency != self.challenge.budget_currency:
                self.add_error(
                    "offer_currency",
                    "La moneda de la oferta debe coincidir con la moneda del presupuesto.",
                )
            if not cleaned_data.get("estimated_duration_days"):
                self.add_error(
                    "estimated_duration_days",
                    "Debes indicar la duración estimada de ejecución.",
                )
        if not cleaned_data.get("confirm_submission"):
            self.add_error(
                "confirm_submission",
                "Debes confirmar el envío inmutable de la propuesta.",
            )
        return cleaned_data

    def to_draft_command(self) -> SaveApplicationDraftCommand:
        return SaveApplicationDraftCommand(
            problem_understanding=self.cleaned_data["problem_understanding"],
            proposed_solution=self.cleaned_data["proposed_solution"],
            capabilities_evidence=self.cleaned_data["capabilities_evidence"],
            execution_plan=self.cleaned_data["execution_plan"],
            offered_amount=self.cleaned_data.get("offered_amount"),
            offer_currency=self.cleaned_data.get("offer_currency") or "",
            estimated_duration_days=self.cleaned_data.get("estimated_duration_days"),
            attachments=tuple(self.cleaned_data.get("attachments") or ()),
        )

    def to_command(self) -> SubmitApplicationCommand:
        return SubmitApplicationCommand(
            problem_understanding=self.cleaned_data["problem_understanding"],
            proposed_solution=self.cleaned_data["proposed_solution"],
            capabilities_evidence=self.cleaned_data["capabilities_evidence"],
            execution_plan=self.cleaned_data["execution_plan"],
            offered_amount=self.cleaned_data.get("offered_amount"),
            offer_currency=self.cleaned_data.get("offer_currency") or "",
            estimated_duration_days=self.cleaned_data.get("estimated_duration_days"),
            attachments=tuple(self.cleaned_data.get("attachments") or ()),
        )
