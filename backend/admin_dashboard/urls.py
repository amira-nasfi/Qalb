from django.urls import path
from .views import KPIDashboardView

app_name = "admin_dashboard"

urlpatterns = [
    path("kpis/", KPIDashboardView.as_view(), name="kpis"),
]
