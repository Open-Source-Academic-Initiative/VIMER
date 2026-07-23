from django.dispatch import receiver
from django.urls import reverse

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
from apps.identity.models import User
from apps.notifications.domain.handlers import send_notification_email
from apps.notifications.models import Notification


def _create_and_deliver(*, recipient: User, kind: str, title: str, body: str, link: str):
    notification = Notification.objects.create(
        recipient=recipient,
        kind=kind,
        title=title,
        body=body,
        link=link,
    )
    send_notification_email(notification)


@receiver(
    representative_join_requested,
    sender=RepresentativeJoinRequested,
    dispatch_uid="notifications.on_representative_join_requested",
)
def notify_representative_join_requested(sender, *, event, **kwargs):
    recipients = User.objects.operational_members_of(event.organization_id).filter(
        is_organization_titular=True
    )
    for recipient in recipients:
        _create_and_deliver(
            recipient=recipient,
            kind=Notification.Kind.REPRESENTATIVE_JOIN_REQUESTED,
            title="Nueva solicitud de unión",
            body=(
                "Un representante solicitó unirse a tu organización. "
                "Revisa la solicitud antes de decidir."
            ),
            link=reverse("organization-join-requests"),
        )


@receiver(
    representative_join_approved,
    sender=RepresentativeJoinApproved,
    dispatch_uid="notifications.on_representative_join_approved",
)
def notify_representative_join_approved(sender, *, event, **kwargs):
    recipient = User.objects.filter(pk=event.requester_user_id).first()
    if recipient is None:
        return
    _create_and_deliver(
        recipient=recipient,
        kind=Notification.Kind.REPRESENTATIVE_JOIN_APPROVED,
        title="Tu solicitud de unión fue aprobada",
        body=(
            "El titular aprobó tu vinculación. Podrás operar cuando tu correo "
            "también esté verificado."
        ),
        link=reverse("marketplace:challenge-list"),
    )


@receiver(
    representative_join_rejected,
    sender=RepresentativeJoinRejected,
    dispatch_uid="notifications.on_representative_join_rejected",
)
def notify_representative_join_rejected(sender, *, event, **kwargs):
    recipient = User.objects.filter(pk=event.requester_user_id).first()
    if recipient is None:
        return
    _create_and_deliver(
        recipient=recipient,
        kind=Notification.Kind.REPRESENTATIVE_JOIN_REJECTED,
        title="Tu solicitud de unión fue rechazada",
        body="El titular rechazó tu solicitud de vinculación a la organización.",
        link=reverse("home"),
    )


@receiver(
    representative_join_expired,
    sender=RepresentativeJoinExpired,
    dispatch_uid="notifications.on_representative_join_expired",
)
def notify_representative_join_expired(sender, *, event, **kwargs):
    recipient = User.objects.filter(pk=event.requester_user_id).first()
    if recipient is None:
        return
    _create_and_deliver(
        recipient=recipient,
        kind=Notification.Kind.REPRESENTATIVE_JOIN_EXPIRED,
        title="Tu solicitud de unión expiró",
        body="La solicitud venció sin una decisión y tu cuenta quedó inactiva.",
        link=reverse("home"),
    )


@receiver(
    organization_ownership_transferred,
    sender=OrganizationOwnershipTransferred,
    dispatch_uid="notifications.on_organization_ownership_transferred",
)
def notify_organization_ownership_transferred(sender, *, event, **kwargs):
    recipients = User.objects.operational().filter(
        pk__in={
            event.previous_titular_user_id,
            event.new_titular_user_id,
        }
    )
    for recipient in recipients:
        is_new_titular = recipient.pk == event.new_titular_user_id
        _create_and_deliver(
            recipient=recipient,
            kind=Notification.Kind.ORGANIZATION_OWNERSHIP_TRANSFERRED,
            title=(
                "Ahora eres el representante titular"
                if is_new_titular
                else "Transferiste la titularidad"
            ),
            body=(
                "La transferencia de titularidad de la organización quedó "
                "registrada en la auditoría."
            ),
            link=(
                reverse("organization-join-requests")
                if is_new_titular
                else reverse("home")
            ),
        )
