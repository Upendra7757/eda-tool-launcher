from django.db import models
from django.contrib.auth import get_user_model

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
