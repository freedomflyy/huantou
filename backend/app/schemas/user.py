from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import UserStatus


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wx_openid: str | None
    nickname: str | None
    avatar_url: str | None
    status: UserStatus
    points_balance: int
    created_at: datetime
    updated_at: datetime

