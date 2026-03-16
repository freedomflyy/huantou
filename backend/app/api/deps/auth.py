from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import User, UserStatus
from app.services.auth_tokens import AuthTokenError, TOKEN_TYPE_ACCESS, decode_token


def _extract_user_id(
    authorization: str | None,
    x_user_id: str | None,
) -> int:
    debug_header_enabled = settings.auth_allow_debug_user_header
    mock_token_enabled = settings.auth_accept_mock_token
    is_prod = settings.app_env.lower() == "prod"
    if is_prod and settings.auth_force_disable_debug_user_header_in_prod:
        debug_header_enabled = False
    if is_prod and settings.auth_force_disable_mock_token_in_prod:
        mock_token_enabled = False

    if x_user_id and not debug_header_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id header is disabled",
        )

    if debug_header_enabled and x_user_id:
        try:
            return int(x_user_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid X-User-Id header",
            ) from exc

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization schema",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if mock_token_enabled and token.startswith("mock-"):
        user_id_raw = token.removeprefix("mock-")
        try:
            return int(user_id_raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            ) from exc

    try:
        payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
        return payload.user_id
    except AuthTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> User:
    user_id = _extract_user_id(authorization=authorization, x_user_id=x_user_id)
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if user.status == UserStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled",
        )
    return user
