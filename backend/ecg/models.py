"""
ECG app models — file storage, processing results, and status tracking.
"""

import hashlib
from django.db import models
from django.conf import settings
from patients.models import Patient


class ECGRecord(models.Model):
    """One uploaded ECG file from the field team."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Awaiting processing"
        PROCESSING = "PROCESSING", "Pipeline running"
        DONE = "DONE", "Processing complete"
        ERROR = "ERROR", "Processing failed"

    class Format(models.TextChoices):
        WFDB = "wfdb", "WFDB (.mat + .hea)"
        CSV = "csv", "CSV"
        EDF = "edf", "EDF/EDF+"

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
    fs = models.IntegerField(
        null=True,
        blank=True,
        help_text="Sampling frequency in Hz")
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
        help_text="List of Flag dicts from ecg.pipeline.rule_engine — each includes citation.", )
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


class EcgStudy(models.Model):
    """
    One trip round the medical loop. Every transition is timestamped,
    because the challenge requires showing the delay of each step.
    """

    class State(models.TextChoices):
        ACQUIRED = "acquired", "Acquis"
        ANALYSED = "analysed", "Analyse automatique faite"
        REJECTED = "rejected", "Rejete, reacquisition requise"
        TRANSMITTED = "transmitted", "Transmis au medecin"
        REVIEWING = "reviewing", "En cours de lecture"
        SIGNED = "signed", "Compte rendu signe"
        DELIVERED = "delivered", "Restitue au SIH"

    # identity, verified at acquisition
    patient_id = models.CharField(max_length=64, db_index=True)
    patient_name = models.CharField(max_length=128)
    patient_birth = models.DateField(null=True, blank=True)
    patient_sex = models.CharField(max_length=1, blank=True)
    identity_verified = models.BooleanField(default=False)
    identity_method = models.CharField(max_length=32, blank=True)  # CIN, bracelet...

    # acquisition
    file = models.FileField(upload_to="ecg_uploads/%Y/%m/")
    file_format = models.CharField(max_length=8, blank=True)  # wfdb csv edf
    paced = models.BooleanField(default=False)  # flag from the device
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ecg_acquired",
    )

    # automated analysis
    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.ACQUIRED,
        db_index=True,
    )
    analysis = models.JSONField(null=True, blank=True)  # analyze() output
    report_text = models.TextField(blank=True)
    triage_level = models.CharField(max_length=8, blank=True, db_index=True)
    triage_priority = models.IntegerField(null=True, blank=True, db_index=True)
    escalated = models.BooleanField(default=False, db_index=True)

    # physician
    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ecg_read",
    )
    physician_report = models.TextField(blank=True)
    signature = models.CharField(max_length=256, blank=True)

    # loop timestamps
    acquired_at = models.DateTimeField(auto_now_add=True)
    analysed_at = models.DateTimeField(null=True, blank=True)
    transmitted_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["triage_priority", "-acquired_at"]

    def __str__(self):
        return f"EcgStudy {self.pk} [{self.state}] — patient {self.patient_id} ({self.patient_name})"

    @property
    def turnaround_s(self):
        """Acquisition to signature. The metric the challenge is about."""
        if self.signed_at and self.acquired_at:
            return (self.signed_at - self.acquired_at).total_seconds()
        return None

    def loop_timings(self):
        """Elapsed seconds for each leg of the loop, for the audit view."""
        legs = [
            ("acquisition -> analyse", self.acquired_at, self.analysed_at),
            ("analyse -> transmission", self.analysed_at, self.transmitted_at),
            ("transmission -> ouverture", self.transmitted_at, self.opened_at),
            ("ouverture -> signature", self.opened_at, self.signed_at),
            ("signature -> SIH", self.signed_at, self.delivered_at),
        ]
        return [
            {"leg": n, "seconds": round((b - a).total_seconds(), 1)}
            for n, a, b in legs
            if a and b
        ]


class AuditEvent(models.Model):
    """Append-only trail. One row per action, never updated or deleted."""

    study = models.ForeignKey(
        EcgStudy,
        on_delete=models.CASCADE,
        related_name="events",
    )
    at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    action = models.CharField(max_length=40)
    from_state = models.CharField(max_length=16, blank=True)
    to_state = models.CharField(max_length=16, blank=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["at"]

    def __str__(self):
        return f"AuditEvent {self.action} on Study {self.study_id} at {self.at}"
