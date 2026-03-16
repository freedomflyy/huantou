import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PointsChangeType(str, enum.Enum):
    SIGNUP_BONUS = "signup_bonus"
    DAILY_BONUS = "daily_bonus"
    GENERATION_COST = "generation_cost"
    REFUND = "refund"
    ADMIN_ADJUST = "admin_adjust"


class PointsLedger(Base):
    __tablename__ = "points_ledgers"
    __table_args__ = (
        Index("ix_points_ledgers_user_created", "user_id", "created_at"),
        Index("ix_points_ledgers_task_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generation_tasks.id", ondelete="SET NULL")
    )

    change_type: Mapped[PointsChangeType] = mapped_column(
        Enum(PointsChangeType, name="points_change_type", native_enum=False),
        nullable=False,
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    operator: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="points_ledgers")
    task = relationship("GenerationTask", back_populates="points_ledgers")

