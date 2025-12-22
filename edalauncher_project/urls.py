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
