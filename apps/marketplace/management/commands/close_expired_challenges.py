from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.marketplace.application.challenges import close_expired_challenge
from apps.marketplace.models import Challenge


class Command(BaseCommand):
    help = (
        "Cierra de forma idempotente desafíos publicados cuyo plazo de "
        "recepción ya venció."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Máximo de desafíos a procesar en esta ejecución.",
        )

    def handle(self, *args, **options):
        challenge_ids = Challenge.objects.filter(
            status=Challenge.Status.PUBLISHED,
            application_deadline__lt=timezone.localdate(),
        ).order_by("application_deadline", "pk").values_list("pk", flat=True)
        if options["limit"] is not None:
            challenge_ids = challenge_ids[: max(options["limit"], 0)]

        closed_count = 0
        for challenge_id in challenge_ids.iterator():
            if close_expired_challenge(challenge_id=challenge_id) is not None:
                closed_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Desafíos cerrados automáticamente: {closed_count}."
            )
        )
