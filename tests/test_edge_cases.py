
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.db.session as session_module

from app.core.config import settings
from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)
from app.schemas.user import UserCreate
from app.services.user_service import (
    UserAlreadyExistsError,
    create_user,
)


# -----------------------------------------
# JWT security tests
# -----------------------------------------

@pytest.mark.parametrize("user_id", [0, -1])
def test_create_token_rejects_invalid_user_id(user_id):
    with pytest.raises(ValueError):
        create_access_token(user_id)


@pytest.mark.parametrize(
    "subject, token_type",
    [
        ("1", "refresh"),
        ("abc", "access"),
        ("0", "access"),
        ("-1", "access"),
    ],
)
def test_decode_rejects_invalid_payload(
    subject,
    token_type,
):
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": subject,
            "type": token_type,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


# -----------------------------------------
# Database integrity tests
# -----------------------------------------

def make_failing_session(constraint_name):
    db = Mock(spec=Session)
    db.scalar.return_value = None

    original_error = Exception(
        "Simulated database integrity error."
    )

    original_error.diag = SimpleNamespace(
        constraint_name=constraint_name,
    )

    db.commit.side_effect = IntegrityError(
        "INSERT INTO users",
        {},
        original_error,
    )

    return db


def test_registration_handles_duplicate_integrity_error():
    db = make_failing_session("ix_users_email")

    user_data = UserCreate(
        email="duplicate@example.com",
        password="SecurePass123!",
    )

    with pytest.raises(
        UserAlreadyExistsError,
        match="Email address is already registered",
    ):
        create_user(db, user_data)

    db.add.assert_called_once()
    db.rollback.assert_called_once()
    db.refresh.assert_not_called()


def test_registration_reraises_other_integrity_errors():
    db = make_failing_session("other_constraint")

    user_data = UserCreate(
        email="other@example.com",
        password="SecurePass123!",
    )

    with pytest.raises(IntegrityError):
        create_user(db, user_data)

    db.rollback.assert_called_once()
    db.refresh.assert_not_called()


# -----------------------------------------
# Database session lifecycle tests
# -----------------------------------------

def test_get_db_closes_session_normally(monkeypatch):
    fake_db = Mock()

    monkeypatch.setattr(
        session_module,
        "SessionLocal",
        lambda: fake_db,
    )

    generator = session_module.get_db()

    assert next(generator) is fake_db

    with pytest.raises(StopIteration):
        next(generator)

    fake_db.close.assert_called_once()


def test_get_db_closes_session_on_error(monkeypatch):
    fake_db = Mock()

    monkeypatch.setattr(
        session_module,
        "SessionLocal",
        lambda: fake_db,
    )

    generator = session_module.get_db()

    assert next(generator) is fake_db

    with pytest.raises(
        RuntimeError,
        match="Simulated request failure",
    ):
        generator.throw(
            RuntimeError("Simulated request failure")
        )

    fake_db.close.assert_called_once()
