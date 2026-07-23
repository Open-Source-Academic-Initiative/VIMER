from apps.notifications.models import Notification


def notifications_summary(request):
    if not request.user.is_authenticated or not request.user.can_operate:
        return {"notifications_unread_count": 0}

    return {
        "notifications_unread_count": Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()
    }
