from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.corporate.models import Organization
from apps.marketplace.application.commands import (
    SaveApplicationDraftCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.domain.applications import (
    build_application_summary,
    ensure_challenge_is_open_for_applications,
    ensure_existing_application_is_not_submitted,
    ensure_organization_can_submit_application,
    get_existing_application_for_organization,
    ensure_submitted_application_is_complete,
)
from apps.marketplace.domain.exceptions import (
    ChallengeApplicationNotAllowed,
    ChallengeNotOpenForApplications,
    ExistingSubmittedApplication,
    IncompleteChallengeApplication,
)
from apps.marketplace.models import Application, Challenge


def _upsert_application(
    *,
    challenge: Challenge,
    applicant: Organization,
    status: str,
    problem_understanding: str,
    proposed_solution: str,
    capabilities_evidence: str,
    execution_plan: str,
) -> Application:
    existing_application = get_existing_application_for_organization(
        challenge,
        applicant,
    )
    ensure_existing_application_is_not_submitted(existing_application)

    application = existing_application or Application(
        challenge=challenge,
        applicant=applicant,
    )
    application.status = status
    application.problem_understanding = problem_understanding
    application.proposed_solution = proposed_solution
    application.capabilities_evidence = capabilities_evidence
    application.execution_plan = execution_plan
    if status == Application.Status.SUBMITTED:
        application.proposal_text = build_application_summary(
            problem_understanding=problem_understanding,
            proposed_solution=proposed_solution,
            capabilities_evidence=capabilities_evidence,
            execution_plan=execution_plan,
        )

    try:
        application.save()
    except IntegrityError as exc:
        raise DuplicateChallengeApplicationError from exc
    except ValidationError as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc

    return application


@transaction.atomic
def save_application_draft(
    challenge: Challenge,
    applicant: Organization,
    command: SaveApplicationDraftCommand,
) -> Application:
    try:
        ensure_challenge_is_open_for_applications(challenge)
        ensure_organization_can_submit_application(applicant)
        ensure_existing_application_is_not_submitted(
            get_existing_application_for_organization(challenge, applicant)
        )
    except ChallengeNotOpenForApplications as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ChallengeApplicationNotAllowed as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ExistingSubmittedApplication as exc:
        raise DuplicateChallengeApplicationError from exc

    return _upsert_application(
        challenge=challenge,
        applicant=applicant,
        status=Application.Status.DRAFT,
        problem_understanding=command.problem_understanding,
        proposed_solution=command.proposed_solution,
        capabilities_evidence=command.capabilities_evidence,
        execution_plan=command.execution_plan,
    )


@transaction.atomic
def submit_challenge_application(
    challenge: Challenge,
    applicant: Organization,
    command: SubmitApplicationCommand,
) -> Application:
    try:
        ensure_challenge_is_open_for_applications(challenge)
        ensure_organization_can_submit_application(applicant)
        ensure_existing_application_is_not_submitted(
            get_existing_application_for_organization(challenge, applicant)
        )
        ensure_submitted_application_is_complete(
            problem_understanding=command.problem_understanding,
            proposed_solution=command.proposed_solution,
            capabilities_evidence=command.capabilities_evidence,
            execution_plan=command.execution_plan,
        )
    except ExistingSubmittedApplication as exc:
        raise DuplicateChallengeApplicationError from exc
    except IncompleteChallengeApplication as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ChallengeNotOpenForApplications as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ChallengeApplicationNotAllowed as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc

    return _upsert_application(
        challenge=challenge,
        applicant=applicant,
        status=Application.Status.SUBMITTED,
        problem_understanding=command.problem_understanding,
        proposed_solution=command.proposed_solution,
        capabilities_evidence=command.capabilities_evidence,
        execution_plan=command.execution_plan,
    )
