from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.corporate.models import Organization
from apps.marketplace.application.commands import PublishChallengeCommand
from apps.marketplace.application.exceptions import (
    ChallengeLifecycleValidationError,
    ChallengePublicationValidationError,
)
from apps.marketplace.domain.challenges import (
    ensure_organization_can_publish_challenge,
)
from apps.marketplace.domain.exceptions import ChallengePublicationNotAllowed
from apps.marketplace.domain.events import ChallengeLifecycleChanged
from apps.marketplace.domain.signals import publish_challenge_lifecycle_changed
from apps.marketplace.models import (
    Challenge,
    ChallengeAttachment,
    ChallengeCategory,
    ChallengeEvaluationCriterion,
    ChallengeLifecycleEvent,
)


def _cleanup_uncommitted_files(created_attachments) -> None:
    for attachment in created_attachments:
        if attachment.file:
            attachment.file.storage.delete(attachment.file.name)


def _resolve_operational_actor(*, publisher: Organization, actor):
    resolved_actor = actor or publisher.members.filter(
        is_active=True,
        status="ACTIVE",
        is_email_verified=True,
    ).order_by("pk").first()
    if (
        resolved_actor is None
        or not resolved_actor.is_operational_member_of(publisher.pk)
    ):
        raise ChallengeLifecycleValidationError(
            [
                "La transición requiere una cuenta activa, verificada y "
                "aprobada de la organización publicadora."
            ]
        )
    return resolved_actor


def _validate_publishable_challenge(challenge: Challenge) -> None:
    messages = []
    if not challenge.application_deadline:
        messages.append("Debes definir una fecha límite para recibir propuestas.")
    if challenge.budget_amount is None:
        messages.append("Debes definir el presupuesto máximo del desafío.")
    if not challenge.has_evaluation_criteria():
        messages.append("Debes definir al menos un criterio de evaluación válido.")
    elif (
        challenge.budget_amount is not None
        and not challenge.evaluation_criteria_items.filter(
            criterion_type=ChallengeEvaluationCriterion.CriterionType.ECONOMIC
        ).exists()
    ):
        messages.append(
            "Debes incluir un criterio económico explícito, por ejemplo "
            "«Valor económico de la oferta»."
        )
    if not challenge.categories.filter(is_active=True).exists():
        messages.append("Debes seleccionar al menos una categoría activa.")
    if messages:
        raise ChallengeLifecycleValidationError(messages)


def _record_lifecycle_event(
    *,
    challenge: Challenge,
    event_type: str,
    from_status: str,
    actor,
    reason: str = "",
    is_automatic: bool = False,
) -> ChallengeLifecycleEvent:
    lifecycle_event = ChallengeLifecycleEvent.objects.create(
        challenge=challenge,
        event_type=event_type,
        from_status=from_status,
        to_status=challenge.status,
        actor=actor,
        reason=(reason or "").strip(),
        is_automatic=is_automatic,
    )
    publish_challenge_lifecycle_changed(
        ChallengeLifecycleChanged(
            challenge_id=challenge.pk,
            event_type=event_type,
            actor_user_id=getattr(actor, "pk", None),
            occurred_at=lifecycle_event.occurred_at,
        )
    )
    return lifecycle_event


@transaction.atomic
def publish_challenge(
    publisher: Organization,
    command: PublishChallengeCommand,
    actor=None,
) -> Challenge:
    created_attachments = []
    try:
        ensure_organization_can_publish_challenge(publisher)
    except ChallengePublicationNotAllowed as exc:
        raise ChallengePublicationValidationError(exc.messages) from exc

    # La taxonomía es cerrada y obligatoria: sin una categoría activa elegida
    # por el publicador no se publica nada (no se asigna una en silencio).
    selected_categories = list(
        ChallengeCategory.objects.filter(
            pk__in=command.category_ids,
            is_active=True,
        )
    )
    if not selected_categories:
        raise ChallengePublicationValidationError(
            ["Debes seleccionar al menos una categoría para el desafío."]
        )

    try:
        resolved_actor = _resolve_operational_actor(
            publisher=publisher,
            actor=actor,
        )
    except ChallengeLifecycleValidationError as exc:
        raise ChallengePublicationValidationError(exc.messages) from exc

    challenge = Challenge(
        publisher=publisher,
        title=command.title,
        description=command.description,
        evaluation_criteria=command.evaluation_criteria,
        status=Challenge.Status.PUBLISHED,
        application_deadline=command.application_deadline,
        budget_amount=command.budget_amount,
        budget_currency=command.budget_currency,
    )

    try:
        challenge.save()
        challenge.categories.set(selected_categories)
        _validate_publishable_challenge(challenge)
        if len(command.attachments) > settings.MARKETPLACE_ATTACHMENT_MAX_COUNT:
            raise ChallengePublicationValidationError(
                [f"No puedes adjuntar más de {settings.MARKETPLACE_ATTACHMENT_MAX_COUNT} archivos."]
            )
        for attachment in command.attachments:
            created_attachment = ChallengeAttachment.objects.create(
                challenge=challenge,
                file=attachment,
                original_filename=attachment.name,
                content_type=getattr(attachment, "content_type", ""),
                size=attachment.size,
                uploaded_by=resolved_actor,
            )
            created_attachments.append(created_attachment)
        _record_lifecycle_event(
            challenge=challenge,
            event_type=ChallengeLifecycleEvent.EventType.PUBLISHED,
            from_status="",
            actor=resolved_actor,
            reason="Publicación inicial del desafío.",
        )
    except ChallengeLifecycleValidationError as exc:
        _cleanup_uncommitted_files(created_attachments)
        raise ChallengePublicationValidationError(exc.messages) from exc
    except ValidationError as exc:
        _cleanup_uncommitted_files(created_attachments)
        raise ChallengePublicationValidationError(exc.messages) from exc

    challenge.sync_evaluation_criteria_items()

    return challenge


@transaction.atomic
def create_challenge_draft(
    *,
    publisher: Organization,
    command: PublishChallengeCommand,
    actor,
) -> Challenge:
    created_attachments = []
    try:
        ensure_organization_can_publish_challenge(publisher)
    except ChallengePublicationNotAllowed as exc:
        raise ChallengePublicationValidationError(exc.messages) from exc

    resolved_actor = _resolve_operational_actor(publisher=publisher, actor=actor)
    selected_categories = list(
        ChallengeCategory.objects.filter(
            pk__in=command.category_ids,
            is_active=True,
        )
    )
    challenge = Challenge(
        publisher=publisher,
        title=command.title,
        description=command.description,
        evaluation_criteria=command.evaluation_criteria,
        status=Challenge.Status.DRAFT,
        application_deadline=command.application_deadline,
        budget_amount=command.budget_amount,
        budget_currency=command.budget_currency,
    )
    try:
        challenge.save()
        challenge.categories.set(selected_categories)
        if len(command.attachments) > settings.MARKETPLACE_ATTACHMENT_MAX_COUNT:
            raise ChallengePublicationValidationError(
                [
                    "No puedes adjuntar más de "
                    f"{settings.MARKETPLACE_ATTACHMENT_MAX_COUNT} archivos."
                ]
            )
        for attachment in command.attachments:
            created_attachment = ChallengeAttachment.objects.create(
                challenge=challenge,
                file=attachment,
                original_filename=attachment.name,
                content_type=getattr(attachment, "content_type", ""),
                size=attachment.size,
                uploaded_by=resolved_actor,
            )
            created_attachments.append(created_attachment)
        _record_lifecycle_event(
            challenge=challenge,
            event_type=ChallengeLifecycleEvent.EventType.DRAFT_CREATED,
            from_status="",
            actor=resolved_actor,
            reason="Creación del borrador.",
        )
    except ValidationError as exc:
        _cleanup_uncommitted_files(created_attachments)
        raise ChallengePublicationValidationError(exc.messages) from exc
    return challenge


@transaction.atomic
def update_challenge_draft(
    *,
    challenge: Challenge,
    command: PublishChallengeCommand,
    actor,
) -> Challenge:
    challenge = (
        Challenge.objects.select_for_update()
        .select_related("publisher")
        .get(pk=challenge.pk)
    )
    resolved_actor = _resolve_operational_actor(
        publisher=challenge.publisher,
        actor=actor,
    )
    if challenge.status != Challenge.Status.DRAFT:
        raise ChallengeLifecycleValidationError(
            ["Solo un desafío en borrador puede editarse."]
        )

    selected_categories = list(
        ChallengeCategory.objects.filter(
            pk__in=command.category_ids,
            is_active=True,
        )
    )
    if len(command.attachments) + challenge.attachments.count() > (
        settings.MARKETPLACE_ATTACHMENT_MAX_COUNT
    ):
        raise ChallengeLifecycleValidationError(
            [
                "El desafío no puede acumular más de "
                f"{settings.MARKETPLACE_ATTACHMENT_MAX_COUNT} archivos."
            ]
        )

    challenge.title = command.title
    challenge.description = command.description
    challenge.evaluation_criteria = command.evaluation_criteria
    challenge.application_deadline = command.application_deadline
    challenge.budget_amount = command.budget_amount
    challenge.budget_currency = command.budget_currency
    created_attachments = []
    try:
        challenge.save()
        challenge.categories.set(selected_categories)
        for attachment in command.attachments:
            created_attachment = ChallengeAttachment.objects.create(
                challenge=challenge,
                file=attachment,
                original_filename=attachment.name,
                content_type=getattr(attachment, "content_type", ""),
                size=attachment.size,
                uploaded_by=resolved_actor,
            )
            created_attachments.append(created_attachment)
    except ValidationError as exc:
        _cleanup_uncommitted_files(created_attachments)
        raise ChallengeLifecycleValidationError(exc.messages) from exc

    _record_lifecycle_event(
        challenge=challenge,
        event_type=ChallengeLifecycleEvent.EventType.DRAFT_UPDATED,
        from_status=Challenge.Status.DRAFT,
        actor=resolved_actor,
        reason="Actualización del contenido del borrador.",
    )
    return challenge


@transaction.atomic
def publish_challenge_draft(*, challenge: Challenge, actor) -> Challenge:
    challenge = (
        Challenge.objects.select_for_update()
        .select_related("publisher")
        .get(pk=challenge.pk)
    )
    resolved_actor = _resolve_operational_actor(
        publisher=challenge.publisher,
        actor=actor,
    )
    if challenge.status != Challenge.Status.DRAFT:
        raise ChallengeLifecycleValidationError(
            ["Solo un desafío en borrador puede publicarse."]
        )
    _validate_publishable_challenge(challenge)
    previous_status = challenge.status
    challenge.status = Challenge.Status.PUBLISHED
    try:
        challenge.save(update_fields=["status"])
    except ValidationError as exc:
        raise ChallengeLifecycleValidationError(exc.messages) from exc
    _record_lifecycle_event(
        challenge=challenge,
        event_type=ChallengeLifecycleEvent.EventType.PUBLISHED,
        from_status=previous_status,
        actor=resolved_actor,
        reason="Publicación aprobada por la organización convocante.",
    )
    return challenge


@transaction.atomic
def close_challenge(
    *,
    challenge: Challenge,
    actor,
    reason: str = "",
) -> Challenge:
    challenge = (
        Challenge.objects.select_for_update()
        .select_related("publisher")
        .get(pk=challenge.pk)
    )
    resolved_actor = _resolve_operational_actor(
        publisher=challenge.publisher,
        actor=actor,
    )
    if challenge.status != Challenge.Status.PUBLISHED:
        raise ChallengeLifecycleValidationError(
            ["Solo un desafío publicado puede cerrar la recepción de propuestas."]
        )
    normalized_reason = (reason or "").strip()
    if (
        (
            challenge.application_deadline is None
            or challenge.application_deadline >= timezone.localdate()
        )
        and not normalized_reason
    ):
        raise ChallengeLifecycleValidationError(
            ["El cierre anticipado exige registrar un motivo."]
        )
    previous_status = challenge.status
    challenge.status = Challenge.Status.CLOSED
    challenge.save(update_fields=["status"])
    _record_lifecycle_event(
        challenge=challenge,
        event_type=ChallengeLifecycleEvent.EventType.CLOSED,
        from_status=previous_status,
        actor=resolved_actor,
        reason=normalized_reason or "Cierre posterior al vencimiento del plazo.",
    )
    return challenge


@transaction.atomic
def close_expired_challenge(*, challenge_id: int) -> Challenge | None:
    """Close one expired published challenge exactly once.

    The row lock and state/deadline comparison make repeated scheduler runs
    idempotent. System transitions have no human actor and remain explicit in
    the lifecycle ledger.
    """
    challenge = (
        Challenge.objects.select_for_update()
        .select_related("publisher")
        .filter(pk=challenge_id)
        .first()
    )
    if (
        challenge is None
        or challenge.status != Challenge.Status.PUBLISHED
        or challenge.application_deadline is None
        or challenge.application_deadline >= timezone.localdate()
    ):
        return None

    previous_status = challenge.status
    challenge.status = Challenge.Status.CLOSED
    challenge.save(update_fields=["status"])
    _record_lifecycle_event(
        challenge=challenge,
        event_type=ChallengeLifecycleEvent.EventType.CLOSED,
        from_status=previous_status,
        actor=None,
        reason="Cierre automático por vencimiento del plazo de recepción.",
        is_automatic=True,
    )
    return challenge


@transaction.atomic
def cancel_challenge(*, challenge: Challenge, actor, reason: str) -> Challenge:
    challenge = (
        Challenge.objects.select_for_update()
        .select_related("publisher")
        .get(pk=challenge.pk)
    )
    resolved_actor = _resolve_operational_actor(
        publisher=challenge.publisher,
        actor=actor,
    )
    if challenge.status not in {
        Challenge.Status.DRAFT,
        Challenge.Status.PUBLISHED,
        Challenge.Status.CLOSED,
    }:
        raise ChallengeLifecycleValidationError(
            ["Este desafío ya no admite cancelación."]
        )
    normalized_reason = (reason or "").strip()
    if not normalized_reason:
        raise ChallengeLifecycleValidationError(
            ["Debes registrar el motivo de la cancelación."]
        )
    previous_status = challenge.status
    challenge.status = Challenge.Status.CANCELLED
    challenge.save(update_fields=["status"])
    _record_lifecycle_event(
        challenge=challenge,
        event_type=ChallengeLifecycleEvent.EventType.CANCELLED,
        from_status=previous_status,
        actor=resolved_actor,
        reason=normalized_reason,
    )
    return challenge


@transaction.atomic
def declare_challenge_deserted(
    *,
    challenge: Challenge,
    actor,
    reason: str,
) -> Challenge:
    challenge = (
        Challenge.objects.select_for_update()
        .select_related("publisher")
        .get(pk=challenge.pk)
    )
    resolved_actor = _resolve_operational_actor(
        publisher=challenge.publisher,
        actor=actor,
    )
    if challenge.status not in {
        Challenge.Status.CLOSED,
        Challenge.Status.UNDER_EVALUATION,
    }:
        raise ChallengeLifecycleValidationError(
            ["Solo un desafío cerrado o en evaluación puede declararse desierto."]
        )
    if challenge.status == Challenge.Status.UNDER_EVALUATION:
        from apps.evaluation.models import ChallengeEvaluationRoleAssignment

        if not challenge.evaluation_role_assignments.filter(
            user=resolved_actor,
            role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR,
        ).exists():
            raise ChallengeLifecycleValidationError(
                [
                    "Durante la evaluación, solo el adjudicador designado puede "
                    "declarar desierto el desafío."
                ]
            )
    if hasattr(challenge, "award_decision"):
        raise ChallengeLifecycleValidationError(
            ["Un desafío adjudicado no puede declararse desierto."]
        )
    normalized_reason = (reason or "").strip()
    if not normalized_reason:
        raise ChallengeLifecycleValidationError(
            ["Debes registrar el motivo para declarar desierto el desafío."]
        )
    previous_status = challenge.status
    challenge.status = Challenge.Status.DESERTED
    challenge.save(update_fields=["status"])
    _record_lifecycle_event(
        challenge=challenge,
        event_type=ChallengeLifecycleEvent.EventType.DESERTED,
        from_status=previous_status,
        actor=resolved_actor,
        reason=normalized_reason,
    )
    return challenge
