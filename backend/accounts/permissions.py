"""
accounts/permissions.py
DRF permission classes based on the Qalb role system.
"""
from rest_framework.permissions import BasePermission
from .models import Role


class IsPhysician(BasePermission):
    """Only PHYSICIAN role may access this view."""
    message = "Access restricted to physicians."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and not request.user.is_suspended
            and request.user.role == Role.PHYSICIAN
        )


class IsFieldAgent(BasePermission):
    """Only FIELD_AGENT role may access this view."""
    message = "Access restricted to field agents."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and not request.user.is_suspended
            and request.user.role == Role.FIELD_AGENT
        )


class IsAdmin(BasePermission):
    """Only ADMIN role may access this view."""
    message = "Access restricted to administrators."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and not request.user.is_suspended
            and request.user.role == Role.ADMIN
        )


class IsPhysicianOrAdmin(BasePermission):
    """PHYSICIAN or ADMIN roles."""
    message = "Access restricted to physicians and administrators."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and not request.user.is_suspended
            and request.user.role in (Role.PHYSICIAN, Role.ADMIN)
        )


class IsFieldAgentOrPhysician(BasePermission):
    """FIELD_AGENT or PHYSICIAN roles."""
    message = "Access restricted to field agents and physicians."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and not request.user.is_suspended
            and request.user.role in (Role.FIELD_AGENT, Role.PHYSICIAN)
        )


class IsNotSuspended(BasePermission):
    """Blocks suspended accounts from accessing any view."""
    message = "Your account has been suspended. Contact your administrator."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and not request.user.is_suspended
        )
