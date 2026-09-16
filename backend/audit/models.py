"""
Audit log model — full traceability of every action in Qalb قلب.

Design principles:
  - Append-only: no UPDATE or DELETE is permitted via the API.
  - Every state change to Patient, ECGRecord, ProcessingResult, or Report
    is recorded with before/after JSON snapshots.
  - System-generated events (pipeline runs) use actor="SYSTEM".
  - IP addresses are stored as SHA-256 hashes (not plaintext) for privacy.
"""

import hashlib
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Record created"
    UPDATE = "UPDATE", "Record updated"
    SIGN = "SIGN", "Report signed by physician"
    PROCESS_START = "PROCESS_START", "ECG processing started"
    PROCESS_DONE = "PROCESS_DONE", "ECG processing completed"
    PROCESS_ERROR = "PROCESS_ERROR", "ECG processing failed"
    EXPORT_FHIR = "EXPORT_FHIR", "FHIR bundle exported"
    # ── Auth & Account ──────────────────────────────────────────────────────
    LOGIN = "LOGIN", "User logged in"
    LOGIN_FAILED = "LOGIN_FAILED", "Login attempt failed"
    LOGOUT = "LOGOUT", "User logged out"
    PASSWORD_CHANGED = "PASSWORD_CHANGED", "Password changed"
    INVITE = "INVITE", "User account invited/created"
    SUSPEND = "SUSPEND", "User account suspended"
    REINSTATE = "REINSTATE", "User account reinstated"
    ROLE_CHANGED = "ROLE_CHANGED", "User role changed"
    # ── Access control ──────────────────────────────────────────────────────
    PERMISSION_DENY = "PERMISSION_DENY", "Access denied (403)"
    VIEW = "VIEW", "Record viewed"


class AuditLog(models.Model):
    """
    Immutable audit record. One row per auditable event.

    Every clinical action (upload, process, review, sign, export) produces
    at least one AuditLog entry. The combination of (timestamp, actor, action,
    target_type, target_id) provides a full reconstruction of the clinical
    decision timeline.
    """

    # When
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Who (nullable for SYSTEM events)
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        help_text="User who performed the action; null means SYSTEM (pipeline).",
    )
    actor_label = models.CharField(
        max_length=150,
        default="SYSTEM",
        help_text="Snapshot of username at event time (preserved even if user is deleted).",
    )

    # What
    action = models.CharField(
        max_length=30,
        choices=AuditAction.choices,
        db_index=True,
    )

    # On what
    target_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Django model name, e.g. 'ECGRecord', 'Report'.",
    )
    target_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="PK or UUID of the affected record.",
    )

    # Before / after snapshots
    old_value = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON snapshot of the record state before the action.",
    )
    new_value = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON snapshot of the record state after the action.",
    )

    # Request context
    ip_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 of the request IP address (not stored in plaintext).",
    )
    user_agent = models.TextField(blank=True)

    # Free-form extra context
    extra = models.JSONField(
        null=True,
        blank=True,
        help_text="Arbitrary context, e.g. {flag_codes: ['QTC_CRITICAL'], severity: 'CRITICAL'}.",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log"
        # Prevent accidental bulk-delete
        default_permissions = ("add", "view")  # no 'change', no 'delete'

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.actor_label} · {self.action} · {self.target_type}:{self.target_id}"

    @staticmethod
    def hash_ip(ip: str) -> str:
        """Return SHA-256 hex digest of an IP address string."""
        return hashlib.sha256(ip.encode()).hexdigest()

    @classmethod
    def log(
        cls,
        action: str,
        target_type: str,
        target_id,
        actor=None,
        old_value=None,
        new_value=None,
        request=None,
        extra=None,
    ) -> "AuditLog":
        """
        Convenience factory method for creating audit log entries.

        Usage:
            AuditLog.log(
                action=AuditAction.SIGN,
                target_type="Report",
                target_id=report.pk,
                actor=request.user,
                new_value={"status": "SIGNED", "signed_by": username},
                request=request,
                extra={"report_severity": "CRITICAL"},
            )
        """
        ip_hash = ""
        user_agent = ""
        if request:
            raw_ip = request.META.get("REMOTE_ADDR", "")
            if raw_ip:
                ip_hash = cls.hash_ip(raw_ip)
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]

        actor_label = "SYSTEM"
        if actor and hasattr(actor, "username"):
            actor_label = actor.username

        return cls.objects.create(
            actor=actor if (actor and actor.is_authenticated) else None,
            actor_label=actor_label,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            old_value=old_value,
            new_value=new_value,
            ip_hash=ip_hash,
            user_agent=user_agent,
            extra=extra,
        )
