from rest_framework import generics, permissions, filters
from .models import Patient
from .serializers import PatientSerializer


class PatientListCreateView(generics.ListCreateAPIView):
    """
    GET /api/patients/ - List patients with search.
    POST /api/patients/ - Register a new patient.
    """
    queryset = Patient.objects.all().order_by("-created_at")
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["patient_identifier", "last_name", "first_name", "pseudo_id"]


class PatientDetailView(generics.RetrieveAPIView):
    """
    GET /api/patients/{pseudo_id}/
    Retrieve patient metadata by pseudo_id.
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pseudo_id"
