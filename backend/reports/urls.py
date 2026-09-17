from django.urls import path
from .views import (
    ReportListView,
    ReportDetailView,
    ReportClaimView,
    ReportRetakeView,
    ReportEmergencyView,
    ReportSignView,
)

app_name = "reports"

urlpatterns = [
    path("", ReportListView.as_view(), name="list"),
    path("<int:pk>/", ReportDetailView.as_view(), name="detail"),
    path("<int:pk>/claim/", ReportClaimView.as_view(), name="claim"),
    path("<int:pk>/retake/", ReportRetakeView.as_view(), name="retake"),
    path("<int:pk>/emergency/", ReportEmergencyView.as_view(), name="emergency"),
    path("<int:pk>/sign/", ReportSignView.as_view(), name="sign"),
]
