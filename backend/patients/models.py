"""
Patient model with HL7 FHIR R4 compliance.
Stores complete patient information associated with ECG records,
and exports directly as a FHIR R4 Patient resource.
"""

import uuid
from django.db import models
from django.utils import timezone


class Patient(models.Model):
    """
    Patient record associated with ECG signals and reports.
    Directly convertible to a standardized HL7 FHIR R4 'Patient' resource.
    """

    pseudo_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text="System-generated unique identifier (used as FHIR resource id).",
    )
    patient_identifier = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Official Patient Identifier / IPP.",
    )
    first_name = models.CharField(max_length=120, blank=True, default="")
    last_name = models.CharField(max_length=120, blank=True, default="")
    birth_date = models.DateField(null=True, blank=True)
    dob_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Birth year (derived from birth_date or specified directly).",
    )
    sex = models.CharField(
        max_length=1,
        choices=[("M", "Male"), ("F", "Female"), ("O", "Other/Unknown")],
        default="M",
        help_text="Biological sex — required for sex-specific QTc thresholds (Rautaharju 1992).",
    )
    gender = models.CharField(
        max_length=16,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other"), ("unknown", "Unknown")],
        default="male",
        help_text="FHIR R4 compliant gender.",
    )
    facility_id = models.CharField(
        max_length=64,
        blank=True,
        default="DISP-CENTRE-01",
        help_text="Health facility / dispensary code.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Patient"
        verbose_name_plural = "Patients"

    def __str__(self):
        return f"{self.full_name} ({self.patient_identifier or self.pseudo_id})"

    def save(self, *args, **kwargs):
        # Synchronize birth_date and dob_year
        if self.birth_date and not self.dob_year:
            self.dob_year = self.birth_date.year
        elif self.dob_year and not self.birth_date:
            import datetime
            self.birth_date = datetime.date(self.dob_year, 1, 1)

        # Synchronize sex and gender
        if self.gender == "male":
            self.sex = "M"
        elif self.gender == "female":
            self.sex = "F"
        elif self.sex == "M":
            self.gender = "male"
        elif self.sex == "F":
            self.gender = "female"

        super().save(*args, **kwargs)

    @property
    def full_name(self) -> str:
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return f"Patient {str(self.pseudo_id)[:8]}"

    @property
    def age(self) -> int | None:
        today = timezone.now().date()
        if self.birth_date:
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        if self.dob_year:
            return today.year - self.dob_year
        return None

    def to_fhir_resource(self) -> dict:
        """
        Builds a standard HL7 FHIR R4 'Patient' resource.
        """
        resource = {
            "resourceType": "Patient",
            "id": str(self.pseudo_id),
            "identifier": [
                {
                    "system": "https://qalb.health/patients",
                    "value": self.patient_identifier or f"PAT-{str(self.pseudo_id)[:8].upper()}"
                }
            ],
            "name": [
                {
                    "use": "official",
                    "family": self.last_name or "Anonyme",
                    "given": [self.first_name] if self.first_name else ["Patient"]
                }
            ],
            "gender": self.gender or ("male" if self.sex == "M" else "female" if self.sex == "F" else "other"),
        }

        if self.birth_date:
            resource["birthDate"] = self.birth_date.isoformat()
        elif self.dob_year:
            resource["birthDate"] = f"{self.dob_year}-01-01"

        return resource
