from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.corporate.models import Organization
from apps.marketplace.application.commands import SubmitApplicationCommand
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.domain.applications import (
    build_application_summary,
    ensure_challenge_is_open_for_applications,
    ensure_organization_can_submit_application,
    ensure_organization_has_not_applied_to_challenge,
    ensure_submitted_application_is_complete,
)
from apps.marketplace.domain.exceptions import (
    ChallengeApplicationNotAllowed,
    ChallengeNotOpenForApplications,
    DuplicateChallengeApplication,
    IncompleteChallengeApplication,
)
from apps.marketplace.models import Application, Challenge


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
