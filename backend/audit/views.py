from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from .models import AuditLog
from .serializers import AuditLogSerializer


from accounts.permissions import IsAdmin


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
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
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
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
