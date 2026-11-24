
from datetime import datetime
from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


TaskStatus = Literal[
    "todo",
    "in_progress",
    "done",
]

TaskPriority = Literal[
    "low",
    "medium",
    "high",
]


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    priority: TaskPriority = "medium"

    due_date: AwareDatetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized_title = value.strip()

        if not normalized_title:
            raise ValueError(
                "Task title cannot be empty."
            )

        return normalized_title


class TaskUpdate(BaseModel):
    """Schema for partially updating a task."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    status: TaskStatus | None = None

    priority: TaskPriority | None = None

    due_date: AwareDatetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(
        cls,
        value: str | None,
    ) -> str:
        if value is None:
            raise ValueError(
                "Task title cannot be null."
            )

        normalized_title = value.strip()

        if not normalized_title:
            raise ValueError(
                "Task title cannot be empty."
            )

        return normalized_title

    @field_validator("status", "priority")
    @classmethod
    def reject_null(
        cls,
        value: str | None,
    ) -> str:
        if value is None:
            raise ValueError(
                "Status and priority cannot be null."
            )

        return value


class TaskResponse(BaseModel):
    """Schema returned by task endpoints."""

    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
