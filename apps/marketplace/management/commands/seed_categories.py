from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.marketplace.models import ChallengeCategory


DEFAULT_CATEGORIES = (
    "Agrotech",
    "Salud",
    "Educación",
    "Energía",
    "Sostenibilidad",
    "Industria 4.0",
    "Logística",
    "Fintech",
    "Gobierno digital",
    "Inteligencia artificial",
)


class Command(BaseCommand):
    help = "Seed the initial closed challenge category catalog."

    def handle(self, *args, **options):
        for position, name in enumerate(DEFAULT_CATEGORIES, start=1):
            ChallengeCategory.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "position": position,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS("Challenge categories seeded."))
