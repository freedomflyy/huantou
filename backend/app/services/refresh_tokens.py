from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefreshToken


def create_refresh_token_record(
    db: Session,
    *,
    user_id: int,
    jti: str,
    expires_at: datetime,
) -> RefreshToken:
    row = RefreshToken(
        user_id=user_id,
        jti=jti,
        expires_at=expires_at,
    )
    db.add(row)
    return row


def get_refresh_token_record(db: Session, *, jti: str) -> RefreshToken | None:
    return db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))


def is_refresh_token_active(row: RefreshToken, *, now: datetime | None = None) -> bool:
    clock = now or datetime.now(UTC)
    if row.revoked_at is not None:
        return False
    return row.expires_at > clock


def revoke_refresh_token(
    db: Session,
    *,
    row: RefreshToken,
    reason: str,
    replaced_by_jti: str | None = None,
) -> None:
    now = datetime.now(UTC)
    row.revoked_at = now
    row.revoke_reason = reason
    row.replaced_by_jti = replaced_by_jti
    row.last_used_at = now


def revoke_all_user_refresh_tokens(
    db: Session,
    *,
    user_id: int,
    reason: str,
) -> int:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    ).all()
    for row in rows:
        row.revoked_at = now
        row.revoke_reason = reason
        row.last_used_at = now
    return len(rows)
