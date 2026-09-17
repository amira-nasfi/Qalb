"""
Draft report and physician workflow model.
"""

from django.db import models
from django.contrib.auth import get_user_model
from ecg.models import ProcessingResult

User = get_user_model()


class Report(models.Model):
    """
    A clinical report derived from the ECG pipeline results,
    awaiting or having received physician sign-off via tele-interpretation.
    """

    class Status(models.TextChoices):
        PENDING_REVIEW = "PENDING_REVIEW", "En attente d'attribution"
        IN_REVIEW = "IN_REVIEW", "Pris en charge (en cours d'analyse)"
        SIGNED = "SIGNED", "Validé et signé électroniquement"
        RETAKE_REQUESTED = "RETAKE_REQUESTED", "Réacquisition demandée"
        EMERGENCY_TRANSFER = "EMERGENCY_TRANSFER", "Urgence SAMU déclenchée"

    result = models.OneToOneField(
        ProcessingResult,
        on_delete=models.CASCADE,
        related_name="report",
    )
    draft_text = models.TextField(
        help_text="Auto-generated clinical summary based on flags.",
    )
    physician_notes = models.TextField(
        blank=True,
        help_text="Manual notes added by the reviewing physician.",
    )
    severity = models.CharField(
        max_length=10,
        choices=[("ROUTINE", "Routine"), ("URGENT", "Urgent"), ("CRITICAL", "Critical")],
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_REVIEW,
        db_index=True,
    )

    # Tele-interpretation: claiming
    claimed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claimed_reports",
        help_text="Physician who took ownership of this case.",
    )
    claimed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp when the case was claimed.",
    )

    # Tele-interpretation: signing
    signed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="signed_reports",
    )
    signed_at = models.DateTimeField(null=True, blank=True)

    # Tele-interpretation: retake request
    retake_reason = models.TextField(
        blank=True,
        help_text="Technical reason for requesting ECG re-acquisition.",
    )

    # Tele-interpretation: SAMU emergency
    emergency_notes = models.TextField(
        blank=True,
        help_text="Immediate instructions transmitted to field team in case of vital emergency.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report {self.pk} [{self.status}] — {self.severity}"
