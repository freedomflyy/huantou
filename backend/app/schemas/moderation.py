from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ModerationAuditItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    source: str
    target_type: str
    target_ref: str | None
    state: str | None
    label: str | None
    blocked: bool
    job_id: str | None
    detail_code: str | None
    detail_message: str | None
    user_id: int | None
    asset_id: UUID | None
    raw_payload: dict[str, Any]
    created_at: datetime


class ModerationAuditListResponse(BaseModel):
    items: list[ModerationAuditItem]
    total: int
