from django import forms
from django.utils import timezone

from apps.marketplace.models import Challenge, ChallengeCategory
from apps.marketplace.application.commands import PublishChallengeCommand


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return ()
        if isinstance(data, (list, tuple)):
            return tuple(forms.FileField.clean(self, item, initial) for item in data)
        return (forms.FileField.clean(self, data, initial),)


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
            "Usa una línea por criterio. Puedes asignar pesos con el formato "
            "«Viabilidad técnica | 60»; deben sumar 100 %. Incluye un criterio "
            "económico como «Valor económico de la oferta»."
        ),
    )
    application_deadline = forms.DateField(
        required=True,
        label="Fecha límite para recibir propuestas",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    budget_amount = forms.DecimalField(
        required=True,
        min_value=0.01,
        max_digits=18,
        decimal_places=2,
        label="Presupuesto máximo",
    )
    budget_currency = forms.ChoiceField(
        choices=Challenge.Currency.choices,
        initial=Challenge.Currency.COP,
        label="Moneda del presupuesto",
    )
    categories = forms.ModelMultipleChoiceField(
        queryset=ChallengeCategory.objects.filter(is_active=True),
        label="Categorías",
    )
    attachments = MultipleFileField(
        required=False,
        label="Adjuntos del desafío (PDF, JPG o PNG)",
    )

    def clean_application_deadline(self):
        deadline = self.cleaned_data["application_deadline"]
        if deadline < timezone.localdate():
            raise forms.ValidationError(
                "La fecha límite de aplicación no puede estar en el pasado."
            )
        return deadline

    def to_command(self) -> PublishChallengeCommand:
        return PublishChallengeCommand(
            title=self.cleaned_data["title"],
            description=self.cleaned_data["description"],
            evaluation_criteria=self.cleaned_data["evaluation_criteria"],
            application_deadline=self.cleaned_data.get("application_deadline"),
            budget_amount=self.cleaned_data["budget_amount"],
            budget_currency=self.cleaned_data["budget_currency"],
            category_ids=tuple(
                self.cleaned_data["categories"].values_list("pk", flat=True)
            ),
            attachments=tuple(self.cleaned_data.get("attachments") or ()),
        )


class ChallengeTransitionForm(forms.Form):
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Motivo",
    )
    confirm = forms.BooleanField(
        required=True,
        label="Confirmo que revisé la transición y sus consecuencias",
    )

    def __init__(
        self,
        *args,
        reason_required: bool = False,
        reason_help_text: str = "",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["reason"].required = reason_required
        self.fields["reason"].help_text = reason_help_text
