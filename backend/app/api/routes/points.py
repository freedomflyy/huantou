from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import PointsLedger, User
from app.schemas.points import (
    PointsBalanceResponse,
    PointsCheckInResponse,
    PointsLedgerItem,
    PointsLedgerListResponse,
    PointsRedeemCodeRequest,
    PointsRedeemCodeResponse,
    PointsRules,
)
from app.services.points import get_points_rules, grant_daily_bonus_if_needed, redeem_points_code

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/balance", response_model=PointsBalanceResponse)
def get_points_balance(
    user: User = Depends(get_current_user),
) -> PointsBalanceResponse:
    return PointsBalanceResponse(
        user_id=user.id,
        points_balance=user.points_balance,
        rules=PointsRules(**get_points_rules().__dict__),
    )


@router.get("/ledgers", response_model=PointsLedgerListResponse)
def list_points_ledgers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PointsLedgerListResponse:
    stmt = (
        select(PointsLedger)
        .where(PointsLedger.user_id == user.id)
        .order_by(PointsLedger.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    total_stmt = select(func.count(PointsLedger.id)).where(PointsLedger.user_id == user.id)

    rows = db.scalars(stmt).all()
    total = db.scalar(total_stmt) or 0

    return PointsLedgerListResponse(
        items=[PointsLedgerItem.model_validate(item) for item in rows],
        total=total,
    )


@router.post("/check-in", response_model=PointsCheckInResponse)
def check_in_points(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PointsCheckInResponse:
    now = datetime.now(timezone.utc)
    granted = grant_daily_bonus_if_needed(db, user=user, operator="miniapp_checkin", now=now)
    db.commit()
    db.refresh(user)
    return PointsCheckInResponse(
        granted=granted,
        points_balance=user.points_balance,
        reward_points=get_points_rules().daily_bonus,
        checked_in_at=now,
    )


@router.post("/redeem-code", response_model=PointsRedeemCodeResponse)
def redeem_code_points(
    payload: PointsRedeemCodeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PointsRedeemCodeResponse:
    try:
        granted, reward_points = redeem_points_code(db, user=user, code=payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(user)
    return PointsRedeemCodeResponse(
        granted=granted,
        points_balance=user.points_balance,
        reward_points=reward_points,
    )
