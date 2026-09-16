from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from reports.models import Report
from .builder import build_bundle
from audit.models import AuditLog, AuditAction
from accounts.permissions import IsPhysicianOrAdmin


class FHIRExportView(APIView):
    """
    GET /api/fhir/reports/{id}/
    Returns HL7 FHIR R4 Bundle for a signed report.
    """
    permission_classes = [permissions.IsAuthenticated, IsPhysicianOrAdmin]

    def get(self, request, report_id):
        report = get_object_or_404(Report, pk=report_id)

        # Only SIGNED reports can be exported
        if report.status != Report.Status.SIGNED:
            return Response(
                {"error": "Only signed reports can be exported to FHIR."},
                status=status.HTTP_403_FORBIDDEN
            )

        bundle = build_bundle(report)

        AuditLog.log(
            action=AuditAction.EXPORT_FHIR,
            target_type="Report",
            target_id=report.pk,
            actor=request.user,
            request=request,
        )

        return Response(bundle, content_type="application/fhir+json")
