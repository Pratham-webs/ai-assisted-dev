from uuid import UUID

from fastapi import FastAPI, HTTPException, Response, status

from app.database import (
    create_task as add_task_record,
    delete_task as delete_task_record,
    get_task as get_task_record,
    list_tasks as get_task_records,
    update_task as update_task_record,
)
from app.models import TaskCreate, TaskResponse


app = FastAPI(
    title="Student Task Management API",
    description="Create, view, update, and delete academic tasks.",
    version="1.0.0",
)


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate) -> TaskResponse:
    saved_task = add_task_record(task.model_dump())
    return TaskResponse.model_validate(saved_task)


@app.get("/tasks", response_model=list[TaskResponse])
def list_tasks() -> list[TaskResponse]:
    tasks = get_task_records()
    return [TaskResponse.model_validate(task) for task in tasks]


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID) -> TaskResponse:
    task = get_task_record(str(task_id))
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
    return TaskResponse.model_validate(task)


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def replace_task(task_id: UUID, replacement: TaskCreate) -> TaskResponse:
    task = update_task_record(str(task_id), replacement.model_dump())
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
    return TaskResponse.model_validate(task)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task(task_id: UUID) -> Response:
    if not delete_task_record(str(task_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
