from django.db import transaction
from django.utils import timezone

from apps.notifications.models import Notification


@transaction.atomic
def mark_all_notifications_as_read(*, recipient) -> int:
    return Notification.objects.filter(
        recipient=recipient,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
