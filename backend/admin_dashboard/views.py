from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import timedelta

from ecg.models import ECGRecord
from reports.models import Report
from audit.models import AuditLog, AuditAction
from accounts.permissions import IsAdmin


class KPIDashboardView(APIView):
    """
    GET /api/admin/kpis/
    Returns live metrics for the fixed navbar.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Total ECGs uploaded today
        uploads_today = ECGRecord.objects.filter(
            uploaded_at__gte=today).count()

        # Pending physician reviews
        pending_reviews = Report.objects.filter(
            status=Report.Status.PENDING_REVIEW).count()

        # Signed reports today
        signed_today = Report.objects.filter(
            status=Report.Status.SIGNED,
            signed_at__gte=today).count()

        # Active CRITICAL flags (in pending reports)
        critical_flags = Report.objects.filter(
            status=Report.Status.PENDING_REVIEW,
            severity="CRITICAL"
        ).count()

        # Avg processing time
        # We can estimate it by looking at Process Done audit logs
        recent_done_logs = AuditLog.objects.filter(
            action=AuditAction.PROCESS_DONE,
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).order_by("-timestamp")[:100]

        avg_time = 0
        if recent_done_logs:
            times = [
                log.extra.get("elapsed_ms", 0)
                for log in recent_done_logs
                if log.extra and "elapsed_ms" in log.extra
            ]
            if times:
                avg_time = sum(times) / len(times)

        return Response({
            "uploads_today": uploads_today,
            "pending_reviews": pending_reviews,
            "signed_today": signed_today,
            "critical_active": critical_flags,
            "avg_processing_ms": int(avg_time)
        })
