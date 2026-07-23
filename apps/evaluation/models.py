from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.marketplace.models import (
    Application,
    Challenge,
    ChallengeEvaluationCriterion,
)


class ChallengeEvaluationRoleAssignment(models.Model):
    class Role(models.TextChoices):
        EVALUATOR = "EVALUATOR", _("Evaluador designado")
        ADJUDICATOR = "ADJUDICATOR", _("Adjudicador designado")
        OBSERVER = "OBSERVER", _("Observador de evaluación")

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="evaluation_role_assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenge_evaluation_role_assignments",
    )
    role = models.CharField(
        _("Rol de evaluación"),
        max_length=24,
        choices=Role.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Asignación de rol de evaluación")
        verbose_name_plural = _("Asignaciones de roles de evaluación")
        ordering = ["role", "user__username", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "user", "role"],
                name="unique_challenge_evaluation_role_assignment",
            ),
            models.UniqueConstraint(
                fields=["challenge", "role"],
                condition=Q(role="ADJUDICATOR"),
                name="unique_adjudicator_per_challenge",
            ),
        ]

    def clean(self):
        errors = {}

        if self.challenge_id and self.user_id:
            if not self.user.is_operational_member_of(self.challenge.publisher_id):
                errors["user"] = _(
                    "Los roles de evaluación solo pueden asignarse a miembros "
                    "operativos de la organización publicadora."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.challenge} - {self.get_role_display()} - {self.user.username}"


class AwardDecision(models.Model):
    class SelectionMode(models.TextChoices):
        BEST_RANKED = "BEST_RANKED", _("Alineada con el mejor lugar disponible")
        TIE_BREAK = "TIE_BREAK", _("Desempate humano en el mejor lugar")
        EXCEPTIONAL = "EXCEPTIONAL", _("Adjudicación excepcional")

    class ExceptionalReason(models.TextChoices):
        STRATEGIC_EXTERNAL_DECISION = (
            "DECISION_ESTRATEGICA_EXTERNA",
            _("Decisión estratégica externa"),
        )
        BUDGETARY_OR_CONTRACTUAL_RESTRICTION = (
            "RESTRICCION_PRESUPUESTAL_O_CONTRACTUAL",
            _("Restricción presupuestal o contractual"),
        )
        RISK_OUTSIDE_EVALUATION = (
            "RIESGO_NO_REFLEJADO_EN_EVALUACION",
            _("Riesgo no reflejado en la evaluación"),
        )
        INSTITUTIONAL_REQUIREMENT = (
            "CUMPLIMIENTO_O_REQUISITO_INSTITUCIONAL",
            _("Cumplimiento o requisito institucional"),
        )
        OTHER = "OTRO", _("Otro")

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
    winning_total_score = models.PositiveIntegerField(
        _("Puntaje total registrado al adjudicar"),
        null=True,
        blank=True,
    )
    winning_average_score = models.FloatField(
        _("Promedio registrado al adjudicar"),
        null=True,
        blank=True,
    )
    winning_evaluated_criteria_count = models.PositiveIntegerField(
        _("Cantidad de criterios evaluados al adjudicar"),
        null=True,
        blank=True,
    )
    winning_criteria_total = models.PositiveIntegerField(
        _("Cantidad total de criterios al adjudicar"),
        null=True,
        blank=True,
    )
    winning_assessment_count = models.PositiveIntegerField(
        _("Cantidad total de evaluaciones registradas al adjudicar"),
        null=True,
        blank=True,
    )
    winning_ranking_position = models.PositiveIntegerField(
        _("Posición comparativa registrada al adjudicar"),
        null=True,
        blank=True,
    )
    winning_eligible_ranking_position = models.PositiveIntegerField(
        _("Posición elegible registrada al adjudicar"),
        null=True,
        blank=True,
    )
    selection_mode = models.CharField(
        _("Modo de adjudicación"),
        max_length=16,
        choices=SelectionMode.choices,
        default=SelectionMode.BEST_RANKED,
    )
    exceptional_reason = models.CharField(
        _("Motivo estructurado de adjudicación excepcional"),
        max_length=48,
        choices=ExceptionalReason.choices,
        blank=True,
    )
    best_available_position = models.PositiveIntegerField(
        _("Mejor posición disponible registrada al adjudicar"),
        null=True,
        blank=True,
    )
    tied_best_application_count = models.PositiveIntegerField(
        _("Cantidad de propuestas empatadas en la mejor posición"),
        null=True,
        blank=True,
    )
    best_available_applications_snapshot = models.JSONField(
        _("Snapshot de propuestas en la mejor posición disponible"),
        default=list,
        blank=True,
    )
    higher_ranked_applications_snapshot = models.JSONField(
        _("Snapshot de propuestas con mejor posición que la adjudicada"),
        default=list,
        blank=True,
    )
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

        if (
            self.selection_mode == self.SelectionMode.EXCEPTIONAL
            and not self.exceptional_reason
        ):
            errors["exceptional_reason"] = _(
                "Debes registrar un motivo estructurado para una adjudicación excepcional."
            )

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
        APPLICATION_EVALUATED = "APPLICATION_EVALUATED", _("Propuesta evaluada")
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
        on_delete=models.PROTECT,
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
        ordering = ["criterion__position", "evaluated_by__username", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "criterion", "evaluated_by"],
                name="unique_application_evaluation_per_criterion_and_evaluator",
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
