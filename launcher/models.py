from django.db import models
from django.contrib.auth import get_user_model
import uuid


User = get_user_model()


# -----------------------------------------------------
# Category Model
# -----------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True)

    def __str__(self):
        return self.name


# -----------------------------------------------------
# Tool Model
# -----------------------------------------------------
class Tool(models.Model):
    TOOL_TYPES = [
        ('desktop', 'Desktop'),
        ('web', 'Web')
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='tools')
    description = models.TextField(blank=True)

    tool_type = models.CharField(max_length=20, choices=TOOL_TYPES, default='desktop')

    # Generic executable path (optional)
    executable_path = models.CharField(max_length=1000, blank=True)

    # NEW — OS-specific paths
    linux_executable_path = models.CharField(max_length=1000, blank=True)
    windows_executable_path = models.CharField(max_length=1000, blank=True)
    web_url = models.CharField(max_length=1000, blank=True)

    requires_license = models.BooleanField(default=False)

    env_template = models.JSONField(default=dict, blank=True)
    icon = models.CharField(max_length=200, blank=True, null=True)
    visible = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# -----------------------------------------------------
# License Pool Model
# -----------------------------------------------------
class License(models.Model):
    STATUS = [
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('expired', 'Expired')
    ]

    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name='licenses')
    pool_size = models.IntegerField(default=1)
    active_count = models.IntegerField(default=0)
    expiry_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS, default='available')

    def __str__(self):
        return f"{self.tool.name} License Pool"


# -----------------------------------------------------
# License Allocation Model
# -----------------------------------------------------
class LicenseAllocation(models.Model):
    STATUS = [
        ('active', 'Active'),
        ('released', 'Released'),
    ]

    id = models.AutoField(primary_key=True)
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='allocations')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS, default='active')

    def __str__(self):
        return f"{self.license.tool.name} → {self.user}"


# -----------------------------------------------------
# Environment Configuration Model
# -----------------------------------------------------
class EnvConfig(models.Model):
    id = models.AutoField(primary_key=True)
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name='envs')
    name = models.CharField(max_length=100)
    vars = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.tool.name} - {self.name}"
"""
class ToolRun(models.Model):
    STATUS = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('running', 'Running'),
    ]

    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name='runs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    input_file = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='running'
    )

    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tool.name} run @ {self.created_at}"


# =====================================================
# PHASE 2 — KLAYOUT METADATA (OPTIONAL, SAFE)
# =====================================================
class LayoutMetadata(models.Model):
    run = models.OneToOneField(
        ToolRun,
        on_delete=models.CASCADE,
        related_name='layout_metadata'
    )

    cell_count = models.IntegerField(null=True, blank=True)
    bbox = models.JSONField(null=True, blank=True)
    layers = models.JSONField(null=True, blank=True)
    dbu = models.FloatField(null=True, blank=True)

    png_preview = models.CharField(
        max_length=255,
        blank=True,
        help_text="Path to generated PNG preview"
    )

    def __str__(self):
        return f"Layout metadata for run {self.run.id}"
"""
class ToolRun(models.Model):
    STATUS = [
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name="runs"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    input_file = models.CharField(max_length=255, blank=True)
    run_dir = models.CharField(max_length=500,blank=True,default="")

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="running"
    )

    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tool.name} run @ {self.created_at}"


# =====================================================
# KLAYOUT METADATA (PHASE 2)
# =====================================================
class LayoutMetadata(models.Model):
    run = models.OneToOneField(
        ToolRun,
        on_delete=models.CASCADE,
        related_name="layout_metadata"
    )

    cell_count = models.IntegerField(null=True, blank=True)
    dbu = models.FloatField(null=True, blank=True)

    bbox = models.JSONField(
        null=True,
        blank=True,
        help_text="Layout bounding box"
    )

    layers = models.JSONField(
        null=True,
        blank=True,
        help_text="List of layers"
    )

    png_preview = models.CharField(
        max_length=255,
        blank=True,
        help_text="Path to generated PNG preview"
    )

    def __str__(self):
        return f"Layout metadata for run {self.run.id}"
    
# =====================================================
# DESIGN REVIEW / PRESENTATION MODEL
# =====================================================
from django.db import models
from django.contrib.auth.models import User


class PresentationTemplate(models.Model):
    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    base_template = models.CharField(
        max_length=200,
        help_text="Example: launcher/presentation/detail.html"
    )

    def __str__(self):
        return self.name


class PresentationTheme(models.Model):
    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    css_file = models.CharField(
        max_length=200,
        help_text="Example: css/themes/dark.css"
    )

    def __str__(self):
        return self.name


class Presentation(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    run = models.ForeignKey(
        "ToolRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="presentations"
    )

    template = models.ForeignKey(
        PresentationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="presentations"
    )

    theme = models.ForeignKey(
        PresentationTheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="presentations"
    )

    def __str__(self):
        return self.title

class Slide(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    presentation = models.ForeignKey(
        Presentation,
        on_delete=models.CASCADE,
        related_name="slides"
    )

    title = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.presentation.title} - Slide {self.order}"

from django.conf import settings

class RunArtifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    run = models.ForeignKey(
        "ToolRun",
        on_delete=models.CASCADE,
        related_name="artifacts"
    )

    artifact_type = models.CharField(
        max_length=30,
        choices=[
            ("image", "Image"),
            ("metadata", "Metadata"),
            ("log", "Log"),
            ("gds", "GDS"),
            ("report", "Report"),
        ]
    )

    name = models.CharField(max_length=255)

    # MUST be relative to MEDIA_ROOT
    file_path = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def media_url(self):
        """
        URL for templates <img src=...>
        """
        return f"{settings.MEDIA_URL}{self.file_path}"

    def absolute_path(self):
        """
        Filesystem path for reading logs / json
        """
        return settings.MEDIA_ROOT / self.file_path

    def __str__(self):
        return f"{self.artifact_type}: {self.name}"


class SlideItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    slide = models.ForeignKey(
        Slide,
        on_delete=models.CASCADE,
        related_name="items"
    )

    artifact = models.ForeignKey(
        RunArtifact,
        on_delete=models.CASCADE
    )

    item_type = models.CharField(
        max_length=20,
        choices=[
            ("image", "Image"),
            ("log_snippet", "Log Snippet"),
            ("attachment", "Attachment"),
        ]
    )

    config = models.JSONField(blank=True, null=True)
    # Example:
    # {
    #   "log_start": 120,
    #   "log_end": 180,
    #   "zoom": 2.0,
    #   "note": "Timing issue here"
    # }

    def __str__(self):
        return f"{self.item_type} on {self.slide}"
