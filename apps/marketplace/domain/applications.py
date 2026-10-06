from apps.corporate.models import Organization

from apps.marketplace.domain.exceptions import (
    ChallengeApplicationNotAllowed,
    ChallengeNotOpenForApplications,
    DuplicateChallengeApplication,
    ExistingSubmittedApplication,
    IncompleteChallengeApplication,
)
from apps.marketplace.domain.invariants import (
    INV_06_ONLY_SUPPLY_SIDE_CAN_SUBMIT_APPLICATIONS,
    INV_07_ONE_APPLICATION_PER_CHALLENGE_AND_APPLICANT,
    INV_11_CHALLENGE_MUST_BE_OPEN_FOR_APPLICATIONS,
    INV_13_APPLICATION_REQUIRES_ALL_COMPONENTS,
    INV_14_SUBMITTED_APPLICATION_IS_IMMUTABLE,
)
from apps.marketplace.models import Application, Challenge


def ensure_organization_can_submit_application(
    applicant: Organization | None,
) -> None:
    if (
        applicant is None
        or applicant.role != Organization.MarketRole.SUPPLY_SIDE
    ):
        raise ChallengeApplicationNotAllowed(
            "Solo las organizaciones con rol Proveedor tecnológico pueden aplicar a desafíos.",
            invariant_id=INV_06_ONLY_SUPPLY_SIDE_CAN_SUBMIT_APPLICATIONS,
        )


def get_existing_application_for_organization(
    challenge: Challenge,
    applicant: Organization,
) -> Application | None:
    return (
        Application.objects.filter(challenge=challenge, applicant=applicant)
        .order_by("pk")
        .first()
    )


def ensure_organization_has_not_applied_to_challenge(
    challenge: Challenge,
    applicant: Organization,
) -> None:
    if get_existing_application_for_organization(challenge, applicant) is not None:
        raise DuplicateChallengeApplication(
            "Tu organización ya envió una propuesta para este desafío.",
            invariant_id=INV_07_ONE_APPLICATION_PER_CHALLENGE_AND_APPLICANT,
        )


def ensure_challenge_is_open_for_applications(challenge: Challenge) -> None:
    if not challenge.is_open_for_applications():
        raise ChallengeNotOpenForApplications(
            "Este desafío no está abierto para guardar o enviar propuestas.",
            invariant_id=INV_11_CHALLENGE_MUST_BE_OPEN_FOR_APPLICATIONS,
        )


def ensure_submitted_application_is_complete(
    *,
    problem_understanding: str,
    proposed_solution: str,
    capabilities_evidence: str,
    execution_plan: str,
) -> None:
    component_map = {
        "entendimiento del problema": problem_understanding,
        "solución propuesta": proposed_solution,
        "capacidades y evidencia": capabilities_evidence,
        "plan de ejecución": execution_plan,
    }

    missing_components = [
        label for label, value in component_map.items() if not (value or "").strip()
    ]
    if missing_components:
        raise IncompleteChallengeApplication(
            "La propuesta debe incluir: "
            + ", ".join(missing_components)
            + ".",
            invariant_id=INV_13_APPLICATION_REQUIRES_ALL_COMPONENTS,
        )


def ensure_existing_application_is_not_submitted(
    application: Application | None,
) -> None:
    if application is not None and application.status == Application.Status.SUBMITTED:
        raise ExistingSubmittedApplication(
            "Tu organización ya envió una propuesta para este desafío.",
            invariant_id=INV_14_SUBMITTED_APPLICATION_IS_IMMUTABLE,
        )
