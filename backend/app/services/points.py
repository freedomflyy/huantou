from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import PointsChangeType, PointsLedger, TaskType, User


@dataclass(frozen=True)
class PointsRuleSnapshot:
    signup_bonus: int
    daily_bonus: int
    redeem_points: int
    txt2img_cost: int
    img2img_cost: int
    style_transfer_cost: int


def get_points_rules() -> PointsRuleSnapshot:
    return PointsRuleSnapshot(
        signup_bonus=settings.points_signup_bonus,
        daily_bonus=settings.points_daily_bonus,
        redeem_points=settings.points_redeem_points,
        txt2img_cost=settings.points_txt2img_cost,
        img2img_cost=settings.points_img2img_cost,
        style_transfer_cost=settings.points_style_transfer_cost,
    )


def get_task_cost(task_type: TaskType) -> int:
    rules = get_points_rules()
    mapping = {
        TaskType.TXT2IMG: rules.txt2img_cost,
        TaskType.IMG2IMG: rules.img2img_cost,
        TaskType.STYLE_TRANSFER: rules.style_transfer_cost,
        TaskType.QUICK_EDIT: 0,
    }
    return mapping[task_type]


def add_points_ledger(
    db: Session,
    *,
    user: User,
    change_type: PointsChangeType,
    delta: int,
    reason: str | None = None,
    operator: str | None = None,
    task_id: UUID | None = None,
) -> PointsLedger:
    next_balance = user.points_balance + delta
    if next_balance < 0:
        raise ValueError("Insufficient points balance")

    user.points_balance = next_balance
    ledger = PointsLedger(
        user_id=user.id,
        task_id=task_id,
        change_type=change_type,
        delta=delta,
        balance_after=user.points_balance,
        reason=reason,
        operator=operator,
    )
    db.add(ledger)
    return ledger


def has_daily_bonus_today(
    db: Session,
    *,
    user_id: int,
    now: datetime | None = None,
) -> bool:
    current = now or datetime.now(timezone.utc)
    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    stmt = (
        select(PointsLedger.id)
        .where(
            PointsLedger.user_id == user_id,
            PointsLedger.change_type == PointsChangeType.DAILY_BONUS,
            PointsLedger.created_at >= day_start,
            PointsLedger.created_at < day_end,
        )
        .limit(1)
    )
    return db.scalar(stmt) is not None


def grant_daily_bonus_if_needed(
    db: Session,
    *,
    user: User,
    operator: str = "system",
    now: datetime | None = None,
) -> bool:
    rules = get_points_rules()
    if rules.daily_bonus <= 0:
        return False
    if has_daily_bonus_today(db, user_id=user.id, now=now):
        return False
    add_points_ledger(
        db,
        user=user,
        change_type=PointsChangeType.DAILY_BONUS,
        delta=rules.daily_bonus,
        reason="daily_login_bonus",
        operator=operator,
    )
    return True


def normalize_redeem_code(value: str | None) -> str:
    return (value or "").strip().lower()


def redeem_points_code(
    db: Session,
    *,
    user: User,
    code: str,
) -> tuple[bool, int]:
    expected = normalize_redeem_code(settings.points_redeem_code)
    if not expected:
        raise ValueError("激活码兑换暂未开启")

    normalized = normalize_redeem_code(code)
    if normalized != expected:
        raise ValueError("激活码不正确")

    reward_points = max(0, settings.points_redeem_points)
    reason = f"redeem_code:{expected}"
    db.scalar(
        select(User.id)
        .where(User.id == user.id)
        .with_for_update()
    )
    exists = db.scalar(
        select(PointsLedger.id)
        .where(
            PointsLedger.user_id == user.id,
            PointsLedger.change_type == PointsChangeType.ADMIN_ADJUST,
            PointsLedger.reason == reason,
        )
        .limit(1)
    )
    if exists:
        return False, reward_points

    add_points_ledger(
        db,
        user=user,
        change_type=PointsChangeType.ADMIN_ADJUST,
        delta=reward_points,
        reason=reason,
        operator="redeem_code",
    )
    return True, reward_points


def has_task_refund(db: Session, *, task_id: UUID) -> bool:
    stmt = (
        select(PointsLedger.id)
        .where(
            PointsLedger.task_id == task_id,
            PointsLedger.change_type == PointsChangeType.REFUND,
        )
        .limit(1)
    )
    return db.scalar(stmt) is not None
