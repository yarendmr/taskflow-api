
import pytest

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def test_register_success(client, test_engine):
    password = "SecurePass123!"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": password,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "test@example.com"
    assert data["is_active"] is True
    assert isinstance(data["id"], int)
    assert data["created_at"] is not None

    assert "password" not in data
    assert "hashed_password" not in data

    with Session(test_engine) as db:
        saved_user = db.scalar(
            select(User).where(
                User.email == "test@example.com"
            )
        )

        assert saved_user is not None
        assert saved_user.hashed_password != password
        assert verify_password(
            password,
            saved_user.hashed_password,
        )


def test_register_duplicate_email(client):
    user_data = {
        "email": "test@example.com",
        "password": "SecurePass123!",
    }

    first_response = client.post(
        "/api/v1/auth/register",
        json=user_data,
    )

    second_response = client.post(
        "/api/v1/auth/register",
        json=user_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Email address is already registered."
    )


@pytest.mark.parametrize(
    "user_data",
    [
        {
            "email": "invalid-email",
            "password": "SecurePass123!",
        },
        {
            "email": "test@example.com",
            "password": "123",
        },
    ],
)
def test_register_invalid_data(client, user_data):
    response = client.post(
        "/api/v1/auth/register",
        json=user_data,
    )

    assert response.status_code == 422
