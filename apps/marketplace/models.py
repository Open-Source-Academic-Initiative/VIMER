import mimetypes
import re
from decimal import Decimal, InvalidOperation, ROUND_DOWN

from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.corporate.models import Organization
from apps.marketplace.content import (
    build_application_summary,
    build_attachment_upload_path,
    new_opaque_id,
    render_markdown,
    sniff_attachment_content_type,
    validate_attachment_file,
)


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
        CANCELLED = "CANCELLED", _("Cancelado")
        DESERTED = "DESERTED", _("Desierto")
        ARCHIVED = "ARCHIVED", _("Archivado")

    class Currency(models.TextChoices):
        COP = "COP", _("Peso colombiano (COP)")
        USD = "USD", _("Dólar estadounidense (USD)")
        EUR = "EUR", _("Euro (EUR)")

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
        default=Status.DRAFT,
    )
    application_deadline = models.DateField(
        _("Fecha límite de aplicación"),
        null=True,
        blank=True,
    )
    budget_amount = models.DecimalField(
        _("Presupuesto máximo"),
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_(
            "Los registros históricos pueden no tener presupuesto. "
            "Toda nueva publicación debe definirlo."
        ),
    )
    budget_currency = models.CharField(
        _("Moneda del presupuesto"),
        max_length=3,
        choices=Currency.choices,
        default=Currency.COP,
    )
    categories = models.ManyToManyField(
        "marketplace.ChallengeCategory",
        related_name="challenges",
        blank=True,
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Desafío")
        verbose_name_plural = _("Desafíos")
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(budget_amount__isnull=True)
                    | models.Q(budget_amount__gt=0)
                ),
                name="challenge_budget_amount_positive_or_null",
            ),
        ]

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

        if self.budget_amount is not None and self.budget_amount <= 0:
            errors["budget_amount"] = _("El presupuesto debe ser mayor que cero.")

        try:
            criteria_specs = self._parse_evaluation_criteria_specs()
        except ValidationError as exc:
            errors["evaluation_criteria"] = " ".join(exc.messages)
            criteria_specs = []
        parsed_criteria = [label for label, _, _ in criteria_specs]
        if any(len(label) > 255 for label in parsed_criteria):
            errors["evaluation_criteria"] = _(
                "Cada criterio de evaluación debe tener máximo 255 caracteres."
            )
        normalized_criteria = [label.casefold() for label in parsed_criteria]
        if len(normalized_criteria) != len(set(normalized_criteria)):
            errors["evaluation_criteria"] = _(
                "Los criterios de evaluación no pueden estar repetidos."
            )

        if self.pk:
            original = Challenge.objects.filter(pk=self.pk).first()
            if original is not None:
                protected_process = (
                    original.applications.exists()
                    or original.status
                    in {
                        self.Status.CLOSED,
                        self.Status.UNDER_EVALUATION,
                        self.Status.AWARDED,
                        self.Status.CANCELLED,
                        self.Status.DESERTED,
                        self.Status.ARCHIVED,
                    }
                )
                if (
                    protected_process
                    and original.evaluation_criteria != self.evaluation_criteria
                ):
                    errors["evaluation_criteria"] = _(
                        "Los criterios no pueden modificarse después de recibir propuestas o cerrar el desafío."
                    )
                protected_commercial_fields = (
                    "budget_amount",
                    "budget_currency",
                    "application_deadline",
                )
                if protected_process and any(
                    getattr(original, field_name) != getattr(self, field_name)
                    for field_name in protected_commercial_fields
                ):
                    errors["__all__"] = _(
                        "El presupuesto, la moneda y el plazo no pueden modificarse "
                        "después de recibir propuestas o cerrar el desafío."
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
        try:
            return bool(self._parse_evaluation_criteria_specs())
        except ValidationError:
            return False

    def evaluation_criteria_list(self) -> list[str]:
        try:
            parsed_items = [
                label
                for label, _, _ in self._parse_evaluation_criteria_specs()
            ]
        except ValidationError:
            parsed_items = []
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

        desired_items = self._parse_evaluation_criteria_specs()
        existing_items = {
            item.position: item
            for item in self.evaluation_criteria_items.all()
        }

        if not desired_items:
            self.evaluation_criteria_items.all().delete()
            return

        items_to_create = []
        items_to_update = []

        for position, (label, weight, criterion_type) in enumerate(
            desired_items,
            start=1,
        ):
            existing_item = existing_items.get(position)
            if existing_item is None:
                items_to_create.append(
                    ChallengeEvaluationCriterion(
                        challenge=self,
                        label=label,
                        position=position,
                        weight=weight,
                        criterion_type=criterion_type,
                    )
                )
                continue

            if (
                existing_item.label != label
                or existing_item.weight != weight
                or existing_item.criterion_type != criterion_type
            ):
                existing_item.label = label
                existing_item.weight = weight
                existing_item.criterion_type = criterion_type
                items_to_update.append(existing_item)

        stale_positions = set(existing_items) - set(range(1, len(desired_items) + 1))
        if stale_positions:
            self.evaluation_criteria_items.filter(position__in=stale_positions).delete()

        if items_to_update:
            ChallengeEvaluationCriterion.objects.bulk_update(
                items_to_update,
                ["label", "weight", "criterion_type"],
            )

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

    @property
    def rendered_description(self) -> str:
        return render_markdown(self.description)

    @classmethod
    def publicly_visible_statuses(cls) -> tuple[str, ...]:
        return (
            cls.Status.PUBLISHED,
            cls.Status.CLOSED,
            cls.Status.UNDER_EVALUATION,
            cls.Status.AWARDED,
            cls.Status.CANCELLED,
            cls.Status.DESERTED,
        )

    def _parse_evaluation_criteria_text(self) -> list[str]:
        try:
            return [
                label
                for label, _, _ in self._parse_evaluation_criteria_specs()
            ]
        except ValidationError:
            return []

    def _parse_evaluation_criteria_specs(
        self,
    ) -> list[tuple[str, Decimal, str]]:
        raw_items: list[tuple[str, Decimal | None]] = []
        list_prefix = re.compile(r"^\s*(?:[-*•]\s+|\d+[.)]\s+)")
        weight_suffix = re.compile(
            r"^(?P<label>.+?)\s*\|\s*(?P<weight>\d+(?:[.,]\d{1,2})?)\s*%?\s*$"
        )
        for raw_line in (self.evaluation_criteria or "").splitlines():
            stripped_line = raw_line.strip()
            if not stripped_line or stripped_line in {"-", "*", "•"}:
                continue
            label = list_prefix.sub("", stripped_line, count=1).strip()
            weight = None
            weighted_match = weight_suffix.match(label)
            if weighted_match:
                label = weighted_match.group("label").strip()
                try:
                    weight = Decimal(
                        weighted_match.group("weight").replace(",", ".")
                    )
                except InvalidOperation as exc:
                    raise ValidationError(
                        {
                            "evaluation_criteria": _(
                                "El peso de cada criterio debe ser un porcentaje válido."
                            )
                        }
                    ) from exc
            elif "|" in label:
                raise ValidationError(
                    {
                        "evaluation_criteria": _(
                            "Usa el formato «Criterio | porcentaje» para definir pesos."
                        )
                    }
                )
            if label:
                raw_items.append((label, weight))

        if not raw_items:
            return []

        explicit_total = sum(
            (weight for _, weight in raw_items if weight is not None),
            start=Decimal("0"),
        )
        missing_count = sum(weight is None for _, weight in raw_items)
        if explicit_total > Decimal("100"):
            raise ValidationError(
                {
                    "evaluation_criteria": _(
                        "La suma de pesos no puede superar 100 %."
                    )
                }
            )
        if missing_count == 0 and explicit_total != Decimal("100"):
            raise ValidationError(
                {
                    "evaluation_criteria": _(
                        "Cuando indicas todos los pesos, su suma debe ser 100 %."
                    )
                }
            )
        if missing_count and explicit_total >= Decimal("100"):
            raise ValidationError(
                {
                    "evaluation_criteria": _(
                        "Debe quedar un porcentaje positivo para los criterios sin peso."
                    )
                }
            )

        remaining = Decimal("100") - explicit_total
        implicit_weights: list[Decimal] = []
        if missing_count:
            base_weight = (
                remaining / missing_count
            ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            implicit_weights = [base_weight] * missing_count
            implicit_weights[0] += remaining - sum(implicit_weights)

        economic_terms = (
            "costo",
            "precio",
            "económ",
            "econom",
            "valor ofert",
        )
        result = []
        implicit_index = 0
        for label, weight in raw_items:
            if weight is None:
                weight = implicit_weights[implicit_index]
                implicit_index += 1
            if weight <= 0:
                raise ValidationError(
                    {
                        "evaluation_criteria": _(
                            "Todos los criterios deben tener un peso mayor que cero."
                        )
                    }
                )
            normalized_label = label.casefold()
            criterion_type = (
                ChallengeEvaluationCriterion.CriterionType.ECONOMIC
                if any(term in normalized_label for term in economic_terms)
                else ChallengeEvaluationCriterion.CriterionType.TECHNICAL
            )
            result.append((label, weight, criterion_type))
        return result


class ChallengeLifecycleEvent(models.Model):
    """Immutable audit record for every explicit challenge transition."""

    class EventType(models.TextChoices):
        DRAFT_CREATED = "DRAFT_CREATED", _("Borrador creado")
        DRAFT_UPDATED = "DRAFT_UPDATED", _("Borrador actualizado")
        PUBLISHED = "PUBLISHED", _("Desafío publicado")
        CLOSED = "CLOSED", _("Recepción cerrada")
        CANCELLED = "CANCELLED", _("Desafío cancelado")
        DESERTED = "DESERTED", _("Desafío declarado desierto")

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.PROTECT,
        related_name="lifecycle_events",
    )
    event_type = models.CharField(
        _("Tipo de evento"),
        max_length=24,
        choices=EventType.choices,
    )
    from_status = models.CharField(_("Estado anterior"), max_length=24, blank=True)
    to_status = models.CharField(_("Estado resultante"), max_length=24)
    actor = models.ForeignKey(
        "identity.User",
        on_delete=models.PROTECT,
        related_name="challenge_lifecycle_events",
        null=True,
        blank=True,
    )
    is_automatic = models.BooleanField(_("Transición automática"), default=False)
    reason = models.TextField(_("Motivo"), blank=True, default="")
    occurred_at = models.DateTimeField(_("Fecha del evento"), default=timezone.now)

    class Meta:
        verbose_name = _("Evento de ciclo de vida del desafío")
        verbose_name_plural = _("Eventos de ciclo de vida del desafío")
        ordering = ["-occurred_at", "-id"]

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.challenge}"


class ChallengeEvaluationCriterion(models.Model):
    class CriterionType(models.TextChoices):
        TECHNICAL = "TECHNICAL", _("Técnico")
        ECONOMIC = "ECONOMIC", _("Económico")

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="evaluation_criteria_items",
    )
    label = models.CharField(_("Criterio"), max_length=255)
    position = models.PositiveIntegerField(_("Posición"))
    weight = models.DecimalField(
        _("Peso porcentual"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
    )
    criterion_type = models.CharField(
        _("Tipo de criterio"),
        max_length=16,
        choices=CriterionType.choices,
        default=CriterionType.TECHNICAL,
    )

    class Meta:
        verbose_name = _("Criterio de evaluación")
        verbose_name_plural = _("Criterios de evaluación")
        ordering = ["position", "id"]
        constraints = [
            UniqueConstraint(
                fields=["challenge", "position"],
                name="unique_evaluation_criterion_position_per_challenge",
            ),
            models.CheckConstraint(
                condition=models.Q(weight__gt=0) & models.Q(weight__lte=100),
                name="evaluation_criterion_weight_between_zero_and_100",
            ),
        ]

    def __str__(self):
        return f"{self.challenge}: {self.label}"


class ChallengeCategoryQuerySet(models.QuerySet):
    def delete(self):
        referenced = self.filter(challenges__isnull=False).distinct()
        if referenced.exists():
            raise ProtectedError(
                "Las categorías referenciadas no pueden eliminarse; desactívalas.",
                list(referenced),
            )
        return super().delete()


class ChallengeCategory(models.Model):
    objects = ChallengeCategoryQuerySet.as_manager()

    name = models.CharField(_("Nombre"), max_length=120, unique=True)
    slug = models.SlugField(_("Slug"), max_length=140, unique=True)
    description = models.TextField(_("Descripción"), blank=True, default="")
    is_active = models.BooleanField(_("Activa"), default=True)
    position = models.PositiveIntegerField(_("Posición"), default=0)

    class Meta:
        verbose_name = _("Categoría de desafío")
        verbose_name_plural = _("Categorías de desafío")
        ordering = ["position", "name"]

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.challenges.exists():
            raise ProtectedError(
                "Una categoría referenciada no puede eliminarse; desactívala.",
                [self],
            )
        return super().delete(*args, **kwargs)


class ApplicationQuerySet(models.QuerySet):
    def drafts(self):
        return self.filter(status="DRAFT")

    def submitted(self):
        return self.filter(status="SUBMITTED")


class Application(models.Model):
    """
    Proposal submitted by a proveedor tecnológico organization for a challenge.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Borrador")
        SUBMITTED = "SUBMITTED", _("Enviada")

    objects = ApplicationQuerySet.as_manager()

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
    offered_amount = models.DecimalField(
        _("Valor total ofertado"),
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    offer_currency = models.CharField(
        _("Moneda de la oferta"),
        max_length=3,
        choices=Challenge.Currency.choices,
        blank=True,
        default="",
    )
    estimated_duration_days = models.PositiveIntegerField(
        _("Duración estimada (días)"),
        null=True,
        blank=True,
    )
    status = models.CharField(
        _("Estado"),
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    applied_at = models.DateTimeField(
        _("Fecha de envío"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Postulación")
        verbose_name_plural = _("Postulaciones")
        constraints = [
            UniqueConstraint(
                fields=["challenge", "applicant"],
                name="unique_application_per_challenge_and_applicant",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(offered_amount__isnull=True)
                    | models.Q(offered_amount__gt=0)
                ),
                name="application_offered_amount_positive_or_null",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(estimated_duration_days__isnull=True)
                    | models.Q(estimated_duration_days__gt=0)
                ),
                name="application_duration_days_positive_or_null",
            ),
        ]

    def clean(self):
        errors = {}
        original = None
        if self.pk:
            original = Application.objects.filter(pk=self.pk).first()

        if self.applicant and self.applicant.role != Organization.MarketRole.SUPPLY_SIDE:
            errors["applicant"] = _(
                "Solo las organizaciones con rol Proveedor tecnológico pueden aplicar a desafíos."
            )

        requires_open_challenge = (
            self.status == self.Status.DRAFT
            or original is None
            or (original is not None and original.status == self.Status.DRAFT)
        )
        if (
            self.challenge
            and requires_open_challenge
            and not self.challenge.is_open_for_applications()
        ):
            errors["challenge"] = _(
                "Este desafío no está abierto para guardar o enviar propuestas."
            )

        if self.status == self.Status.SUBMITTED:
            required_components = {
                "problem_understanding": self.problem_understanding,
                "proposed_solution": self.proposed_solution,
                "capabilities_evidence": self.capabilities_evidence,
                "execution_plan": self.execution_plan,
            }
            for field_name, value in required_components.items():
                if not (value or "").strip():
                    errors[field_name] = _(
                        "Este campo es obligatorio para enviar la propuesta."
                    )
            if self.applied_at is None:
                errors["applied_at"] = _(
                    "Una propuesta enviada debe registrar su fecha de envío."
                )
            if self.challenge and self.challenge.budget_amount is not None:
                if self.offered_amount is None:
                    errors["offered_amount"] = _(
                        "Debes indicar el valor total de la oferta."
                    )
                elif self.offered_amount <= 0:
                    errors["offered_amount"] = _(
                        "El valor total ofertado debe ser mayor que cero."
                    )
                elif self.offered_amount > self.challenge.budget_amount:
                    errors["offered_amount"] = _(
                        "El valor total ofertado no puede superar el presupuesto "
                        "máximo del desafío."
                    )
                if self.offer_currency != self.challenge.budget_currency:
                    errors["offer_currency"] = _(
                        "La moneda de la oferta debe coincidir con la moneda del presupuesto."
                    )
                if not self.estimated_duration_days:
                    errors["estimated_duration_days"] = _(
                        "Debes indicar la duración estimada de ejecución."
                    )

        if original is not None:
            identity_fields = ("challenge_id", "applicant_id")
            if any(
                getattr(original, field_name) != getattr(self, field_name)
                for field_name in identity_fields
            ):
                errors["__all__"] = _(
                    "La identidad de la propuesta no puede modificarse."
                )

            immutable_fields = (
                "status",
                "proposal_text",
                "problem_understanding",
                "proposed_solution",
                "capabilities_evidence",
                "execution_plan",
                "offered_amount",
                "offer_currency",
                "estimated_duration_days",
                "applied_at",
            )
            if original.status == self.Status.SUBMITTED and any(
                getattr(original, field_name) != getattr(self, field_name)
                for field_name in immutable_fields
            ):
                errors["__all__"] = _(
                    "Una propuesta enviada no puede modificarse después del envío."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.status == self.Status.SUBMITTED:
            if self.applied_at is None:
                self.applied_at = timezone.now()
            if not (self.proposal_text or "").strip():
                self.proposal_text = self._build_application_summary()
        else:
            self.applied_at = None
            self.proposal_text = (self.proposal_text or "").strip()
        self.full_clean()
        super().save(*args, **kwargs)

    def has_required_components(self) -> bool:
        return all(
            (value or "").strip()
            for value in (
                self.problem_understanding,
                self.proposed_solution,
                self.capabilities_evidence,
                self.execution_plan,
            )
        )

    def is_editable_draft(self) -> bool:
        return self.status == self.Status.DRAFT and self.challenge.is_open_for_applications()

    @property
    def summary_text(self) -> str:
        return self.proposed_solution or self.proposal_text

    @property
    def rendered_problem_understanding(self) -> str:
        return render_markdown(self.problem_understanding)

    @property
    def rendered_proposed_solution(self) -> str:
        return render_markdown(self.proposed_solution)

    @property
    def rendered_capabilities_evidence(self) -> str:
        return render_markdown(self.capabilities_evidence)

    @property
    def rendered_execution_plan(self) -> str:
        return render_markdown(self.execution_plan)

    def __str__(self):
        return f"Propuesta de {self.applicant} para {self.challenge}"

    def _build_application_summary(self) -> str:
        return build_application_summary(
            problem_understanding=self.problem_understanding,
            proposed_solution=self.proposed_solution,
            capabilities_evidence=self.capabilities_evidence,
            execution_plan=self.execution_plan,
        )


class AttachmentBase(models.Model):
    opaque_id = models.CharField(
        _("Identificador opaco"),
        max_length=32,
        unique=True,
        default=new_opaque_id,
        editable=False,
    )
    file = models.FileField(
        _("Archivo"),
        upload_to=build_attachment_upload_path,
        validators=[validate_attachment_file],
    )
    original_filename = models.CharField(_("Nombre original"), max_length=255)
    content_type = models.CharField(_("Tipo de contenido"), max_length=120)
    size = models.PositiveIntegerField(_("Tamaño en bytes"))
    uploaded_by = models.ForeignKey(
        "identity.User",
        on_delete=models.PROTECT,
        related_name="%(class)s_uploads",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["created_at", "id"]

    def clean(self):
        validate_attachment_file(self.file)

    def save(self, *args, **kwargs):
        if self.file:
            self.original_filename = self.original_filename or self.file.name
            # El tipo persistido sale del contenido real del archivo; la
            # cabecera del cliente y la extensión son solo fallbacks.
            self.content_type = (
                sniff_attachment_content_type(self.file)
                or self.content_type
                or getattr(self.file, "content_type", "")
                or mimetypes.guess_type(self.file.name)[0]
                or ""
            )
            self.size = self.size or self.file.size
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_filename


class ChallengeAttachment(AttachmentBase):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    class Meta(AttachmentBase.Meta):
        verbose_name = _("Adjunto de desafío")
        verbose_name_plural = _("Adjuntos de desafío")


class ApplicationAttachment(AttachmentBase):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    class Meta(AttachmentBase.Meta):
        verbose_name = _("Adjunto de propuesta")
        verbose_name_plural = _("Adjuntos de propuesta")
