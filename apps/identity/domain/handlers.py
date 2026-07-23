from django.dispatch import receiver

from apps.identity.domain.events import (
    OrganizationOwnershipTransferred,
    RepresentativeJoinApproved,
    RepresentativeJoinExpired,
    RepresentativeJoinRejected,
    RepresentativeJoinRequested,
)
from apps.identity.domain.signals import (
    organization_ownership_transferred,
    representative_join_approved,
    representative_join_expired,
    representative_join_rejected,
    representative_join_requested,
)
from apps.identity.models import IdentityAuditEntry


def _user_snapshot(*, actor_id=None, subject_id=None, secondary_user_id=None) -> dict:
    return {
        key: value
        for key, value in {
            "actor_user_id": actor_id,
            "subject_user_id": subject_id,
            "secondary_user_id": secondary_user_id,
        }.items()
        if value is not None
    }


@receiver(
    representative_join_requested,
    sender=RepresentativeJoinRequested,
    dispatch_uid="identity.audit_representative_join_requested",
)
def audit_representative_join_requested(sender, *, event, **kwargs):
    IdentityAuditEntry.objects.create(
        event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_REQUESTED,
        organization_id=event.organization_id,
        actor_id=event.requester_user_id,
        subject_id=event.requester_user_id,
        join_request_id=event.join_request_id,
        description="Un representante solicitó unirse a la organización.",
        snapshot=_user_snapshot(
            actor_id=event.requester_user_id,
            subject_id=event.requester_user_id,
        ),
        occurred_at=event.occurred_at,
    )


@receiver(
    representative_join_approved,
    sender=RepresentativeJoinApproved,
    dispatch_uid="identity.audit_representative_join_approved",
)
def audit_representative_join_approved(sender, *, event, **kwargs):
    IdentityAuditEntry.objects.create(
        event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_APPROVED,
        organization_id=event.organization_id,
        actor_id=event.decided_by_user_id,
        subject_id=event.requester_user_id,
        join_request_id=event.join_request_id,
        description="El titular aprobó una solicitud de unión.",
        snapshot=_user_snapshot(
            actor_id=event.decided_by_user_id,
            subject_id=event.requester_user_id,
        ),
        occurred_at=event.occurred_at,
    )


@receiver(
    representative_join_rejected,
    sender=RepresentativeJoinRejected,
    dispatch_uid="identity.audit_representative_join_rejected",
)
def audit_representative_join_rejected(sender, *, event, **kwargs):
    IdentityAuditEntry.objects.create(
        event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_REJECTED,
        organization_id=event.organization_id,
        actor_id=event.decided_by_user_id,
        subject_id=event.requester_user_id,
        join_request_id=event.join_request_id,
        description="El titular rechazó una solicitud de unión.",
        snapshot=_user_snapshot(
            actor_id=event.decided_by_user_id,
            subject_id=event.requester_user_id,
        ),
        occurred_at=event.occurred_at,
    )


@receiver(
    representative_join_expired,
    sender=RepresentativeJoinExpired,
    dispatch_uid="identity.audit_representative_join_expired",
)
def audit_representative_join_expired(sender, *, event, **kwargs):
    IdentityAuditEntry.objects.create(
        event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_EXPIRED,
        organization_id=event.organization_id,
        subject_id=event.requester_user_id,
        join_request_id=event.join_request_id,
        description="La solicitud de unión expiró sin decisión.",
        snapshot=_user_snapshot(subject_id=event.requester_user_id),
        occurred_at=event.occurred_at,
    )


@receiver(
    organization_ownership_transferred,
    sender=OrganizationOwnershipTransferred,
    dispatch_uid="identity.audit_organization_ownership_transferred",
)
def audit_organization_ownership_transferred(sender, *, event, **kwargs):
    IdentityAuditEntry.objects.create(
        event_type=IdentityAuditEntry.EventType.ORGANIZATION_OWNERSHIP_TRANSFERRED,
        organization_id=event.organization_id,
        actor_id=event.transferred_by_user_id,
        subject_id=event.new_titular_user_id,
        secondary_user_id=event.previous_titular_user_id,
        description="La titularidad de la organización fue transferida.",
        snapshot=_user_snapshot(
            actor_id=event.transferred_by_user_id,
            subject_id=event.new_titular_user_id,
            secondary_user_id=event.previous_titular_user_id,
        ),
        occurred_at=event.occurred_at,
    )
