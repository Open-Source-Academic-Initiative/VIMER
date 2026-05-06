from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.identity.models import OrganizationJoinRequest, User


class Command(BaseCommand):
    help = "Expire pending organization join requests whose deadline has passed."

    def handle(self, *args, **options):
        expired_requests = OrganizationJoinRequest.objects.filter(
            status=OrganizationJoinRequest.Status.PENDING,
            expires_at__lt=timezone.now(),
        ).select_related("requester")
        count = 0
        for join_request in expired_requests:
            join_request.status = OrganizationJoinRequest.Status.EXPIRED
            join_request.decided_at = timezone.now()
            join_request.save(update_fields=["status", "decided_at"])
            join_request.requester.status = User.AccountStatus.INACTIVE
            join_request.requester.save(update_fields=["status"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Expired {count} join requests."))
