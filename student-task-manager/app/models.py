from datetime import date
from enum import Enum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class Task(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "id": "d7b6c91e-3d3f-4a90-a8dd-9e6b3b3b7f42",
                    "title": "Submit lab report",
                    "description": "Complete the results section and references.",
                    "priority": "high",
                    "status": "pending",
                    "due_date": "2026-11-05",
                }
            ]
        },
    )

    id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def trim_and_validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank.")
        return value


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def trim_and_validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank.")
        return value


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def trim_and_validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank.")
        return value

    @model_validator(mode="after")
    def reject_null_non_nullable_fields(self) -> Self:
        for field in ("title", "priority", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class TaskResponse(Task):
    pass