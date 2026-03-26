from apps.corporate.models import Organization
from apps.marketplace.domain.exceptions import ChallengePublicationNotAllowed
from apps.marketplace.domain.invariants import (
    INV_05_ONLY_DEMAND_SIDE_CAN_PUBLISH_CHALLENGES,
)


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
