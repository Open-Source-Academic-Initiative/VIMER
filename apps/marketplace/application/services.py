from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.corporate.models import Organization
from apps.marketplace.application.commands import (
    PublishChallengeCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.models import Application, Challenge


@transaction.atomic
def publish_challenge(
    publisher: Organization,
    command: PublishChallengeCommand,
) -> Challenge:
    challenge = Challenge(
        publisher=publisher,
        title=command.title,
        description=command.description,
    )
    challenge.save()
    return challenge


@transaction.atomic
def submit_challenge_application(
    challenge: Challenge,
    applicant: Organization,
    command: SubmitApplicationCommand,
) -> Application:
    if Application.objects.filter(challenge=challenge, applicant=applicant).exists():
        raise DuplicateChallengeApplicationError

    application = Application(
        challenge=challenge,
        applicant=applicant,
        proposal_text=command.proposal_text,
    )

    try:
        application.save()
    except IntegrityError as exc:
        raise DuplicateChallengeApplicationError from exc
    except ValidationError as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc

    return application
