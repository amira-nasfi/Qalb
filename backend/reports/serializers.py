from rest_framework import serializers
from .models import Report
from ecg.serializers import ProcessingResultSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class PhysicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "username"]


class ReportSerializer(serializers.ModelSerializer):
    """
    Detailed report serializer including the processing result and physician info.
    """
    result = ProcessingResultSerializer(read_only=True)
    signed_by_user = PhysicianSerializer(source="signed_by", read_only=True)
    pseudo_id = serializers.UUIDField(
        source="result.record.patient.pseudo_id",
        read_only=True)
    job_id = serializers.IntegerField(
        source="result.record.id", read_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "job_id", "pseudo_id", "result", "draft_text",
            "physician_notes", "severity", "status",
            "signed_by_user", "signed_at", "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "job_id", "pseudo_id", "result", "draft_text",
            "severity", "status", "signed_by_user", "signed_at",
            "created_at", "updated_at"
        ]


class ReportUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for physician adding notes.
    """
    class Meta:
        model = Report
        fields = ["physician_notes"]

    def update(self, instance, validated_data):
        instance.physician_notes = validated_data.get(
            "physician_notes", instance.physician_notes)
        if instance.status == Report.Status.PENDING_REVIEW:
            instance.status = Report.Status.REVIEWED
        instance.save()
        return instance
