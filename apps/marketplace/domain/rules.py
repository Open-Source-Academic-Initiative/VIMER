from apps.corporate.models import Organization
from apps.marketplace.domain.exceptions import (
    ChallengeApplicationNotAllowed,
    ChallengeNotOpenForApplications,
    ChallengePublicationNotAllowed,
    DuplicateChallengeApplication,
    IncompleteChallengeApplication,
)
from apps.marketplace.domain.invariants import (
    INV_05_ONLY_DEMAND_SIDE_CAN_PUBLISH_CHALLENGES,
    INV_06_ONLY_SUPPLY_SIDE_CAN_SUBMIT_APPLICATIONS,
    INV_07_ONE_APPLICATION_PER_CHALLENGE_AND_APPLICANT,
    INV_11_CHALLENGE_MUST_BE_OPEN_FOR_APPLICATIONS,
    INV_13_APPLICATION_REQUIRES_ALL_COMPONENTS,
)
from apps.marketplace.models import Application, Challenge


def ensure_organization_can_publish_challenge(
    publisher: Organization | None,
) -> None:
    if (
        publisher is None
        or publisher.role != Organization.MarketRole.DEMAND_SIDE
    ):
        raise ChallengePublicationNotAllowed(
            "Solo las organizaciones con rol Solicitante pueden publicar desafíos.",
            invariant_id=INV_05_ONLY_DEMAND_SIDE_CAN_PUBLISH_CHALLENGES,
        )


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


def ensure_organization_has_not_applied_to_challenge(
    challenge: Challenge,
    applicant: Organization,
) -> None:
    if Application.objects.filter(challenge=challenge, applicant=applicant).exists():
        raise DuplicateChallengeApplication(
            "Tu organización ya envió una propuesta para este desafío.",
            invariant_id=INV_07_ONE_APPLICATION_PER_CHALLENGE_AND_APPLICANT,
        )


def ensure_challenge_is_open_for_applications(challenge: Challenge) -> None:
    if not challenge.is_open_for_applications():
        raise ChallengeNotOpenForApplications(
            "Este desafío no está abierto para recibir propuestas.",
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


def build_application_summary(
    *,
    problem_understanding: str,
    proposed_solution: str,
    capabilities_evidence: str,
    execution_plan: str,
) -> str:
    return "\n\n".join(
        [
            f"Entendimiento del problema: {problem_understanding.strip()}",
            f"Solución propuesta: {proposed_solution.strip()}",
            f"Capacidades y evidencia: {capabilities_evidence.strip()}",
            f"Plan de ejecución: {execution_plan.strip()}",
        ]
    )
