
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)


def test_create_and_decode_access_token():
    token = create_access_token(user_id=1)

    assert isinstance(token, str)
    assert token.count(".") == 2

    user_id = decode_access_token(token)

    assert user_id == 1


def test_invalid_token_signature():
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "1",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        "different-signing-secret",
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_expired_access_token():
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

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(expired_token)
