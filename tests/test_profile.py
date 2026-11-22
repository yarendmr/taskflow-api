
import pytest


TEST_EMAIL = "profile@example.com"
TEST_PASSWORD = "SecurePass123!"


@pytest.fixture
def user_auth(client):
    """Register and authenticate a test user."""

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "user_id": register_response.json()["id"],
        "headers": {
            "Authorization": f"Bearer {token}",
        },
    }


def test_update_full_name(client, user_auth):
    response = client.patch(
        "/api/v1/users/me",
        headers=user_auth["headers"],
        json={
            "full_name": "  Deniz Yılmaz  ",
        },
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Deniz Yılmaz"

    profile_response = client.get(
        "/api/v1/users/me",
        headers=user_auth["headers"],
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["full_name"] == "Deniz Yılmaz"


def test_clear_full_name(client, user_auth):
    response = client.patch(
        "/api/v1/users/me",
        headers=user_auth["headers"],
        json={"full_name": None},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] is None


def test_empty_update_preserves_profile(client, user_auth):
    client.patch(
        "/api/v1/users/me",
        headers=user_auth["headers"],
        json={"full_name": "Deniz Yılmaz"},
    )

    response = client.patch(
        "/api/v1/users/me",
        headers=user_auth["headers"],
        json={},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Deniz Yılmaz"


def test_update_profile_without_token(client):
    response = client.patch(
        "/api/v1/users/me",
        json={"full_name": "Deniz Yılmaz"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"role": "admin"},
        {"is_active": False},
    ],
)
def test_profile_rejects_restricted_fields(
    client,
    user_auth,
    payload,
):
    response = client.patch(
        "/api/v1/users/me",
        headers=user_auth["headers"],
        json=payload,
    )

    assert response.status_code == 422

    profile_response = client.get(
        "/api/v1/users/me",
        headers=user_auth["headers"],
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["role"] == "user"
    assert profile_response.json()["is_active"] is True


def test_profile_rejects_blank_name(client, user_auth):
    response = client.patch(
        "/api/v1/users/me",
        headers=user_auth["headers"],
        json={"full_name": "   "},
    )

    assert response.status_code == 422


def test_profile_rejects_too_long_name(client, user_auth):
    response = client.patch(
        "/api/v1/users/me",
        headers=user_auth["headers"],
        json={"full_name": "A" * 121},
    )

    assert response.status_code == 422
