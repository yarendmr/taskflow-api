
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskDeadlineFilter,
    TaskPriority,
    TaskResponse,
    TaskSortBy,
    TaskSortOrder,
    TaskStatsResponse,
    TaskStatus,
    TaskUpdate,
)
from app.services.task_service import (
    ProjectNotFoundError,
    create_task,
    delete_project_task,
    get_project_task,
    get_project_task_stats,
    list_project_tasks,
    update_project_task,
)


router = APIRouter(
    prefix="/api/v1/projects/{project_id}/tasks",
    tags=["Tasks"],
)


# --------------------------------------------------
# 1. CREATE TASK
# --------------------------------------------------

@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_task(
    project_id: int,
    task_data: TaskCreate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    """Create a task inside an owned project."""

    try:
        return create_task(
            db=db,
            project_id=project_id,
            owner_id=current_user.id,
            task_data=task_data,
        )

    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc


# --------------------------------------------------
# 2. LIST, FILTER, SEARCH AND SORT TASKS
# --------------------------------------------------

@router.get(
    "",
    response_model=list[TaskResponse],
)
def get_my_project_tasks(
    project_id: int,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    status_filter: TaskStatus | None = Query(
        default=None,
        alias="status",
    ),
    priority_filter: TaskPriority | None = Query(
        default=None,
        alias="priority",
    ),
    search_filter: str | None = Query(
        default=None,
        alias="search",
        min_length=1,
        max_length=100,
    ),
    sort_by: TaskSortBy = Query(
        default="id",
    ),
    sort_order: TaskSortOrder = Query(
        default="asc",
    ),
    deadline_filter: TaskDeadlineFilter | None = Query(
        default=None,
        alias="deadline",
    ),
):
    """List owned project tasks with filters and sorting."""

    if search_filter is not None:
        search_filter = search_filter.strip()

        if not search_filter:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Search must not be empty.",
            )

    tasks = list_project_tasks(
        db=db,
        project_id=project_id,
        owner_id=current_user.id,
        offset=offset,
        limit=limit,
        status_filter=status_filter,
        priority_filter=priority_filter,
        search_filter=search_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        deadline_filter=deadline_filter,
    )

    if tasks is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return tasks


# --------------------------------------------------
# 3. TASK STATISTICS
# IMPORTANT: KEEP THIS BEFORE /{task_id}
# --------------------------------------------------

@router.get(
    "/stats",
    response_model=TaskStatsResponse,
)
def get_my_project_task_stats(
    project_id: int,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    """Return statistics for an owned project."""

    stats = get_project_task_stats(
        db=db,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return stats


# --------------------------------------------------
# 4. GET TASK DETAILS
# --------------------------------------------------

@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task_details(
    project_id: int,
    task_id: int,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    """Get a task from an owned project."""

    task = get_project_task(
        db=db,
        project_id=project_id,
        task_id=task_id,
        owner_id=current_user.id,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    return task


# --------------------------------------------------
# 5. UPDATE TASK
# --------------------------------------------------

@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_task(
    project_id: int,
    task_id: int,
    task_data: TaskUpdate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    """Update a task in an owned project."""

    task = update_project_task(
        db=db,
        project_id=project_id,
        task_id=task_id,
        owner_id=current_user.id,
        task_data=task_data,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    return task


# --------------------------------------------------
# 6. DELETE TASK
# --------------------------------------------------

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    project_id: int,
    task_id: int,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    """Delete a task from an owned project."""

    deleted = delete_project_task(
        db=db,
        project_id=project_id,
        task_id=task_id,
        owner_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
