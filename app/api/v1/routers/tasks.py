
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
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services.task_service import (
    ProjectNotFoundError,
    create_task,
    delete_project_task,
    get_project_task,
    list_project_tasks,
    update_project_task,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/tasks",
    tags=["Tasks"],
)


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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List tasks in an owned project."""

    tasks = list_project_tasks(
        db=db,
        project_id=project_id,
        owner_id=current_user.id,
        offset=offset,
        limit=limit,
    )

    if tasks is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return tasks


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
    """Get a task belonging to an owned project."""

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
    """Update a task belonging to an owned project."""

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
    """Delete a task belonging to an owned project."""

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
