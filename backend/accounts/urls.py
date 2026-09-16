from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = "accounts"

urlpatterns = [
    # ── Auth ────────────────────────────────────────────────────────────────
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    path(
        "auth/change-password/",
        views.ChangePasswordView.as_view(),
        name="change_password"),

    # ── Admin: User Management ──────────────────────────────────────────────
    path("admin/users/", views.UserListView.as_view(), name="user_list"),
    path(
        "admin/users/invite/",
        views.UserInviteView.as_view(),
        name="user_invite"),
    path(
        "admin/users/<int:pk>/suspend/",
        views.UserSuspendView.as_view(),
        name="user_suspend"),
    path(
        "admin/users/<int:pk>/role/",
        views.UserRoleUpdateView.as_view(),
        name="user_role"),
]
