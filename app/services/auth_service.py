
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user using email and password."""

    # Normalize the email address
    normalized_email = email.strip().lower()

    # Find the user in the database
    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    # Reject unknown users
    if user is None:
        return None

    # Verify the password
    if not verify_password(
        password,
        user.hashed_password,
    ):
        return None

    # Reject inactive accounts
    if not user.is_active:
        return None

    # Authentication successful
    return user
