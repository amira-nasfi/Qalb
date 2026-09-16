"""
accounts/views.py
All authentication and user management endpoints for Qalb قلب.
"""
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from ratelimit.decorators import ratelimit
from ratelimit.utils import is_ratelimited

from audit.models import AuditLog, AuditAction
from .models import User
from .permissions import IsAdmin
from .serializers import (
    LoginSerializer,
    UserMeSerializer,
    UserListSerializer,
    UserInviteSerializer,
    UserRoleUpdateSerializer,
    ChangePasswordSerializer,
)


class LoginView(APIView):
    """
    POST /api/auth/login/
    Returns JWT access + refresh tokens on valid credentials.
    Rate-limited: 5 attempts / 10 min per IP.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # ── Rate-limit check ───────────────────────────────────────────────────
        limited = is_ratelimited(
            request,
            group="login",
            key="ip",
            rate="5/10m",
            method="POST",
            increment=True,
        )
        if limited:
            return Response(
                {"error": "Too many login attempts. Please wait 10 minutes."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            # Log failed attempt
            AuditLog.log(
                action=AuditAction.LOGIN_FAILED,
                target_type="User",
                target_id=request.data.get("username", "unknown"),
                actor=None,
                request=request,
                extra={"reason": "invalid_credentials"},
            )
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        AuditLog.log(
            action=AuditAction.LOGIN,
            target_type="User",
            target_id=user.pk,
            actor=user,
            request=request,
            extra={"role": user.role},
        )

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserMeSerializer(user).data,
        })


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklists the refresh token, effectively logging out.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except (TokenError, InvalidToken):
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            action=AuditAction.LOGOUT,
            target_type="User",
            target_id=request.user.pk,
            actor=request.user,
            request=request,
        )

        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)


class MeView(generics.RetrieveAPIView):
    """
    GET /api/auth/me/
    Returns the current user's profile and role.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserMeSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    User changes their own password. Requires old password verification.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        update_session_auth_hash(request, user)  # Keeps session valid after password change

        AuditLog.log(
            action=AuditAction.PASSWORD_CHANGED,
            target_type="User",
            target_id=user.pk,
            actor=user,
            request=request,
        )

        return Response({"detail": "Password changed successfully."})


# ── Admin: User Management ─────────────────────────────────────────────────────

class UserListView(generics.ListAPIView):
    """
    GET /api/admin/users/
    ADMIN-only. Returns all users with role and status.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserListSerializer
    queryset = User.objects.all().order_by("last_name", "first_name")


class UserInviteView(generics.CreateAPIView):
    """
    POST /api/admin/users/invite/
    ADMIN-only. Creates a new user account with a specified role.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserInviteSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        AuditLog.log(
            action=AuditAction.INVITE,
            target_type="User",
            target_id=user.pk,
            actor=self.request.user,
            request=self.request,
            extra={"role": user.role, "username": user.username},
        )


class UserSuspendView(APIView):
    """
    POST /api/admin/users/{id}/suspend/
    ADMIN-only. Toggles the is_suspended flag.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            return Response({"error": "You cannot suspend yourself."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_suspended = not user.is_suspended
        user.save(update_fields=["is_suspended"])

        action = AuditAction.SUSPEND if user.is_suspended else AuditAction.REINSTATE
        AuditLog.log(
            action=action,
            target_type="User",
            target_id=user.pk,
            actor=request.user,
            request=request,
            extra={"is_suspended": user.is_suspended},
        )

        return Response({
            "id": user.pk,
            "is_suspended": user.is_suspended,
            "detail": f"User {'suspended' if user.is_suspended else 'reinstated'} successfully.",
        })


class UserRoleUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/admin/users/{id}/role/
    ADMIN-only. Changes a user's role.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserRoleUpdateSerializer
    queryset = User.objects.all()

    def perform_update(self, serializer):
        old_role = self.get_object().role
        instance = serializer.save()
        AuditLog.log(
            action=AuditAction.ROLE_CHANGED,
            target_type="User",
            target_id=instance.pk,
            actor=self.request.user,
            request=self.request,
            extra={"old_role": old_role, "new_role": instance.role},
        )
