from __future__ import annotations

import json
from pathlib import Path

from app.models import StorageProvider
from app.schemas.public_assets import PublicAssetsResponse
from app.services.storage import build_access_url

APP_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = APP_DIR / "data" / "public_assets.json"


def _load_catalog_file() -> dict:
    if not CATALOG_PATH.exists():
        return {}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _resolve_url(payload: dict) -> str:
    if not payload:
        return ""
    object_key = payload.get("object_key")
    if not object_key:
        return payload.get("file_url") or ""
    storage_provider = StorageProvider(payload.get("storage_provider", StorageProvider.COS.value))
    return build_access_url(
        storage_provider=storage_provider,
        object_key=object_key,
        fallback_url=payload.get("file_url"),
    )


def load_public_assets() -> PublicAssetsResponse:
    raw = _load_catalog_file()
    login_logo = raw.get("login_logo") or {}
    home_hero = raw.get("home_hero") or {}
    share_card = raw.get("share_card") or home_hero
    return PublicAssetsResponse(
        login_logo_url=_resolve_url(login_logo),
        home_hero_url=_resolve_url(home_hero),
        share_card_url=_resolve_url(share_card),
    )
