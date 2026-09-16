from django.urls import path
from .views import ECGUploadView, ECGStatusView, ECGResultView, ECGSignalView

app_name = "ecg"

urlpatterns = [
    path("upload/", ECGUploadView.as_view(), name="upload"),
    path("<int:pk>/status/", ECGStatusView.as_view(), name="status"),
    path("<int:record_id>/result/", ECGResultView.as_view(), name="result"),
    path("<int:record_id>/signal/", ECGSignalView.as_view(), name="signal"),
]
