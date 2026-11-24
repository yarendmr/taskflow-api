
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.project_service import get_user_project
from sqlalchemy import select

class ProjectNotFoundError(Exception):
    """Raised when a project is missing or inaccessible."""


def create_task(
    db: Session,
    project_id: int,
    owner_id: int,
    task_data: TaskCreate,
) -> Task:
    """Create a task in a project owned by the user."""

    project = get_user_project(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        raise ProjectNotFoundError(
            "Project not found."
        )

    new_task = Task(
        project_id=project.id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task


def list_project_tasks(
    db: Session,
    project_id: int,
    owner_id: int,
    offset: int = 0,
    limit: int = 20,
) -> list[Task] | None:
    """List tasks in a project owned by the user."""

    project = get_user_project(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        return None

    statement = (
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.id)
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def get_project_task(
    db: Session,
    project_id: int,
    task_id: int,
    owner_id: int,
) -> Task | None:
    """Get a task from a project owned by the user."""

    project = get_user_project(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        return None

    statement = select(Task).where(
        Task.id == task_id,
        Task.project_id == project_id,
    )

    return db.scalar(statement)


def update_project_task(
    db: Session,
    project_id: int,
    task_id: int,
    owner_id: int,
    task_data: TaskUpdate,
) -> Task | None:
    """Update a task in a project owned by the user."""

    task = get_project_task(
        db=db,
        project_id=project_id,
        task_id=task_id,
        owner_id=owner_id,
    )

    if task is None:
        return None

    update_data = task_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(task, field, value)

    if update_data:
        db.commit()
        db.refresh(task)

    return task


def delete_project_task(
    db: Session,
    project_id: int,
    task_id: int,
    owner_id: int,
) -> bool:
    """Delete a task in a project owned by the user."""

    task = get_project_task(
        db=db,
        project_id=project_id,
        task_id=task_id,
        owner_id=owner_id,
    )

    if task is None:
        return False

    db.delete(task)
    db.commit()

    return True


