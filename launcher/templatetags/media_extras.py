from django import template
from django.conf import settings
from pathlib import Path

register = template.Library()

@register.filter
def absolute_media(path):
    return Path(settings.MEDIA_ROOT, path)
