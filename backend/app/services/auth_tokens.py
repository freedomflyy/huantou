from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings


class AuthTokenError(Exception):
    pass


TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    refresh_jti: str
    refresh_expires_at: datetime
    token_type: str
    expires_in: int


@dataclass(frozen=True)
class DecodedToken:
    user_id: int
    token_type: str
    jti: str
    expires_at: datetime


def _create_token(user_id: int, token_type: str, expires_delta: timedelta) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    exp = now + expires_delta
    jti = str(uuid4())
    payload = {
        "sub": str(user_id),
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, exp


def create_token_pair(user_id: int) -> TokenPair:
    access_expire = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    refresh_expire = timedelta(days=settings.jwt_refresh_token_expire_days)
    access_token, _, _ = _create_token(user_id, TOKEN_TYPE_ACCESS, access_expire)
    refresh_token, refresh_jti, refresh_expires_at = _create_token(
        user_id,
        TOKEN_TYPE_REFRESH,
        refresh_expire,
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        refresh_jti=refresh_jti,
        refresh_expires_at=refresh_expires_at,
        token_type="bearer",
        expires_in=int(access_expire.total_seconds()),
    )


def decode_token(token: str, *, expected_type: str) -> DecodedToken:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise AuthTokenError("Token expired") from exc
    except InvalidTokenError as exc:
        raise AuthTokenError("Invalid token") from exc

    token_type = str(payload.get("typ", ""))
    if token_type != expected_type:
        raise AuthTokenError(f"Invalid token type: expected={expected_type}, got={token_type}")

    sub = payload.get("sub")
    jti = str(payload.get("jti") or "")
    exp_raw = payload.get("exp")
    if not jti:
        raise AuthTokenError("Invalid token jti")
    try:
        user_id = int(sub)
    except (TypeError, ValueError) as exc:
        raise AuthTokenError("Invalid token subject") from exc
    try:
        expires_at = datetime.fromtimestamp(int(exp_raw), tz=UTC)
    except Exception as exc:
        raise AuthTokenError("Invalid token exp") from exc
    return DecodedToken(
        user_id=user_id,
        token_type=token_type,
        jti=jti,
        expires_at=expires_at,
    )
