from __future__ import annotations

import json
from pathlib import Path

from app.models import StorageProvider
from app.schemas.materials import MaterialCatalogResponse, MaterialGroup, MaterialItem
from app.services.storage import build_access_url

APP_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = APP_DIR / "data" / "material_catalog.json"


def _load_catalog_file() -> dict:
    if not CATALOG_PATH.exists():
        return {
            "home_styles": [],
            "frame_items": [],
            "sticker_groups": [],
        }
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _serialize_item(payload: dict) -> MaterialItem:
    storage_provider = StorageProvider(payload.get("storage_provider", StorageProvider.COS.value))
    object_key = payload["object_key"]
    return MaterialItem(
        id=payload["id"],
        title=payload["title"],
        object_key=object_key,
        file_url=build_access_url(
            storage_provider=storage_provider,
            object_key=object_key,
            fallback_url=payload.get("file_url"),
        ),
        mime_type=payload.get("mime_type"),
        category=payload.get("category"),
        subtitle=payload.get("subtitle"),
        badge=payload.get("badge"),
    )


def load_material_catalog() -> MaterialCatalogResponse:
    raw = _load_catalog_file()
    return MaterialCatalogResponse(
        home_styles=[_serialize_item(item) for item in raw.get("home_styles", [])],
        frame_items=[_serialize_item(item) for item in raw.get("frame_items", [])],
        sticker_groups=[
            MaterialGroup(
                id=group["id"],
                title=group["title"],
                items=[_serialize_item(item) for item in group.get("items", [])],
            )
            for group in raw.get("sticker_groups", [])
        ],
    )
