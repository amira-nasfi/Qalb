"""
accounts/serializers.py
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User, Role


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={
            "input_type": "password"})

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")
        request = self.context.get("request")

        user = authenticate(
            request=request,
            username=username,
            password=password)
        if not user:
            raise serializers.ValidationError(
                "Invalid credentials.", code="authorization")
        if user.is_suspended:
            raise serializers.ValidationError(
                "Your account has been suspended. Contact your administrator.",
                code="suspended")
        data["user"] = user
        return data


class UserMeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "full_name", "role", "organization", "phone", "date_of_birth",
            "is_suspended", "last_login", "date_joined", "force_password_change",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "first_name",
            "last_name",
            "role",
            "organization",
            "date_of_birth",
            "is_suspended",
            "last_login",
            "date_joined",
        ]
        read_only_fields = ["last_login", "date_joined"]

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserInviteSerializer(serializers.Serializer):
    """Admin creates a new user account: Practitioner (auto 8-digit ID) or Physician (manual medical license)."""
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    date_of_birth = serializers.DateField(required=True)
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(
        choices=[Role.FIELD_AGENT, Role.PHYSICIAN],
        default=Role.FIELD_AGENT,
    )
    license_number = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data):
        role = data.get("role", Role.FIELD_AGENT)
        license_num = data.get("license_number", "").strip()
        if role == Role.PHYSICIAN:
            if not license_num:
                raise serializers.ValidationError({
                    "license_number": "Le numéro de licence médicale (RPPS) est obligatoire pour un compte Médecin."
                })
            if User.objects.filter(username=license_num).exists():
                raise serializers.ValidationError({
                    "license_number": "Un médecin avec ce numéro de licence existe déjà."
                })
        return data


class UserRoleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role"]

    def validate_role(self, value):
        if value not in [Role.FIELD_AGENT, Role.PHYSICIAN, Role.ADMIN]:
            raise serializers.ValidationError("Invalid role.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        user = self.context["request"].user
        if not user.check_password(data["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "Incorrect password."})
        return data
