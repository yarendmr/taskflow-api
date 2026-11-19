
from app.core.security import hash_password, verify_password


def test_password_hashing():
    password = "SecurePass123!"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True


def test_wrong_password():
    password = "SecurePass123!"

    hashed = hash_password(password)

    assert verify_password("WrongPass123!", hashed) is False
