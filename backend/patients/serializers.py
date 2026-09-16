from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer for Patient. Exposes only pseudonymized fields.
    Never exposes name, address, or any PII.
    """

    class Meta:
        model = Patient
        fields = ["pseudo_id", "dob_year", "sex", "facility_id", "created_at"]
        read_only_fields = ["pseudo_id", "created_at"]
