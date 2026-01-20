"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Launcher app
    path("", include("launcher.urls")),
]

# Serve uploaded files (VCDs, logs) in dev
if settings.DEBUG:
    urlpatterns += static("/uploads/", document_root=settings.BASE_DIR / "uploads")
    urlpatterns += static(
    "/uploads/",
    document_root=settings.BASE_DIR
)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("launcher.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

"""
urlpatterns = [
    path("admin/", admin.site.urls),

    # Launcher app
    path("", include("launcher.urls")),
]

# ✅ Serve run artifacts (PNG, metadata, logs) in dev
if settings.DEBUG:
    urlpatterns += static(
    "/uploads/",
    document_root=settings.BASE_DIR / "uploads"
    )
"""



