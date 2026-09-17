from django.urls import path
from .views import PatientListCreateView, PatientDetailView

app_name = "patients"

urlpatterns = [
    path("", PatientListCreateView.as_view(), name="list_create"),
    path("<uuid:pseudo_id>/", PatientDetailView.as_view(), name="detail"),
]
