
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


ProjectStatus = Literal[
    "active",
    "completed",
    "archived",
]


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized_name = value.strip()

        if not normalized_name:
            raise ValueError(
                "Project name cannot be empty."
            )

        return normalized_name


class ProjectUpdate(BaseModel):
    """Schema for partially updating a project."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    status: ProjectStatus | None = None

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str | None,
    ) -> str:
        if value is None:
            raise ValueError(
                "Project name cannot be null."
            )

        normalized_name = value.strip()

        if not normalized_name:
            raise ValueError(
                "Project name cannot be empty."
            )

        return normalized_name

    @field_validator("status")
    @classmethod
    def validate_status(
        cls,
        value: ProjectStatus | None,
    ) -> ProjectStatus:
        if value is None:
            raise ValueError(
                "Project status cannot be null."
            )

        return value


class ProjectResponse(BaseModel):
    """Schema returned by project endpoints."""

    id: int
    name: str
    description: str | None
    status: ProjectStatus
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
