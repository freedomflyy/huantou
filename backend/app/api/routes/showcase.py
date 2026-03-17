from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.showcase import ShowcaseListResponse
from app.services.showcase import load_showcase

router = APIRouter(prefix="/showcase", tags=["showcase"])


@router.get("", response_model=ShowcaseListResponse)
def get_showcase(limit: int = Query(default=24, ge=1, le=100)) -> ShowcaseListResponse:
    return load_showcase(limit=limit)
