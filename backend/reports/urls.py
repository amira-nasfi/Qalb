from django.urls import path
from .views import ReportListView, ReportDetailView, ReportSignView

app_name = "reports"

urlpatterns = [
    path("", ReportListView.as_view(), name="list"),
    path("<int:pk>/", ReportDetailView.as_view(), name="detail"),
    path("<int:pk>/sign/", ReportSignView.as_view(), name="sign"),
]
