from rest_framework import generics, permissions
from .models import Patient
from .serializers import PatientSerializer


class PatientCreateView(generics.CreateAPIView):
    """
    POST /api/patients/
    Register a new pseudonymized patient. Returns a system-generated pseudo_id.
    No personal identifiers accepted or stored.
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]


class PatientDetailView(generics.RetrieveAPIView):
    """
    GET /api/patients/{pseudo_id}/
    Retrieve patient metadata by pseudo_id.
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pseudo_id"
