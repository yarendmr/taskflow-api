
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    UserProfileUpdate,
    UserResponse,
)
from app.services.user_service import update_user_profile


router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
)
def read_current_user(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
):
    """Return the authenticated user's information."""

    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
)
def update_current_user(
    profile_data: UserProfileUpdate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    """Update the authenticated user's profile."""

    return update_user_profile(
        db=db,
        user=current_user,
        profile_data=profile_data,
    )
