from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer for Patient with full demographic and FHIR-compliant fields.
    """
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "pseudo_id",
            "patient_identifier",
            "first_name",
            "last_name",
            "full_name",
            "birth_date",
            "dob_year",
            "age",
            "sex",
            "gender",
            "facility_id",
            "created_at",
        ]
        read_only_fields = ["pseudo_id", "full_name", "age", "created_at"]
