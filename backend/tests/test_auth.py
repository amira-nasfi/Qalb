import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import User, Role


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user(db):
    def make_user(
            username,
            password,
            role=Role.FIELD_AGENT,
            is_suspended=False):
        user = User.objects.create(
            username=username,
            email=f"{username}@example.com",
            role=role,
            is_suspended=is_suspended
        )
        user.set_password(password)
        user.save()
        return user
    return make_user


@pytest.mark.django_db
def test_login_success(api_client, create_user):
    create_user("field1", "securepassword123", Role.FIELD_AGENT)

    url = reverse("accounts:login")
    response = api_client.post(
        url, {"username": "field1", "password": "securepassword123"})

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data
    assert response.data["user"]["role"] == Role.FIELD_AGENT


@pytest.mark.django_db
def test_login_invalid_credentials(api_client, create_user):
    create_user("field1", "securepassword123", Role.FIELD_AGENT)

    url = reverse("accounts:login")
    response = api_client.post(
        url, {"username": "field1", "password": "wrongpassword"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_login_suspended_user(api_client, create_user):
    create_user(
        "field1",
        "securepassword123",
        Role.FIELD_AGENT,
        is_suspended=True)

    url = reverse("accounts:login")
    response = api_client.post(
        url, {"username": "field1", "password": "securepassword123"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "suspended" in str(response.data)


@pytest.mark.django_db
def test_role_based_access(api_client, create_user):
    physician = create_user("doc", "pass12345678", Role.PHYSICIAN)
    field_agent = create_user("agent", "pass12345678", Role.FIELD_AGENT)
    admin_user = create_user("admin", "pass12345678", Role.ADMIN)

    # Physician shouldn't access admin user list
    api_client.force_authenticate(user=physician)
    url = reverse("accounts:user_list")
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    # Admin should access admin user list
    api_client.force_authenticate(user=admin_user)
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK

    # Field agent shouldn't access fhir export (physician/admin only)
    api_client.force_authenticate(user=field_agent)
    url = reverse("fhir_export:report_export", kwargs={"report_id": 1})
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
