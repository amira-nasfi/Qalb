"""Root URL configuration for Qalb قلب backend."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django built-in admin (superuser only)
    path("django-admin/", admin.site.urls),

    # ── Qalb API ──────────────────────────────────────────────────────────────
    path("api/",                include("accounts.urls")),
    path("api/patients/",       include("patients.urls")),
    path("api/ecg/",            include("ecg.urls")),
    path("api/reports/",        include("reports.urls")),
    path("api/fhir/",           include("fhir_export.urls")),
    # Admin dashboard API (separate app — not a redirect to django-admin)
    path("api/admin/",          include("admin_dashboard.urls")),
    # Audit log API (accessible from admin dashboard)
    path("api/audit/",          include("audit.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
