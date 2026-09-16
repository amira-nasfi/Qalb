"""
ECG app models — file storage, processing results, and status tracking.
"""

import hashlib
import os
from django.db import models
from django.conf import settings
from patients.models import Patient


class ECGRecord(models.Model):
    """One uploaded ECG file from the field team."""

    class Status(models.TextChoices):
        PENDING    = "PENDING",    "Awaiting processing"
        PROCESSING = "PROCESSING", "Pipeline running"
        DONE       = "DONE",       "Processing complete"
        ERROR      = "ERROR",      "Processing failed"

    class Format(models.TextChoices):
        WFDB = "wfdb", "WFDB (.mat + .hea)"
        CSV  = "csv",  "CSV"
        EDF  = "edf",  "EDF/EDF+"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="ecg_records",
    )
    file = models.FileField(
        upload_to=settings.ECG_UPLOAD_DIR,
        help_text="Raw ECG file. Stored encrypted at rest.",
    )
    file_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 of the uploaded file content.",
    )
    fmt = models.CharField(
        max_length=10,
        choices=Format.choices,
        default=Format.WFDB,
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    fs = models.IntegerField(null=True, blank=True, help_text="Sampling frequency in Hz")
    lead_count = models.IntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"ECG {self.pk} [{self.status}] — patient {self.patient.pseudo_id}"

    def save(self, *args, **kwargs):
        """Compute SHA-256 of file content on first save."""
        if self.pk is None and self.file:
            self.file_hash = self._hash_file()
        super().save(*args, **kwargs)

    def _hash_file(self) -> str:
        sha = hashlib.sha256()
        for chunk in self.file.chunks():
            sha.update(chunk)
        return sha.hexdigest()


class ProcessingResult(models.Model):
    """
    Output of the deterministic signal-processing pipeline for one ECGRecord.
    Stored as JSON snapshots — immutable after creation.
    """

    record = models.OneToOneField(
        ECGRecord,
        on_delete=models.CASCADE,
        related_name="result",
    )
    intervals_json = models.JSONField(
        help_text="Serialised IntervalResult from ecg.pipeline.intervals.",
    )
    flags_json = models.JSONField(
        help_text="List of Flag dicts from ecg.pipeline.rule_engine — each includes citation.",
    )
    severity = models.CharField(
        max_length=10,
        choices=[("ROUTINE", "Routine"), ("URGENT", "Urgent"), ("CRITICAL", "Critical")],
        db_index=True,
    )
    lead_used = models.CharField(max_length=10, default="II")
    partial = models.BooleanField(default=False)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-processed_at"]

    def __str__(self):
        return f"Result for ECG {self.record_id} [{self.severity}]"
