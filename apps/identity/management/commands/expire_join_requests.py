from django.core.management.base import BaseCommand

from apps.identity.application.services import expire_pending_organization_join_requests


class Command(BaseCommand):
    help = "Expire pending organization join requests whose deadline has passed."

    def handle(self, *args, **options):
        count = expire_pending_organization_join_requests()
        self.stdout.write(self.style.SUCCESS(f"Expired {count} join requests."))
