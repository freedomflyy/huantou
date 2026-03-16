from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import PointsChangeType


class PointsRules(BaseModel):
    signup_bonus: int
    daily_bonus: int
    redeem_points: int
    txt2img_cost: int
    img2img_cost: int
    style_transfer_cost: int


class PointsLedgerItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: UUID | None
    change_type: PointsChangeType
    delta: int
    balance_after: int
    reason: str | None
    operator: str | None
    created_at: datetime


class PointsBalanceResponse(BaseModel):
    user_id: int
    points_balance: int
    rules: PointsRules


class PointsLedgerListResponse(BaseModel):
    items: list[PointsLedgerItem]
    total: int


class PointsCheckInResponse(BaseModel):
    granted: bool
    points_balance: int
    reward_points: int
    checked_in_at: datetime


class PointsRedeemCodeRequest(BaseModel):
    code: str


class PointsRedeemCodeResponse(BaseModel):
    granted: bool
    points_balance: int
    reward_points: int
