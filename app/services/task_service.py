from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import (
    TaskCreate,
    TaskDeadlineFilter,
    TaskPriority,
    TaskSortBy,
    TaskSortOrder,
    TaskStatsResponse,
    TaskStatus,
    TaskUpdate,
)
from app.services.project_service import get_user_project
from sqlalchemy import case, func, select

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
    status_filter: TaskStatus | None = None,
    priority_filter: TaskPriority | None = None,
    search_filter: str | None = None,
    sort_by: TaskSortBy = "id",
    sort_order: TaskSortOrder = "asc",
    deadline_filter: TaskDeadlineFilter | None = None,
) -> list[Task] | None:
    """List owned project tasks with filtering, search, and sorting."""

    # Verify project ownership.
    project = get_user_project(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        return None

    # Only fetch tasks belonging to this project.
    statement = select(Task).where(
        Task.project_id == project_id
    )

    # Filter by task status.
    if status_filter is not None:
        statement = statement.where(
            Task.status == status_filter
        )

    # Filter by task priority.
    if priority_filter is not None:
        statement = statement.where(
            Task.priority == priority_filter
        )

    # Case-insensitive title search.
    if search_filter is not None:
        statement = statement.where(
            Task.title.icontains(
                search_filter,
                autoescape=True,
            )
        )

    # Filter tasks by deadline.
    if deadline_filter is not None:
        now = datetime.now(timezone.utc)

        if deadline_filter == "overdue":
            statement = statement.where(
                Task.due_date < now,
                Task.status != "done",
            )

        elif deadline_filter == "due_soon":
            deadline_limit = now + timedelta(days=7)

            statement = statement.where(
                Task.due_date >= now,
                Task.due_date <= deadline_limit,
                Task.status != "done",
            )

        elif deadline_filter == "no_due_date":
            statement = statement.where(
                Task.due_date.is_(None)
            )

    # Logical priority ordering.
    priority_rank = case(
        (Task.priority == "low", 1),
        (Task.priority == "medium", 2),
        (Task.priority == "high", 3),
        else_=4,
    )

    sort_columns = {
        "id": Task.id,
        "created_at": Task.created_at,
        "title": func.lower(Task.title),
        "priority": priority_rank,
        "due_date": Task.due_date,
    }

    sort_column = sort_columns[sort_by]

    if sort_order == "desc":
        primary_sort = sort_column.desc()
    else:
        primary_sort = sort_column.asc()

    # Keep tasks without due dates at the end,
    # regardless of the sorting direction.
    if sort_by == "due_date":
        primary_sort = primary_sort.nulls_last()

    # Stable sorting before pagination.
    statement = (
        statement
        .order_by(primary_sort, Task.id.asc())
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


def get_project_task_stats(
    db: Session,
    project_id: int,
    owner_id: int,
) -> TaskStatsResponse | None:
    """Calculate statistics for tasks in an owned project."""

    # Verify project ownership.
    project = get_user_project(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        return None

    # Aggregate all task statistics in one SQL query.
    statement = select(
        func.count(Task.id).label("total_tasks"),
        func.count(Task.id)
        .filter(Task.status == "todo")
        .label("todo_tasks"),
        func.count(Task.id)
        .filter(Task.status == "in_progress")
        .label("in_progress_tasks"),
        func.count(Task.id)
        .filter(Task.status == "done")
        .label("done_tasks"),
        func.count(Task.id)
        .filter(Task.priority == "low")
        .label("low_priority_tasks"),
        func.count(Task.id)
        .filter(Task.priority == "medium")
        .label("medium_priority_tasks"),
        func.count(Task.id)
        .filter(Task.priority == "high")
        .label("high_priority_tasks"),
    ).where(
        Task.project_id == project_id
    )

    result = db.execute(statement).one()

    total_tasks = result.total_tasks
    done_tasks = result.done_tasks

    # Avoid division by zero for empty projects.
    completion_rate = (
        round((done_tasks / total_tasks) * 100, 2)
        if total_tasks > 0
        else 0.0
    )

    return TaskStatsResponse(
        project_id=project_id,
        total_tasks=total_tasks,
        todo_tasks=result.todo_tasks,
        in_progress_tasks=result.in_progress_tasks,
        done_tasks=done_tasks,
        low_priority_tasks=result.low_priority_tasks,
        medium_priority_tasks=result.medium_priority_tasks,
        high_priority_tasks=result.high_priority_tasks,
        completion_rate=completion_rate,
    )