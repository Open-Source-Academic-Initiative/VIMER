from django.core.exceptions import ValidationError
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
from apps.marketplace.models import Challenge


@transaction.atomic
def publish_challenge(
    publisher: Organization,
    command: PublishChallengeCommand,
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
    except ValidationError as exc:
        raise ChallengePublicationValidationError(exc.messages) from exc

    challenge.sync_evaluation_criteria_items()

    return challenge
