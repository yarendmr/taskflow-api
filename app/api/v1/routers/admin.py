
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import UserStatusUpdate
from app.schemas.user import UserResponse
from app.services.admin_service import (
    ManagedUserNotFoundError,
    ProtectedAdminAccountError,
    list_users,
    set_user_active_status,
)


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administration"],
)


@router.get("/stats")
def get_admin_stats(
    current_user: Annotated[
        User,
        Depends(require_admin),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    """Return user statistics for administrators."""

    total_users = db.scalar(
        select(func.count(User.id))
    )

    active_users = db.scalar(
        select(func.count(User.id)).where(
            User.is_active.is_(True)
        )
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
    }


@router.get(
    "/users",
    response_model=list[UserResponse],
)
def get_admin_users(
    current_user: Annotated[
        User,
        Depends(require_admin),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List users for administrators."""

    return list_users(
        db=db,
        offset=offset,
        limit=limit,
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
)
def update_admin_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    current_user: Annotated[
        User,
        Depends(require_admin),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    """Activate or deactivate a non-admin user."""

    try:
        return set_user_active_status(
            db=db,
            user_id=user_id,
            is_active=status_data.is_active,
        )

    except ManagedUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from exc

    except ProtectedAdminAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Admin accounts cannot be modified "
                "through this endpoint."
            ),
        ) from exc
