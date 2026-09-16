from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from .models import AuditLog
from .serializers import AuditLogSerializer


class IsAdminUser(permissions.BasePermission):
    """Only superusers or staff can view the audit log."""

    def has_permission(self, request, view):
        return bool(
            request.user and (
                request.user.is_staff or request.user.is_superuser))


class AuditLogListView(generics.ListAPIView):
    """
    GET /api/audit/
    Paginated, filterable audit log.
    Admin/staff only. Append-only — no create/update/delete via API.

    Query params:
      ?action=SIGN
      ?target_type=Report
      ?actor_label=physician1
      ?ordering=-timestamp
      ?search=QTC_CRITICAL
    """
    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ["action", "target_type", "actor_label"]
    ordering_fields = ["timestamp", "action", "target_type"]
    ordering = ["-timestamp"]
    search_fields = ["actor_label", "target_id", "extra"]


class AuditLogDetailView(generics.RetrieveAPIView):
    """
    GET /api/audit/{id}/
    Single audit log entry with full before/after snapshots.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
