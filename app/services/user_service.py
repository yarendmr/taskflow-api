
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserProfileUpdate


class UserAlreadyExistsError(Exception):
    """Raised when an email address is already registered."""
    pass


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user in the database."""

    # Normalize the email address
    email = str(user_data.email).lower()

    # Check whether the email is already registered
    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user is not None:
        raise UserAlreadyExistsError(
            "Email address is already registered."
        )

    # Hash the user's password
    hashed_password = hash_password(user_data.password)

    # Create the SQLAlchemy user object
    new_user = User(
        email=email,
        hashed_password=hashed_password,
    )

    # Save the user to PostgreSQL
    db.add(new_user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        constraint = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint == "ix_users_email":
            raise UserAlreadyExistsError(
                "Email address is already registered."
            ) from exc

        raise

    # Reload database-generated fields
    db.refresh(new_user)

    return new_user


def update_user_profile(
    db: Session,
    user: User,
    profile_data: UserProfileUpdate,
) -> User:
    """Update the authenticated user's profile."""

    # Update only explicitly provided fields
    if "full_name" in profile_data.model_fields_set:
        user.full_name = profile_data.full_name

        db.commit()
        db.refresh(user)

    return user
