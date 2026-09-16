from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
import numpy as np

from patients.models import Patient
from .models import ECGRecord, ProcessingResult
from .serializers import ECGUploadSerializer, ECGStatusSerializer, ProcessingResultSerializer
from .tasks import process_ecg_task
from accounts.permissions import IsFieldAgentOrPhysician


class ECGUploadView(generics.CreateAPIView):
    """
    POST /api/ecg/upload/
    Uploads an ECG file, creates an ECGRecord, and enqueues Celery processing.
    """
    queryset = ECGRecord.objects.all()
    serializer_class = ECGUploadSerializer
    permission_classes = [permissions.IsAuthenticated, IsFieldAgentOrPhysician]

    def create(self, request, *args, **kwargs):
        # Validate patient exists
        pseudo_id = request.data.get("pseudo_id")
        if not Patient.objects.filter(pseudo_id=pseudo_id).exists():
            return Response({"error": "Patient not found"},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()

        # Enqueue Celery task
        process_ecg_task.delay(record.pk)

        status_url = request.build_absolute_uri(
            f"/api/ecg/{record.pk}/status/")
        return Response({
            "job_id": record.pk,
            "status_url": status_url,
            "status": record.status,
        }, status=status.HTTP_201_CREATED)


class ECGStatusView(generics.RetrieveAPIView):
    """
    GET /api/ecg/{job_id}/status/
    Poll for pipeline completion.
    """
    queryset = ECGRecord.objects.all()
    serializer_class = ECGStatusSerializer
    permission_classes = [permissions.IsAuthenticated]


class ECGResultView(generics.RetrieveAPIView):
    """
    GET /api/ecg/{job_id}/result/
    Full computed intervals and flags.
    """
    queryset = ProcessingResult.objects.all()
    serializer_class = ProcessingResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "record_id"


class ECGSignalView(APIView):
    """
    GET /api/ecg/{job_id}/signal/?lead=II&downsample=500
    Returns downsampled ECG signal for frontend chart rendering.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, record_id):
        record = get_object_or_404(ECGRecord, pk=record_id)
        if record.status != "DONE":
            return Response({"error": "Processing not complete"},
                            status=status.HTTP_400_BAD_REQUEST)

        lead_name = request.query_params.get("lead", "II")
        downsample = int(
            request.query_params.get(
                "downsample",
                settings.ECG_DOWNSAMPLE_POINTS))

        # Load the file to serve the signal (raw arrays not stored in DB)
        from .pipeline.loader import load_ecg
        from .pipeline.preprocessing import preprocess

        try:
            signals, fs, metadata = load_ecg(record.file.path, record.fmt)
            signals_clean = preprocess(signals, fs)
        except Exception as exc:
            return Response({"error": str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        lead_names = metadata["lead_names"]
        if lead_name not in lead_names:
            return Response({"error": f"Lead {lead_name} not found"},
                            status=status.HTTP_404_NOT_FOUND)

        lead_idx = lead_names.index(lead_name)
        lead_signal = signals_clean[lead_idx]

        # Downsample for frontend chart
        n_samples = len(lead_signal)
        if n_samples > downsample > 0:
            indices = np.linspace(0, n_samples - 1, downsample, dtype=int)
            lead_signal_ds = lead_signal[indices]
            fs_display = fs * (downsample / n_samples)
        else:
            lead_signal_ds = lead_signal
            indices = np.arange(n_samples)
            fs_display = fs

        # Get R-peaks if available to overlay on chart
        r_peaks_ds = []
        try:
            result = record.result
            if "r_peaks" in result.intervals_json:
                pass  # R-peaks not stored as raw arrays; frontend uses simplified approach
        except ProcessingResult.DoesNotExist:
            pass

        # Quick R-peak detection on signal for UI markers
        import neurokit2 as nk
        try:
            _, info = nk.ecg_peaks(
                lead_signal, sampling_rate=fs, method="pantompkins1985")
            r_peaks_original = info["ECG_R_Peaks"]
            # Map original indices to downsampled indices
            r_peaks_ds = [np.argmin(np.abs(indices - r))
                          for r in r_peaks_original]
        except Exception:
            r_peaks_ds = []

        return Response({
            "samples": lead_signal_ds.tolist(),
            "r_peaks": [int(x) for x in r_peaks_ds],
            "fs_display": fs_display,
            "unit": "mV"
        })
