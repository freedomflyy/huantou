from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import TaskProvider, TaskStatus, TaskType


def _read_output_count(params: dict[str, Any]) -> int | None:
    value = params.get("output_count")
    if value is None:
        options = params.get("sequential_image_generation_options")
        if isinstance(options, dict):
            value = options.get("max_images")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("output_count/max_images must be an integer") from None


class TaskCreateRequest(BaseModel):
    task_type: TaskType
    provider: TaskProvider | None = None
    prompt: str | None = None
    negative_prompt: str | None = None
    input_image_url: str | None = None
    reference_image_url: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_task_inputs(self) -> "TaskCreateRequest":
        if self.task_type in {TaskType.IMG2IMG, TaskType.QUICK_EDIT} and not self.input_image_url:
            raise ValueError("input_image_url is required for img2img/quick_edit")
        if self.task_type == TaskType.STYLE_TRANSFER and (
            not self.input_image_url or not self.reference_image_url
        ):
            raise ValueError(
                "input_image_url and reference_image_url are required for style_transfer"
            )
        output_count = _read_output_count(self.params)
        if output_count is not None and not 1 <= output_count <= 6:
            raise ValueError("output_count/max_images must be between 1 and 6")
        return self


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    task_type: TaskType
    provider: TaskProvider
    status: TaskStatus
    prompt: str | None
    negative_prompt: str | None
    input_image_url: str | None
    reference_image_url: str | None
    params: dict[str, Any]
    cost_points: int
    retry_count: int
    error_message: str | None
    queued_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


class MockTaskCompleteRequest(BaseModel):
    file_url: str | None = None
    thumbnail_url: str | None = None


class MockTaskFailRequest(BaseModel):
    error_message: str = "Mock task failed"
    refund_points: bool = True


class MockTaskFailResponse(BaseModel):
    task: TaskResponse
    refund_granted: bool


class TaskExecuteResponse(BaseModel):
    task: TaskResponse
    output_urls: list[str]
    refund_granted: bool = False
