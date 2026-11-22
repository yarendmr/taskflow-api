
import pytest

from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User


TEST_PASSWORD = "SecurePass123!"


def register_user(client, email):
    """Register a regular test user."""

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 201

    return response.json()


def auth_headers(user_id):
    """Create Authorization headers for a test user."""

    token = create_access_token(user_id=user_id)

    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture
def admin_auth(client, test_engine):
    """Create an admin only in the test database."""

    admin_data = register_user(
        client,
        "admin@example.com",
    )

    admin_id = admin_data["id"]

    with Session(test_engine) as db:
        admin = db.get(User, admin_id)

        assert admin is not None

        admin.role = "admin"
        db.commit()

    return {
        "admin_id": admin_id,
        "headers": auth_headers(admin_id),
    }


def test_admin_stats(client, admin_auth):
    register_user(client, "user@example.com")

    response = client.get(
        "/api/v1/admin/stats",
        headers=admin_auth["headers"],
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_users": 2,
        "active_users": 2,
    }


def test_admin_can_list_users(client, admin_auth):
    register_user(client, "user@example.com")

    response = client.get(
        "/api/v1/admin/users",
        headers=admin_auth["headers"],
    )

    assert response.status_code == 200

    users = response.json()

    assert len(users) == 2
    assert users[0]["role"] == "admin"
    assert users[1]["role"] == "user"

    for user in users:
        assert "password" not in user
        assert "hashed_password" not in user


def test_admin_user_pagination(client, admin_auth):
    register_user(client, "user1@example.com")
    register_user(client, "user2@example.com")

    response = client.get(
        "/api/v1/admin/users",
        headers=admin_auth["headers"],
        params={
            "offset": 1,
            "limit": 1,
        },
    )

    assert response.status_code == 200

    users = response.json()

    assert len(users) == 1
    assert users[0]["email"] == "user1@example.com"


def test_admin_requires_valid_token(client):
    no_token_response = client.get(
        "/api/v1/admin/users",
    )

    assert no_token_response.status_code == 401

    invalid_token_response = client.get(
        "/api/v1/admin/users",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert invalid_token_response.status_code == 401


def test_regular_user_cannot_access_admin_endpoints(client):
    user = register_user(
        client,
        "regular@example.com",
    )

    headers = auth_headers(user["id"])

    list_response = client.get(
        "/api/v1/admin/users",
        headers=headers,
    )

    assert list_response.status_code == 403

    update_response = client.patch(
        f"/api/v1/admin/users/{user['id']}/status",
        headers=headers,
        json={"is_active": False},
    )

    assert update_response.status_code == 403


def test_admin_can_deactivate_and_reactivate_user(
    client,
    admin_auth,
):
    user = register_user(
        client,
        "managed@example.com",
    )

    user_id = user["id"]

    # Token issued while the account is active
    user_headers = auth_headers(user_id)

    # Deactivate account
    deactivate_response = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin_auth["headers"],
        json={"is_active": False},
    )

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    # Existing token must no longer grant access
    profile_response = client.get(
        "/api/v1/users/me",
        headers=user_headers,
    )

    assert profile_response.status_code == 401

    # Deactivated user cannot log in
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "managed@example.com",
            "password": TEST_PASSWORD,
        },
    )

    assert login_response.status_code == 401

    # Reactivate account
    reactivate_response = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin_auth["headers"],
        json={"is_active": True},
    )

    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["is_active"] is True

    # User can log in again
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "managed@example.com",
            "password": TEST_PASSWORD,
        },
    )

    assert login_response.status_code == 200


def test_admin_cannot_modify_admin_account(
    client,
    admin_auth,
):
    admin_id = admin_auth["admin_id"]

    response = client.patch(
        f"/api/v1/admin/users/{admin_id}/status",
        headers=admin_auth["headers"],
        json={"is_active": False},
    )

    assert response.status_code == 403

    profile_response = client.get(
        "/api/v1/users/me",
        headers=admin_auth["headers"],
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["is_active"] is True


def test_admin_unknown_user_returns_404(
    client,
    admin_auth,
):
    response = client.patch(
        "/api/v1/admin/users/999999/status",
        headers=admin_auth["headers"],
        json={"is_active": False},
    )

    assert response.status_code == 404


def test_admin_rejects_invalid_status_data(
    client,
    admin_auth,
):
    user = register_user(
        client,
        "managed@example.com",
    )

    endpoint = (
        f"/api/v1/admin/users/{user['id']}/status"
    )

    # String instead of boolean
    response = client.patch(
        endpoint,
        headers=admin_auth["headers"],
        json={"is_active": "false"},
    )

    assert response.status_code == 422

    # Attempt to modify role
    response = client.patch(
        endpoint,
        headers=admin_auth["headers"],
        json={
            "is_active": False,
            "role": "admin",
        },
    )

    assert response.status_code == 422

    # Account status must remain unchanged
    users_response = client.get(
        "/api/v1/admin/users",
        headers=admin_auth["headers"],
    )

    assert users_response.status_code == 200

    managed_user = next(
        user_data
        for user_data in users_response.json()
        if user_data["id"] == user["id"]
    )

    assert managed_user["is_active"] is True
    assert managed_user["role"] == "user"
