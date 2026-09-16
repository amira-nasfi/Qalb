from django.urls import path
from .views import FHIRExportView

app_name = "fhir_export"

urlpatterns = [
    path("reports/<int:report_id>/", FHIRExportView.as_view(), name="export"),
]
