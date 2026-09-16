from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "username",
        "email",
        "get_full_name",
        "role",
        "is_suspended",
        "last_login"]
    list_filter = ["role", "is_suspended", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Qalb Profile", {"fields": ("role", "is_suspended", "organization", "phone")}),
    )
