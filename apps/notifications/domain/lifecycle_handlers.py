from django.dispatch import receiver

from apps.identity.models import User
from apps.marketplace.domain.events import ChallengeLifecycleChanged
from apps.marketplace.domain.signals import challenge_lifecycle_changed
from apps.marketplace.models import Challenge, ChallengeLifecycleEvent
from apps.notifications.domain.handlers import (
    _build_challenge_link,
    send_notification_email,
)
from apps.notifications.models import Notification


@receiver(
    challenge_lifecycle_changed,
    sender=ChallengeLifecycleChanged,
    dispatch_uid="notifications.on_challenge_lifecycle_changed",
)
def create_notifications_for_challenge_lifecycle_change(
    sender,
    *,
    event,
    **kwargs,
):
    notification_configuration = {
        ChallengeLifecycleEvent.EventType.CLOSED: (
            Notification.Kind.CHALLENGE_CLOSED,
            "Cerró la recepción de propuestas",
            "cerró la recepción de propuestas",
        ),
        ChallengeLifecycleEvent.EventType.CANCELLED: (
            Notification.Kind.CHALLENGE_CANCELLED,
            "El desafío fue cancelado",
            "fue cancelado",
        ),
        ChallengeLifecycleEvent.EventType.DESERTED: (
            Notification.Kind.CHALLENGE_DESERTED,
            "El desafío fue declarado desierto",
            "fue declarado desierto",
        ),
    }.get(event.event_type)
    if notification_configuration is None:
        return

    kind, title, action = notification_configuration
    challenge = Challenge.objects.get(pk=event.challenge_id)
    participant_organization_ids = set(
        challenge.applications.submitted().values_list(
            "applicant_id",
            flat=True,
        )
    )
    participant_organization_ids.add(challenge.publisher_id)
    recipients = User.objects.operational().filter(
        organization_id__in=participant_organization_ids
    )
    notifications = [
        Notification(
            recipient=recipient,
            kind=kind,
            title=title,
            body=f"El desafío '{challenge.title}' {action}.",
            link=_build_challenge_link(challenge.pk),
        )
        for recipient in recipients
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
        for notification in notifications:
            send_notification_email(notification)
