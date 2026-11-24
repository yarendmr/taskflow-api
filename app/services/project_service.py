
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

from sqlalchemy import select


def create_project(
    db: Session,
    project_data: ProjectCreate,
    owner_id: int,
) -> Project:
    """Create a project for the authenticated user."""

    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=owner_id,
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project


def list_user_projects(
    db: Session,
    owner_id: int,
    offset: int = 0,
    limit: int = 20,
) -> list[Project]:
    """List projects belonging to a user."""

    statement = (
        select(Project)
        .where(Project.owner_id == owner_id)
        .order_by(Project.id)
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def get_user_project(
    db: Session,
    project_id: int,
    owner_id: int,
) -> Project | None:
    """Get a project only if it belongs to the user."""

    statement = select(Project).where(
        Project.id == project_id,
        Project.owner_id == owner_id,
    )

    return db.scalar(statement)


def update_user_project(
    db: Session,
    project_id: int,
    owner_id: int,
    project_data: ProjectUpdate,
) -> Project | None:
    """Update a project belonging to the authenticated user."""

    project = get_user_project(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        return None

    # Update only fields included in the request
    update_data = project_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(project, field, value)

    if update_data:
        db.commit()
        db.refresh(project)

    return project


def delete_user_project(
    db: Session,
    project_id: int,
    owner_id: int,
) -> bool:
    """Delete a project belonging to the authenticated user."""

    project = get_user_project(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        return False

    db.delete(project)
    db.commit()

    return True


