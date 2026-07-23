from django.db import transaction
from django.dispatch import Signal

from apps.identity.domain.events import (
    OrganizationOwnershipTransferred,
    RepresentativeJoinApproved,
    RepresentativeJoinExpired,
    RepresentativeJoinRejected,
    RepresentativeJoinRequested,
)

representative_join_requested = Signal()
representative_join_approved = Signal()
representative_join_rejected = Signal()
representative_join_expired = Signal()
organization_ownership_transferred = Signal()


def _publish_after_commit(signal, sender, event) -> None:
    transaction.on_commit(lambda: signal.send(sender=sender, event=event))


def publish_representative_join_requested(event: RepresentativeJoinRequested) -> None:
    _publish_after_commit(
        representative_join_requested,
        RepresentativeJoinRequested,
        event,
    )


def publish_representative_join_approved(event: RepresentativeJoinApproved) -> None:
    _publish_after_commit(
        representative_join_approved,
        RepresentativeJoinApproved,
        event,
    )


def publish_representative_join_rejected(event: RepresentativeJoinRejected) -> None:
    _publish_after_commit(
        representative_join_rejected,
        RepresentativeJoinRejected,
        event,
    )


def publish_representative_join_expired(event: RepresentativeJoinExpired) -> None:
    _publish_after_commit(
        representative_join_expired,
        RepresentativeJoinExpired,
        event,
    )


def publish_organization_ownership_transferred(
    event: OrganizationOwnershipTransferred,
) -> None:
    _publish_after_commit(
        organization_ownership_transferred,
        OrganizationOwnershipTransferred,
        event,
    )
