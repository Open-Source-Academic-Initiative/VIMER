from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.corporate.models import Organization
from apps.marketplace.application.commands import (
    PublishChallengeCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.application.exceptions import (
    ChallengePublicationValidationError,
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.domain.exceptions import (
    ChallengeApplicationNotAllowed,
    ChallengeNotOpenForApplications,
    ChallengePublicationNotAllowed,
    DuplicateChallengeApplication,
    IncompleteChallengeApplication,
)
from apps.marketplace.domain.rules import (
    build_application_summary,
    ensure_challenge_is_open_for_applications,
    ensure_organization_can_publish_challenge,
    ensure_organization_can_submit_application,
    ensure_organization_has_not_applied_to_challenge,
    ensure_submitted_application_is_complete,
)
from apps.marketplace.models import Application, Challenge


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


@transaction.atomic
def submit_challenge_application(
    challenge: Challenge,
    applicant: Organization,
    command: SubmitApplicationCommand,
) -> Application:
    try:
        ensure_challenge_is_open_for_applications(challenge)
        ensure_organization_can_submit_application(applicant)
        ensure_organization_has_not_applied_to_challenge(challenge, applicant)
        ensure_submitted_application_is_complete(
            problem_understanding=command.problem_understanding,
            proposed_solution=command.proposed_solution,
            capabilities_evidence=command.capabilities_evidence,
            execution_plan=command.execution_plan,
        )
    except DuplicateChallengeApplication as exc:
        raise DuplicateChallengeApplicationError from exc
    except IncompleteChallengeApplication as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ChallengeNotOpenForApplications as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ChallengeApplicationNotAllowed as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc

    application = Application(
        challenge=challenge,
        applicant=applicant,
        proposal_text=build_application_summary(
            problem_understanding=command.problem_understanding,
            proposed_solution=command.proposed_solution,
            capabilities_evidence=command.capabilities_evidence,
            execution_plan=command.execution_plan,
        ),
        problem_understanding=command.problem_understanding,
        proposed_solution=command.proposed_solution,
        capabilities_evidence=command.capabilities_evidence,
        execution_plan=command.execution_plan,
    )

    try:
        application.save()
    except IntegrityError as exc:
        raise DuplicateChallengeApplicationError from exc
    except ValidationError as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc

    return application
