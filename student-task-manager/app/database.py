from datetime import date
from enum import Enum
from typing import Any, Literal
from uuid import uuid4


tasks_db: dict[str, dict[str, Any]] = {}


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    return value


def add_task(data: dict[str, Any]) -> dict[str, Any]:
    task = {
        "id": str(uuid4()),
        "title": data["title"],
        "description": data.get("description"),
        "priority": _serialize_value(data.get("priority", "medium")),
        "status": _serialize_value(data.get("status", "pending")),
        "due_date": _serialize_value(data.get("due_date")),
    }
    tasks_db[task["id"]] = task
    return task.copy()


def create_task(data: dict[str, Any]) -> dict[str, Any]:
    return add_task(data)


def get_task(task_id: str) -> dict[str, Any] | None:
    task = tasks_db.get(task_id)
    return task.copy() if task is not None else None


def list_tasks(
    *,
    status: str | None = None,
    priority: str | None = None,
    due_date: str | None = None,
    sort_by: Literal["due_date", "priority", "status"] = "due_date",
    order: Literal["asc", "desc"] = "asc",
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    if sort_by not in {"due_date", "priority", "status"}:
        raise ValueError("sort_by must be due_date, priority, or status")
    if order not in {"asc", "desc"}:
        raise ValueError("order must be asc or desc")

    matching = [
        task
        for task in tasks_db.values()
        if (status is None or task["status"] == status)
        and (priority is None or task["priority"] == priority)
        and (due_date is None or task["due_date"] == due_date)
    ]
    if sort_by == "due_date":
        dated = sorted(
            (task for task in matching if task["due_date"] is not None),
            key=lambda task: task["due_date"],
            reverse=order == "desc",
        )
        undated = [task for task in matching if task["due_date"] is None]
        matching = dated + undated
    else:
        matching.sort(key=lambda task: task[sort_by], reverse=order == "desc")

    return [task.copy() for task in matching[offset : offset + limit]]


def update_task(task_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    task = tasks_db.get(task_id)
    if task is None:
        return None

    for field in ("title", "description", "priority", "status", "due_date"):
        if field in data:
            task[field] = _serialize_value(data[field])
    return task.copy()


def delete_task(task_id: str) -> bool:
    return tasks_db.pop(task_id, None) is not None
