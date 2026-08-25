from django.core.management.base import BaseCommand
from safety_companion.services import process_wellness_checks

class Command(BaseCommand):
    help = "Prompt due wellness checks and escalate missed checks to guardians."

    def handle(self, *args, **options):
        result = process_wellness_checks()
        self.stdout.write(
            self.style.SUCCESS(
                f"Safety Companion maintenance complete: prompted={result['prompted']} missed={result['missed']}"
            )
        )
