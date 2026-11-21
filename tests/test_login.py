
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
)
from app.models.user import User


TEST_EMAIL = "registered@example.com"
TEST_PASSWORD = "SecurePass123!"


@pytest.fixture
def registered_user(client):
    """Register a user in the isolated test database."""

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 201

    return response.json()


def test_login_success(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": TEST_EMAIL.upper(),
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)

    user_id = decode_access_token(
        data["access_token"]
    )

    assert user_id == registered_user["id"]


def test_login_wrong_password(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": TEST_EMAIL,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Incorrect email or password."
    )


def test_login_unknown_user(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "unknown@example.com",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 401


def test_login_inactive_user(
    client,
    test_engine,
    registered_user,
):
    with Session(test_engine) as db:
        user = db.get(User, registered_user["id"])

        assert user is not None

        user.is_active = False
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 401


def test_users_me_without_token(client):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_users_me_valid_token(client, registered_user):
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == registered_user["id"]
    assert data["email"] == TEST_EMAIL
    assert data["is_active"] is True

    assert "password" not in data
    assert "hashed_password" not in data


def test_users_me_invalid_token(client):
    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401


def test_users_me_expired_token(client):
    now = datetime.now(timezone.utc)

    expired_token = jwt.encode(
        {
            "sub": "1",
            "type": "access",
            "iat": now - timedelta(hours=1),
            "exp": now - timedelta(minutes=1),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )

    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {expired_token}"
        },
    )

    assert response.status_code == 401


def test_users_me_inactive_user(
    client,
    test_engine,
    registered_user,
):
    token = create_access_token(
        registered_user["id"]
    )

    with Session(test_engine) as db:
        user = db.get(User, registered_user["id"])

        assert user is not None

        user.is_active = False
        db.commit()

    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 401


def test_users_me_nonexistent_user(client):
    token = create_access_token(user_id=999999)

    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 401
