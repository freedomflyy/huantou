from __future__ import annotations

from fastapi import APIRouter

from app.schemas.public_assets import PublicAssetsResponse
from app.services.public_assets import load_public_assets

router = APIRouter(prefix="/public-assets", tags=["public-assets"])


@router.get("", response_model=PublicAssetsResponse)
def get_public_assets() -> PublicAssetsResponse:
    return load_public_assets()
