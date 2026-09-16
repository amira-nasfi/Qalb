from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for audit log entries."""

    actor_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "timestamp",
            "actor_label",
            "actor_display",
            "action",
            "target_type",
            "target_id",
            "old_value",
            "new_value",
            "ip_hash",
            "extra",
        ]
        read_only_fields = fields  # audit log is always read-only via API

    def get_actor_display(self, obj) -> str:
        return obj.actor.get_full_name() if obj.actor else obj.actor_label
