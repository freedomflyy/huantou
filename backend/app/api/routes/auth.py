from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import PointsChangeType, User, UserStatus
from app.schemas.auth import (
    LogoutAllResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    WechatLoginRequest,
    WechatLoginResponse,
)
from app.schemas.user import UserInfo
from app.services.auth_tokens import AuthTokenError, TOKEN_TYPE_REFRESH, create_token_pair, decode_token
from app.services.points import add_points_ledger, get_points_rules, grant_daily_bonus_if_needed
from app.services.refresh_tokens import (
    create_refresh_token_record,
    get_refresh_token_record,
    is_refresh_token_active,
    revoke_all_user_refresh_tokens,
    revoke_refresh_token,
)
from app.services.wechat_auth import WechatAuthError, resolve_openid_from_code

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/wechat-login", response_model=WechatLoginResponse)
def wechat_login(payload: WechatLoginRequest, db: Session = Depends(get_db)) -> WechatLoginResponse:
    now = datetime.now(timezone.utc)
    try:
        openid = resolve_openid_from_code(payload.code)
    except WechatAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    rules = get_points_rules()

    user = db.scalar(select(User).where(User.wx_openid == openid))
    is_new_user = user is None
    signup_bonus_granted = False
    daily_bonus_granted = False

    if not user:
        user = User(
            wx_openid=openid,
            nickname=payload.nickname,
            avatar_url=payload.avatar_url,
            points_balance=0,
        )
        db.add(user)
        db.flush()

        if rules.signup_bonus > 0:
            add_points_ledger(
                db,
                user=user,
                change_type=PointsChangeType.SIGNUP_BONUS,
                delta=rules.signup_bonus,
                reason="new_user_bonus",
                operator="system",
            )
            signup_bonus_granted = True

    if payload.nickname:
        user.nickname = payload.nickname
    if payload.avatar_url:
        user.avatar_url = payload.avatar_url

    daily_bonus_granted = grant_daily_bonus_if_needed(db, user=user, operator="system", now=now)

    user.last_login_at = now
    db.commit()
    db.refresh(user)

    pair = create_token_pair(user.id)
    create_refresh_token_record(
        db,
        user_id=user.id,
        jti=pair.refresh_jti,
        expires_at=pair.refresh_expires_at,
    )
    db.commit()
    return WechatLoginResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
        is_new_user=is_new_user,
        signup_bonus_granted=signup_bonus_granted,
        daily_bonus_granted=daily_bonus_granted,
        user=UserInfo.model_validate(user),
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> RefreshTokenResponse:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type=TOKEN_TYPE_REFRESH)
    except AuthTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    token_row = get_refresh_token_record(db, jti=token_payload.jti)
    if not token_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found")
    if not is_refresh_token_active(token_row):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or expired")

    user = db.scalar(select(User).where(User.id == token_payload.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.status == UserStatus.DISABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")

    pair = create_token_pair(user.id)
    revoke_refresh_token(
        db,
        row=token_row,
        reason="rotated",
        replaced_by_jti=pair.refresh_jti,
    )
    create_refresh_token_record(
        db,
        user_id=user.id,
        jti=pair.refresh_jti,
        expires_at=pair.refresh_expires_at,
    )
    db.commit()
    return RefreshTokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> LogoutResponse:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type=TOKEN_TYPE_REFRESH)
    except AuthTokenError:
        return LogoutResponse(revoked=False)

    token_row = get_refresh_token_record(db, jti=token_payload.jti)
    if not token_row:
        return LogoutResponse(revoked=False)
    if token_row.revoked_at is None:
        revoke_refresh_token(db, row=token_row, reason="logout")
        db.commit()
        return LogoutResponse(revoked=True)
    return LogoutResponse(revoked=False)


@router.post("/logout-all", response_model=LogoutAllResponse)
def logout_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LogoutAllResponse:
    count = revoke_all_user_refresh_tokens(
        db,
        user_id=user.id,
        reason="logout_all",
    )
    db.commit()
    return LogoutAllResponse(revoked_count=count)
