from rest_framework import serializers
from .models import Report
from ecg.serializers import ProcessingResultSerializer
from patients.serializers import PatientSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class PhysicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "username"]


class ReportSerializer(serializers.ModelSerializer):
    """
    Detailed report serializer including processing result, patient info, and physician info.
    """
    result = ProcessingResultSerializer(read_only=True)
    signed_by_user = PhysicianSerializer(source="signed_by", read_only=True)
    claimed_by_user = PhysicianSerializer(source="claimed_by", read_only=True)
    pseudo_id = serializers.UUIDField(
        source="result.record.patient.pseudo_id",
        read_only=True)
    job_id = serializers.IntegerField(
        source="result.record.id", read_only=True)
    patient = PatientSerializer(source="result.record.patient", read_only=True)
    patient_identifier = serializers.CharField(
        source="result.record.patient.patient_identifier", read_only=True)
    patient_name = serializers.CharField(
        source="result.record.patient.full_name", read_only=True)
    patient_age = serializers.IntegerField(
        source="result.record.patient.age", read_only=True)
    patient_gender = serializers.CharField(
        source="result.record.patient.gender", read_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "job_id", "pseudo_id", "patient", "patient_identifier",
            "patient_name", "patient_age", "patient_gender",
            "result", "draft_text", "physician_notes", "severity", "status",
            "claimed_by_user", "claimed_at",
            "retake_reason", "emergency_notes",
            "signed_by_user", "signed_at", "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "job_id", "pseudo_id", "patient", "patient_identifier",
            "patient_name", "patient_age", "patient_gender",
            "result", "draft_text", "severity", "status",
            "claimed_by_user", "claimed_at",
            "retake_reason", "emergency_notes",
            "signed_by_user", "signed_at", "created_at", "updated_at"
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
            instance.status = Report.Status.IN_REVIEW
        instance.save()
        return instance
