from datetime import datetime
from typing import Any
from uuid import UUID as UUIDType

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ModerationAudit(Base):
    __tablename__ = "moderation_audits"
    __table_args__ = (
        Index("ix_moderation_audits_created", "created_at"),
        Index("ix_moderation_audits_job_id", "job_id"),
        Index("ix_moderation_audits_blocked_created", "blocked", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), default="tencent_ci", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="callback", nullable=False)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_ref: Mapped[str | None] = mapped_column(Text)

    state: Mapped[str | None] = mapped_column(String(32))
    label: Mapped[str | None] = mapped_column(String(64))
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    job_id: Mapped[str | None] = mapped_column(String(128))
    detail_code: Mapped[str | None] = mapped_column(String(64))
    detail_message: Mapped[str | None] = mapped_column(String(255))

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    asset_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL")
    )

    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User")
    asset = relationship("Asset")
