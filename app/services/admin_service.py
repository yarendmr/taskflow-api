
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class ManagedUserNotFoundError(Exception):
    """Raised when a managed user does not exist."""


class ProtectedAdminAccountError(Exception):
    """Raised when attempting to modify an admin account."""


def list_users(
    db: Session,
    offset: int = 0,
    limit: int = 20,
) -> list[User]:
    """Return users with pagination."""

    statement = (
        select(User)
        .order_by(User.id)
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def set_user_active_status(
    db: Session,
    user_id: int,
    is_active: bool,
) -> User:
    """Activate or deactivate a non-admin user."""

    user = db.get(User, user_id)

    if user is None:
        raise ManagedUserNotFoundError(
            "User not found."
        )

    if user.role == "admin":
        raise ProtectedAdminAccountError(
            "Admin accounts cannot be modified."
        )

    user.is_active = is_active

    db.commit()
    db.refresh(user)

    return user
