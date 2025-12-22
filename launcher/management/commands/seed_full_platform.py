from django.core.management.base import BaseCommand
from launcher.models import Category, Tool, EnvConfig, License
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
import os

class Command(BaseCommand):
    help = "Seed categories, tools (including Verilator), envs and licenses"

    def handle(self, *args, **options):
        # categories
        cats = [
            "Custom Layout",
            "Circuit Design / Characterization",
            "Physical Designing",
            "Memory IP",
            "Analog IP",
            "Std Cell Library",
            "Simulation / RTL Verification"
        ]
        for name in cats:
            slug = slugify(name)
            cat, _ = Category.objects.get_or_create(name=name, slug=slug)

        # Add Verilator
        sim_cat = Category.objects.get(slug='simulation-rtl-verification')
        ver_tool, created = Tool.objects.get_or_create(
            name='Verilator',
            slug='verilator',
            category=sim_cat,
            defaults={
                'description': 'Verilator - fast open-source SystemVerilog/Verilog simulator',
                'tool_type': 'desktop',
                'executable_path': r'C:\msys64\mingw64\bin\verilator.cmd',
                'env_template': {}
            }
        )
        if created:
            self.stdout.write("Created Verilator tool")

        # add sample license
        License.objects.get_or_create(tool=ver_tool, pool_size=10, expiry_date=timezone.now() + timedelta(days=30), status='available')

        # sample env
        EnvConfig.objects.get_or_create(tool=ver_tool, name='Default', vars={}, is_default=True)

        self.stdout.write(self.style.SUCCESS("Seeding completed."))
