"""
accounts/models.py
Custom User model for Qalb قلب — extends AbstractUser with:
  - role: FIELD_AGENT | PHYSICIAN | ADMIN
  - is_suspended: soft-disable without deleting account
  - organization, phone: operational context
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    FIELD_AGENT = "FIELD_AGENT", "Field Agent"
    PHYSICIAN   = "PHYSICIAN",   "Physician"
    ADMIN       = "ADMIN",       "Administrator"


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FIELD_AGENT,
        db_index=True,
    )
    is_suspended = models.BooleanField(
        default=False,
        help_text="Soft-disable: user cannot log in but record is preserved for audit.",
    )
    organization = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    # last_login is already on AbstractUser

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    # ── Role helpers ───────────────────────────────────────────────────────────
    @property
    def is_physician(self):
        return self.role == Role.PHYSICIAN

    @property
    def is_field_agent(self):
        return self.role == Role.FIELD_AGENT

    @property
    def is_admin_user(self):
        return self.role == Role.ADMIN
