from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.marketplace.models import (
    Application,
    Challenge,
    ChallengeEvaluationCriterion,
)


class AwardDecision(models.Model):
    challenge = models.OneToOneField(
        Challenge,
        on_delete=models.CASCADE,
        related_name="award_decision",
    )
    winning_application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="award_decisions",
    )
    comment = models.TextField(_("Comentario de adjudicación"))
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="award_decisions",
    )
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Decisión de adjudicación")
        verbose_name_plural = _("Decisiones de adjudicación")
        ordering = ["-decided_at"]

    def clean(self):
        errors = {}

        if self.winning_application_id and self.challenge_id:
            if self.winning_application.challenge_id != self.challenge_id:
                errors["winning_application"] = _(
                    "La propuesta seleccionada debe pertenecer al mismo desafío."
                )

        if not (self.comment or "").strip():
            errors["comment"] = _("Debes registrar un comentario de adjudicación.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Adjudicación de {self.challenge}"


class ChallengeTimelineEntry(models.Model):
    class EventType(models.TextChoices):
        EVALUATION_STARTED = "EVALUATION_STARTED", _("Evaluación iniciada")
        CHALLENGE_AWARDED = "CHALLENGE_AWARDED", _("Desafío adjudicado")

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="timeline_entries",
    )
    event_type = models.CharField(
        _("Tipo de evento"),
        max_length=32,
        choices=EventType.choices,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="challenge_timeline_entries",
    )
    award_decision = models.ForeignKey(
        AwardDecision,
        on_delete=models.SET_NULL,
        related_name="timeline_entries",
        null=True,
        blank=True,
    )
    description = models.CharField(_("Descripción"), max_length=255)
    occurred_at = models.DateTimeField(_("Fecha del evento"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Evento de historial del desafío")
        verbose_name_plural = _("Eventos de historial del desafío")
        ordering = ["-occurred_at", "-id"]

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.challenge}"


class ApplicationCriterionEvaluation(models.Model):
    class Score(models.IntegerChoices):
        VERY_WEAK = 1, _("1 - Muy débil")
        WEAK = 2, _("2 - Débil")
        ACCEPTABLE = 3, _("3 - Aceptable")
        STRONG = 4, _("4 - Fuerte")
        OUTSTANDING = 5, _("5 - Sobresaliente")

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="criterion_evaluations",
    )
    criterion = models.ForeignKey(
        ChallengeEvaluationCriterion,
        on_delete=models.CASCADE,
        related_name="application_evaluations",
    )
    score = models.PositiveSmallIntegerField(
        _("Puntaje"),
        choices=Score.choices,
    )
    comment = models.TextField(_("Comentario de evaluación"))
    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="application_criterion_evaluations",
    )
    evaluated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Evaluación de criterio")
        verbose_name_plural = _("Evaluaciones de criterio")
        ordering = ["criterion__position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "criterion"],
                name="unique_application_evaluation_per_criterion",
            ),
        ]

    def clean(self):
        errors = {}

        if self.application_id and self.criterion_id:
            if self.application.challenge_id != self.criterion.challenge_id:
                errors["criterion"] = _(
                    "El criterio evaluado debe pertenecer al mismo desafío de la propuesta."
                )

        if not (self.comment or "").strip():
            errors["comment"] = _("Debes registrar un comentario para cada criterio evaluado.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.application} - {self.criterion}"
