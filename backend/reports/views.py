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
    List reports. Physicians see all, field agents see only SIGNED.
    """
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "severity"]
    ordering_fields = ["created_at", "severity"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Report.objects.select_related(
            "result__record__patient", "signed_by", "claimed_by").all()
        user = self.request.user
        if getattr(user, 'is_field_agent', False):
            # Practitioners see:
            # - SIGNED: validated report, readable
            # - RETAKE_REQUESTED: they must re-record the ECG
            # - EMERGENCY_TRANSFER: they must call SAMU immediately
            qs = qs.filter(status__in=[
                Report.Status.SIGNED,
                Report.Status.RETAKE_REQUESTED,
                Report.Status.EMERGENCY_TRANSFER,
            ])
        return qs


class ReportDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/reports/{id}/
    PATCH /api/reports/{id}/ (physician_notes)
    """
    queryset = Report.objects.select_related(
        "result__record__patient", "signed_by", "claimed_by").all()
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        PRACTITIONER_VISIBLE = {
            Report.Status.SIGNED,
            Report.Status.RETAKE_REQUESTED,
            Report.Status.EMERGENCY_TRANSFER,
        }
        if getattr(user, 'is_field_agent', False) and obj.status not in PRACTITIONER_VISIBLE:
            self.permission_denied(
                self.request,
                message="Praticiens : accès limité aux dossiers validés, en réacquisition ou en urgence SAMU.")
        return obj

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return ReportUpdateSerializer
        return ReportSerializer


class ReportClaimView(APIView):
    """
    POST /api/reports/{id}/claim/
    Physician takes ownership of the case (tele-interpretation).
    Idempotent: if already claimed by same doctor, returns 200.
    """
    permission_classes = [permissions.IsAuthenticated, IsPhysician]

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)

        if report.status == Report.Status.SIGNED:
            return Response(
                {"error": "Ce dossier est déjà signé et clôturé."},
                status=status.HTTP_400_BAD_REQUEST)

        if report.status == Report.Status.IN_REVIEW and report.claimed_by != request.user:
            return Response(
                {"error": "Ce dossier est déjà pris en charge par un autre médecin."},
                status=status.HTTP_409_CONFLICT)

        report.status = Report.Status.IN_REVIEW
        report.claimed_by = request.user
        report.claimed_at = timezone.now()
        report.save(update_fields=["status", "claimed_by", "claimed_at", "updated_at"])

        AuditLog.log(
            action=AuditAction.SIGN,  # reuse closest action
            target_type="Report",
            target_id=report.pk,
            actor=request.user,
            request=request,
            extra={"action": "claim", "severity": report.severity},
        )

        return Response(ReportSerializer(report).data)


class ReportRetakeView(APIView):
    """
    POST /api/reports/{id}/retake/
    Physician requests ECG re-acquisition with a technical reason.
    Body: { "reason": "..." }
    """
    permission_classes = [permissions.IsAuthenticated, IsPhysician]

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"error": "Un motif technique est requis pour demander une réacquisition."},
                status=status.HTTP_400_BAD_REQUEST)

        report.status = Report.Status.RETAKE_REQUESTED
        report.retake_reason = reason
        report.save(update_fields=["status", "retake_reason", "updated_at"])

        AuditLog.log(
            action=AuditAction.SIGN,
            target_type="Report",
            target_id=report.pk,
            actor=request.user,
            request=request,
            extra={"action": "retake_requested", "reason": reason},
        )

        return Response(ReportSerializer(report).data)


class ReportEmergencyView(APIView):
    """
    POST /api/reports/{id}/emergency/
    Physician triggers a vital emergency alert (SAMU escalation).
    Body: { "notes": "..." }
    """
    permission_classes = [permissions.IsAuthenticated, IsPhysician]

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)

        notes = request.data.get("notes", "").strip()
        if not notes:
            return Response(
                {"error": "Des consignes d'urgence sont requises pour déclencher une alerte SAMU."},
                status=status.HTTP_400_BAD_REQUEST)

        report.status = Report.Status.EMERGENCY_TRANSFER
        report.emergency_notes = notes
        # Also sign at this point to lock the report
        report.signed_by = request.user
        report.signed_at = timezone.now()
        report.save(update_fields=[
            "status", "emergency_notes", "signed_by", "signed_at", "updated_at"])

        AuditLog.log(
            action=AuditAction.SIGN,
            target_type="Report",
            target_id=report.pk,
            actor=request.user,
            request=request,
            extra={"action": "emergency_samu", "severity": report.severity},
        )

        return Response(ReportSerializer(report).data)


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
