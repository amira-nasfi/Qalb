from django.urls import path
from .views import PatientCreateView, PatientDetailView

app_name = "patients"

urlpatterns = [
    path("", PatientCreateView.as_view(), name="create"),
    path("<uuid:pseudo_id>/", PatientDetailView.as_view(), name="detail"),
]
