"""
accounts/serializers.py
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User, Role


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")
        request = self.context.get("request")

        user = authenticate(request=request, username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials.", code="authorization")
        if user.is_suspended:
            raise serializers.ValidationError(
                "Your account has been suspended. Contact your administrator.", code="suspended"
            )
        data["user"] = user
        return data


class UserMeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "full_name", "role", "organization", "phone",
            "is_suspended", "last_login", "date_joined",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "full_name", "first_name", "last_name",
            "role", "organization", "is_suspended", "last_login", "date_joined",
        ]
        read_only_fields = ["last_login", "date_joined"]

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserInviteSerializer(serializers.ModelSerializer):
    """ADMIN creates a new inactive account. A temporary password must be set."""
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "username", "email", "first_name", "last_name",
            "role", "organization", "phone", "password",
        ]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_role(self, value):
        if value not in [Role.FIELD_AGENT, Role.PHYSICIAN, Role.ADMIN]:
            raise serializers.ValidationError("Invalid role.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True  # Activated immediately; email flow is optional
        user.save()
        return user


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
            raise serializers.ValidationError({"old_password": "Incorrect password."})
        return data
