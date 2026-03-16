from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.moderation_callback import ingest_tencent_ci_callback

router = APIRouter(prefix="/moderation", tags=["moderation"])


def _verify_callback_token(
    token: str | None,
    x_callback_token: str | None,
) -> None:
    expected = settings.moderation_callback_token
    if not expected:
        return
    provided = token or x_callback_token
    if provided != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid moderation callback token",
        )


@router.post("/tencent/callback")
async def tencent_callback(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Query(default=None),
    x_callback_token: str | None = Header(default=None, alias="X-Callback-Token"),
) -> dict[str, Any]:
    _verify_callback_token(token, x_callback_token)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {exc}",
        ) from exc

    if not isinstance(payload, (dict, list)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Callback payload must be a JSON object or array",
        )

    processed = ingest_tencent_ci_callback(db, payload=payload, source="callback")
    db.commit()
    return {
        "ok": True,
        "processed": processed,
    }
