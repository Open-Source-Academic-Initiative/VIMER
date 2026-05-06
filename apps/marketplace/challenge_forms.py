from django import forms

from apps.marketplace.models import ChallengeCategory
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
            "Usa una línea por criterio."
        ),
    )
    application_deadline = forms.DateField(
        required=False,
        label="Fecha límite para recibir propuestas",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    categories = forms.ModelMultipleChoiceField(
        queryset=ChallengeCategory.objects.filter(is_active=True),
        label="Categorías",
    )
    attachments = MultipleFileField(
        required=False,
        label="Adjuntos del desafío (PDF, JPG o PNG)",
    )

    def to_command(self) -> PublishChallengeCommand:
        return PublishChallengeCommand(
            title=self.cleaned_data["title"],
            description=self.cleaned_data["description"],
            evaluation_criteria=self.cleaned_data["evaluation_criteria"],
            application_deadline=self.cleaned_data.get("application_deadline"),
            category_ids=tuple(
                self.cleaned_data["categories"].values_list("pk", flat=True)
            ),
            attachments=tuple(self.cleaned_data.get("attachments") or ()),
        )
