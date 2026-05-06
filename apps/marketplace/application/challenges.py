from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction

from apps.corporate.models import Organization
from apps.marketplace.application.commands import PublishChallengeCommand
from apps.marketplace.application.exceptions import (
    ChallengePublicationValidationError,
)
from apps.marketplace.domain.challenges import (
    ensure_organization_can_publish_challenge,
)
from apps.marketplace.domain.exceptions import ChallengePublicationNotAllowed
from apps.marketplace.models import Challenge, ChallengeAttachment, ChallengeCategory


@transaction.atomic
def publish_challenge(
    publisher: Organization,
    command: PublishChallengeCommand,
    actor=None,
) -> Challenge:
    try:
        ensure_organization_can_publish_challenge(publisher)
    except ChallengePublicationNotAllowed as exc:
        raise ChallengePublicationValidationError(exc.messages) from exc

    challenge = Challenge(
        publisher=publisher,
        title=command.title,
        description=command.description,
        evaluation_criteria=command.evaluation_criteria,
        status=Challenge.Status.PUBLISHED,
        application_deadline=command.application_deadline,
    )

    try:
        challenge.save()
        selected_categories = ChallengeCategory.objects.filter(
            pk__in=command.category_ids,
            is_active=True,
        )
        if not command.category_ids:
            selected_categories = ChallengeCategory.objects.filter(is_active=True)[:1]
        challenge.categories.set(selected_categories)
        if not challenge.categories.exists():
            raise ChallengePublicationValidationError(
                ["Debes seleccionar al menos una categoría para el desafío."]
            )
        if len(command.attachments) > settings.MARKETPLACE_ATTACHMENT_MAX_COUNT:
            raise ChallengePublicationValidationError(
                [f"No puedes adjuntar más de {settings.MARKETPLACE_ATTACHMENT_MAX_COUNT} archivos."]
            )
        for attachment in command.attachments:
            ChallengeAttachment.objects.create(
                challenge=challenge,
                file=attachment,
                original_filename=attachment.name,
                content_type=getattr(attachment, "content_type", ""),
                size=attachment.size,
                uploaded_by=actor or publisher.members.order_by("pk").first(),
            )
    except ValidationError as exc:
        raise ChallengePublicationValidationError(exc.messages) from exc

    challenge.sync_evaluation_criteria_items()

    return challenge
