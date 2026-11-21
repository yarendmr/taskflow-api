
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


# Password hashing configuration
password_hasher = PasswordHash.recommended()

# JWT configuration
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password against its stored hash."""
    return password_hasher.verify(
        plain_password,
        hashed_password,
    )


class InvalidAccessTokenError(Exception):
    """Raised when an access token is invalid or expired."""
    pass


def create_access_token(user_id: int) -> str:
    """Generate a signed JWT access token."""

    if user_id <= 0:
        raise ValueError("User ID must be positive.")

    now = datetime.now(timezone.utc)

    expire = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int:
    """Validate an access token and return its user ID."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
    except InvalidTokenError as exc:
        raise InvalidAccessTokenError(
            "Invalid or expired access token."
        ) from exc

    subject = payload.get("sub")

    if (
        payload.get("type") != "access"
        or not isinstance(subject, str)
        or not subject.isdecimal()
        or int(subject) <= 0
    ):
        raise InvalidAccessTokenError(
            "Invalid access token payload."
        )

    return int(subject)
