from rest_framework import serializers
from .models import ECGRecord, ProcessingResult


class ECGUploadSerializer(serializers.ModelSerializer):
    """Serializer for ECG file upload."""
    pseudo_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ECGRecord
        fields = ["pseudo_id", "file", "fmt"]

    def create(self, validated_data):
        from patients.models import Patient
        pseudo_id = validated_data.pop("pseudo_id")
        patient = Patient.objects.get(pseudo_id=pseudo_id)
        return ECGRecord.objects.create(patient=patient, **validated_data)


class ECGStatusSerializer(serializers.ModelSerializer):
    """Lightweight status polling response."""
    result_url = serializers.SerializerMethodField()

    class Meta:
        model = ECGRecord
        fields = ["id", "status", "error_message", "uploaded_at", "result_url"]

    def get_result_url(self, obj) -> str | None:
        if obj.status == "DONE":
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(f"/api/ecg/{obj.pk}/result/")
        return None


class ProcessingResultSerializer(serializers.ModelSerializer):
    """Full processing result with intervals and flags."""
    class Meta:
        model = ProcessingResult
        fields = [
            "id", "record_id", "intervals_json", "flags_json",
            "severity", "lead_used", "partial", "processed_at",
        ]
        read_only_fields = fields
