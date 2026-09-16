from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import Report
from .serializers import ReportSerializer, ReportUpdateSerializer
from audit.models import AuditLog, AuditAction


from accounts.permissions import IsPhysician


class ReportListView(generics.ListAPIView):
    """
    GET /api/reports/
    List reports. Physicians see all, field team sees only SIGNED.
    """
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "severity"]
    ordering_fields = ["created_at", "severity"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Report.objects.select_related(
            "result__record__patient", "signed_by").all()
        user = self.request.user
        if getattr(user, 'is_field_agent', False):
            # Field agents only see signed reports
            qs = qs.filter(status=Report.Status.SIGNED)
        return qs


class ReportDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/reports/{id}/
    PATCH /api/reports/{id}/ (physician_notes)
    """
    queryset = Report.objects.select_related(
        "result__record__patient", "signed_by").all()
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if getattr(
            user,
            'is_field_agent',
                False) and obj.status != Report.Status.SIGNED:
            self.permission_denied(
                self.request,
                message="Field agents can only view signed reports.")
        return obj

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return ReportUpdateSerializer
        return ReportSerializer


class ReportSignView(APIView):
    """
    POST /api/reports/{id}/sign/
    Physician electronically signs the report. Irreversible.
    """
    permission_classes = [permissions.IsAuthenticated, IsPhysician]

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)

        if report.status == Report.Status.SIGNED:
            return Response({"error": "Report is already signed"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Must have notes (business logic as per requirements)
        # Actually, let's just enforce it if we want to. Let's assume frontend enforces it.
        # We'll allow empty notes here, or maybe enforce it:
        if not report.physician_notes.strip():
            return Response(
                {
                    "error": "Physician notes cannot be empty before signing"},
                status=status.HTTP_400_BAD_REQUEST)

        report.status = Report.Status.SIGNED
        report.signed_by = request.user
        report.signed_at = timezone.now()
        report.save(
            update_fields=[
                "status",
                "signed_by",
                "signed_at",
                "updated_at"])

        AuditLog.log(
            action=AuditAction.SIGN,
            target_type="Report",
            target_id=report.pk,
            actor=request.user,
            request=request,
            extra={"severity": report.severity},
        )

        return Response(ReportSerializer(report).data)
