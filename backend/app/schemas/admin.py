from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import TaskStatus, UserStatus


class AdminUserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wx_openid: str | None
    nickname: str | None
    status: UserStatus
    points_balance: int
    created_at: datetime
    last_login_at: datetime | None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]
    total: int


class AdminUserStatusUpdateRequest(BaseModel):
    status: UserStatus


class AdminPointsAdjustRequest(BaseModel):
    delta: int
    reason: str = "admin_adjust"


class AdminTaskRetryResponse(BaseModel):
    task_id: UUID
    status: TaskStatus
    retry_count: int


class AdminAssetTakeDownRequest(BaseModel):
    reason: str = "admin_take_down"


class AdminAssetTakeDownResponse(BaseModel):
    asset_id: UUID
    is_removed: bool
    removed_reason: str | None


class AdminOverviewResponse(BaseModel):
    users_total: int
    active_users_total: int
    disabled_users_total: int
    tasks_total: int
    tasks_queued: int
    tasks_running: int
    tasks_failed: int
    tasks_succeeded: int
    assets_total: int
    assets_removed_total: int
