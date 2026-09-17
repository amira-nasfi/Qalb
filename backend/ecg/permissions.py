from rest_framework.permissions import BasePermission
from accounts.models import Role


class CanAccessEcgStudy(BasePermission):
    """
    Object-level permission scoping for EcgStudy:
    1. Admin / superuser: full access.
    2. Field agent: access only if study.operator == user (or unassigned).
    3. Physician:
       - Read access if study state in [TRANSMITTED, REVIEWING, SIGNED, DELIVERED].
       - Write / sign access if study.reader is user (or unassigned for opening).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "role", None) == Role.ADMIN or user.is_staff or user.is_superuser:
            return True

        if getattr(user, "role", None) == Role.FIELD_AGENT:
            # Field agent has full read access to worklist, trace waveforms and generated results
            if request.method in ("GET", "HEAD", "OPTIONS"):
                return True
            # Write/edit operations restricted to own studies
            return obj.operator is None or obj.operator_id == user.id

        if getattr(user, "role", None) == Role.PHYSICIAN:
            from ecg.models import EcgStudy
            allowed_states = [
                EcgStudy.State.TRANSMITTED,
                EcgStudy.State.REVIEWING,
                EcgStudy.State.SIGNED,
                EcgStudy.State.DELIVERED,
            ]
            if obj.state in allowed_states:
                if request.method not in ("GET", "HEAD", "OPTIONS"):
                    return obj.reader is None or obj.reader_id == user.id
                return True
            return False

        return False
