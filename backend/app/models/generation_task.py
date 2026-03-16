import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaskType(str, enum.Enum):
    TXT2IMG = "txt2img"
    IMG2IMG = "img2img"
    STYLE_TRANSFER = "style_transfer"
    QUICK_EDIT = "quick_edit"


class TaskProvider(str, enum.Enum):
    MOCK = "mock"
    LOCAL_COMFYUI = "local_comfyui"
    VOLCENGINE = "volcengine"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class GenerationTask(Base):
    __tablename__ = "generation_tasks"
    __table_args__ = (
        Index("ix_generation_tasks_user_created", "user_id", "created_at"),
        Index("ix_generation_tasks_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="task_type", native_enum=False), nullable=False
    )
    provider: Mapped[TaskProvider] = mapped_column(
        Enum(TaskProvider, name="task_provider", native_enum=False),
        default=TaskProvider.MOCK,
        nullable=False,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", native_enum=False),
        default=TaskStatus.PENDING,
        nullable=False,
    )

    prompt: Mapped[str | None] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    input_image_url: Mapped[str | None] = mapped_column(Text)
    reference_image_url: Mapped[str | None] = mapped_column(Text)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    cost_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="tasks")
    points_ledgers = relationship("PointsLedger", back_populates="task")
    assets = relationship("Asset", back_populates="source_task")

