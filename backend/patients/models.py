"""
Patient pseudonymization model.

No PII is stored server-side. The facility retains the link between
the real patient identity and the pseudo_id locally.
"""

import uuid
from django.db import models


class Patient(models.Model):
    """
    Pseudonymized patient record.

    Stores only:
      - pseudo_id  : randomly-generated UUID (no link to real identity server-side)
      - dob_year   : birth year only (not full date of birth)
      - sex        : biological sex (M/F/O) — needed for sex-specific QTc thresholds
      - facility_id: anonymised facility code (not a real facility name)
    """

    pseudo_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text="System-generated pseudonymous identifier. Never maps to real patient name.",
    )
    dob_year = models.PositiveSmallIntegerField(
        help_text="Birth year only. No full date of birth stored.",
    )
    sex = models.CharField(
        max_length=1,
        choices=[("M", "Male"), ("F", "Female"), ("O", "Other/Unknown")],
        help_text="Biological sex — required for sex-specific QTc thresholds (Rautaharju 1992).",
    )
    facility_id = models.CharField(
        max_length=64,
        help_text="Anonymised facility code. Not a real facility name.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Patient (pseudonymized)"

    def __str__(self):
        return f"Patient {self.pseudo_id} ({self.sex}, b.{self.dob_year})"
