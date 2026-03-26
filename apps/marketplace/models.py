from django.db import models
from django.db.models import UniqueConstraint
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.corporate.models import Organization


class ChallengeQuerySet(models.QuerySet):
    def visible_to_organization(self, organization: Organization | None):
        public_statuses = Challenge.publicly_visible_statuses()
        if organization is None:
            return self.filter(status__in=public_statuses)

        return self.filter(
            models.Q(status__in=public_statuses)
            | models.Q(publisher=organization)
        ).distinct()


class Challenge(models.Model):
    """
    R&D&I challenge published by a solicitante organization.
    """
    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Borrador")
        PUBLISHED = "PUBLISHED", _("Publicado")
        CLOSED = "CLOSED", _("Cerrado")
        UNDER_EVALUATION = "UNDER_EVALUATION", _("En evaluación")
        AWARDED = "AWARDED", _("Adjudicado")
        ARCHIVED = "ARCHIVED", _("Archivado")

    objects = ChallengeQuerySet.as_manager()

    publisher = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="published_challenges",
        limit_choices_to={'role': Organization.MarketRole.DEMAND_SIDE}
    )
    title = models.CharField(_("Título del Desafío"), max_length=255)
    description = models.TextField(_("Descripción del Reto / Necesidad"))
    evaluation_criteria = models.TextField(
        _("Criterios de evaluación"),
        blank=True,
        default="",
    )
    status = models.CharField(
        _("Estado"),
        max_length=24,
        choices=Status.choices,
        default=Status.PUBLISHED,
    )
    application_deadline = models.DateField(
        _("Fecha límite de aplicación"),
        null=True,
        blank=True,
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Desafío")
        verbose_name_plural = _("Desafíos")
        ordering = ['-created_at']

    def clean(self):
        errors = {}

        if self.publisher and self.publisher.role != Organization.MarketRole.DEMAND_SIDE:
            errors["publisher"] = _(
                "Solo las organizaciones con rol Solicitante pueden publicar desafíos."
            )

        if (
            self.status == self.Status.PUBLISHED
            and self.application_deadline
            and self.application_deadline < timezone.localdate()
        ):
            errors["application_deadline"] = _(
                "La fecha límite de aplicación no puede estar en el pasado para un desafío publicado."
            )

        if errors:
            raise ValidationError(errors)

    def is_open_for_applications(self) -> bool:
        if self.status != self.Status.PUBLISHED:
            return False

        if self.application_deadline and self.application_deadline < timezone.localdate():
            return False

        return True

    def has_evaluation_criteria(self) -> bool:
        return bool(self._parse_evaluation_criteria_text())

    def evaluation_criteria_list(self) -> list[str]:
        parsed_items = self._parse_evaluation_criteria_text()
        if parsed_items:
            return parsed_items

        return list(
            self.evaluation_criteria_items.order_by("position").values_list(
                "label",
                flat=True,
            )
        )

    def sync_evaluation_criteria_items(self) -> None:
        if self.pk is None:
            return

        desired_items = self._parse_evaluation_criteria_text()
        existing_items = {
            item.position: item
            for item in self.evaluation_criteria_items.all()
        }

        if not desired_items:
            self.evaluation_criteria_items.all().delete()
            return

        items_to_create = []
        items_to_update = []

        for position, label in enumerate(desired_items, start=1):
            existing_item = existing_items.get(position)
            if existing_item is None:
                items_to_create.append(
                    ChallengeEvaluationCriterion(
                        challenge=self,
                        label=label,
                        position=position,
                    )
                )
                continue

            if existing_item.label != label:
                existing_item.label = label
                items_to_update.append(existing_item)

        stale_positions = set(existing_items) - set(range(1, len(desired_items) + 1))
        if stale_positions:
            self.evaluation_criteria_items.filter(position__in=stale_positions).delete()

        if items_to_update:
            ChallengeEvaluationCriterion.objects.bulk_update(items_to_update, ["label"])

        if items_to_create:
            ChallengeEvaluationCriterion.objects.bulk_create(items_to_create)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        original_evaluation_criteria = ""
        if not is_new:
            original_evaluation_criteria = (
                Challenge.objects.filter(pk=self.pk)
                .values_list("evaluation_criteria", flat=True)
                .first()
                or ""
            )

        self.full_clean()
        super().save(*args, **kwargs)
        if is_new or (self.evaluation_criteria or "") != original_evaluation_criteria:
            self.sync_evaluation_criteria_items()

    def __str__(self):
        return self.title

    @classmethod
    def publicly_visible_statuses(cls) -> tuple[str, ...]:
        return (
            cls.Status.PUBLISHED,
            cls.Status.CLOSED,
            cls.Status.UNDER_EVALUATION,
            cls.Status.AWARDED,
        )

    def _parse_evaluation_criteria_text(self) -> list[str]:
        return [
            line.lstrip("-*0123456789. ").strip()
            for line in (self.evaluation_criteria or "").splitlines()
            if line.strip()
        ]


class ChallengeEvaluationCriterion(models.Model):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="evaluation_criteria_items",
    )
    label = models.CharField(_("Criterio"), max_length=255)
    position = models.PositiveIntegerField(_("Posición"))

    class Meta:
        verbose_name = _("Criterio de evaluación")
        verbose_name_plural = _("Criterios de evaluación")
        ordering = ["position", "id"]
        constraints = [
            UniqueConstraint(
                fields=["challenge", "position"],
                name="unique_evaluation_criterion_position_per_challenge",
            ),
        ]

    def __str__(self):
        return f"{self.challenge}: {self.label}"

class Application(models.Model):
    """
    Proposal submitted by a proveedor tecnológico organization for a challenge.
    """
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="applications"
    )
    applicant = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="submitted_proposals",
        limit_choices_to={'role': Organization.MarketRole.SUPPLY_SIDE}
    )
    proposal_text = models.TextField(_("Resumen legado de propuesta"), blank=True, default="")
    problem_understanding = models.TextField(
        _("Entendimiento del problema"),
        blank=True,
        default="",
    )
    proposed_solution = models.TextField(
        _("Solución propuesta"),
        blank=True,
        default="",
    )
    capabilities_evidence = models.TextField(
        _("Capacidades y evidencia"),
        blank=True,
        default="",
    )
    execution_plan = models.TextField(
        _("Plan de ejecución"),
        blank=True,
        default="",
    )
    
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Postulación")
        verbose_name_plural = _("Postulaciones")
        constraints = [
            UniqueConstraint(
                fields=["challenge", "applicant"],
                name="unique_application_per_challenge_and_applicant",
            ),
        ]

    def clean(self):
        errors = {}

        if self.applicant and self.applicant.role != Organization.MarketRole.SUPPLY_SIDE:
            errors["applicant"] = _(
                "Solo las organizaciones con rol Proveedor tecnológico pueden aplicar a desafíos."
            )

        if self.challenge and not self.challenge.is_open_for_applications():
            errors["challenge"] = _(
                "Este desafío no está abierto para recibir propuestas."
            )

        required_components = {
            "problem_understanding": self.problem_understanding,
            "proposed_solution": self.proposed_solution,
            "capabilities_evidence": self.capabilities_evidence,
            "execution_plan": self.execution_plan,
        }
        for field_name, value in required_components.items():
            if not (value or "").strip():
                errors[field_name] = _("Este campo es obligatorio para enviar la propuesta.")

        if self.pk:
            original = Application.objects.filter(pk=self.pk).first()
            if original is not None:
                immutable_fields = (
                    "challenge_id",
                    "applicant_id",
                    "proposal_text",
                    "problem_understanding",
                    "proposed_solution",
                    "capabilities_evidence",
                    "execution_plan",
                )
                if any(
                    getattr(original, field_name) != getattr(self, field_name)
                    for field_name in immutable_fields
                ):
                    errors["__all__"] = _(
                        "Una propuesta enviada no puede modificarse después del envío."
                    )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def summary_text(self) -> str:
        return self.proposed_solution or self.proposal_text

    def __str__(self):
        return f"Propuesta de {self.applicant} para {self.challenge}"
