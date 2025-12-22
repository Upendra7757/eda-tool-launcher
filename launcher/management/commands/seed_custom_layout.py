from django.core.management.base import BaseCommand
from launcher.models import Category, Tool

class Command(BaseCommand):
    help = "Seed Custom Layout tools: KLayout, Magic, Custom Layout Editor"

    def handle(self, *args, **kwargs):

        # Ensure category exists
        category, created = Category.objects.get_or_create(
            slug="custom-layout",
            defaults={"name": "Custom Layout"}
        )

        tools_to_create = [
            {
                "name": "KLayout",
                "slug": "klayout",
                "description": "Open-source IC layout viewer & editor",
                "tool_type": "desktop",
                "windows_executable_path": r"C:\Program Files\KLayout\klayout.exe",
                "linux_executable_path": "/usr/bin/klayout",
                "web_url": "/klayout/web/"  # optional, for future web viewer
            },
            {
                "name": "Magic",
                "slug": "magic",
                "description": "VLSI layout editor used in open-source physical design workflows",
                "tool_type": "desktop",
                "windows_executable_path": "",
                "linux_executable_path": "/usr/bin/magic"
            },
            {
                "name": "Custom Layout Editor",
                "slug": "custom-layout-editor",
                "description": "Internal custom layout editor tool",
                "tool_type": "desktop",
                "windows_executable_path": "",
                "linux_executable_path": ""
            }
        ]

        for tool_data in tools_to_create:
            tool, created = Tool.objects.update_or_create(
                slug=tool_data["slug"],
                defaults={**tool_data, "category": category}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created tool: {tool.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Updated tool: {tool.name}"))

        self.stdout.write(self.style.SUCCESS("Custom Layout tools seeded successfully."))
