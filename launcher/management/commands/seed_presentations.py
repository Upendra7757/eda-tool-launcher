from django.core.management.base import BaseCommand
from launcher.models import PresentationTemplate, PresentationTheme


class Command(BaseCommand):
    help = "Seed default presentation templates and themes"

    def handle(self, *args, **kwargs):

        templates = [
            ("standard", "Standard Review", "Default technical review", "launcher/presentation/detail.html"),
            ("engineering", "Engineering Focus", "Deep technical layout", "launcher/presentation/detail_engineering.html"),
            ("executive", "Executive Summary", "High-level executive view", "launcher/presentation/detail_executive.html"),
            ("darkboard", "Dark Boardroom", "Dark professional layout", "launcher/presentation/detail_dark.html"),
        ]

        for key, name, desc, tpl in templates:
            PresentationTemplate.objects.get_or_create(
                key=key,
                defaults={
                    "name": name,
                    "description": desc,
                    "base_template": tpl,
                }
            )

        themes = [
            ("dark", "Dark Pro", "css/themes/dark.css"),
            ("light", "Light Clean", "css/themes/light.css"),
            ("blueprint", "Blueprint", "css/themes/blueprint.css"),
        ]

        for key, name, css in themes:
            PresentationTheme.objects.get_or_create(
                key=key,
                defaults={
                    "name": name,
                    "css_file": css,
                }
            )

        self.stdout.write(self.style.SUCCESS("Presentation templates & themes seeded"))
