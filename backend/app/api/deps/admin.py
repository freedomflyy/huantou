from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_admin(
    x_admin_key: str | None = Header(default=None),
) -> bool:
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY is not configured",
        )
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )
    return True
