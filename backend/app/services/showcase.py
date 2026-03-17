from __future__ import annotations

import json
from pathlib import Path

from app.models import StorageProvider
from app.schemas.showcase import ShowcaseItem, ShowcaseListResponse
from app.services.storage import build_access_url

APP_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = APP_DIR / "data" / "showcase_gallery.json"


def _load_catalog_file() -> dict:
    if not CATALOG_PATH.exists():
        return {"items": []}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _resolve_url(payload: dict, fallback_key: str = "file_url") -> str:
    if not payload:
        return ""
    object_key = payload.get("object_key")
    if not object_key:
        return payload.get(fallback_key) or ""
    storage_provider = StorageProvider(payload.get("storage_provider", StorageProvider.COS.value))
    return build_access_url(
        storage_provider=storage_provider,
        object_key=object_key,
        fallback_url=payload.get(fallback_key),
    )


def load_showcase(*, limit: int | None = None) -> ShowcaseListResponse:
    raw = _load_catalog_file()
    items = raw.get("items") or []
    ordered = sorted(
        items,
        key=lambda item: (
            int(item.get("sort_order") or 0),
            item.get("published_at") or "",
        ),
    )
    if limit is not None:
        ordered = ordered[:limit]

    return ShowcaseListResponse(
        items=[
            ShowcaseItem(
                id=item.get("id") or "",
                title=item.get("title") or "",
                subtitle=item.get("subtitle") or "",
                badge=item.get("badge") or "",
                creator_name=item.get("creator_name") or "幻头官方",
                style_name=item.get("style_name") or "",
                file_url=_resolve_url(item, "file_url"),
                thumbnail_url=_resolve_url(item, "thumbnail_url") or _resolve_url(item, "file_url"),
                published_at=item.get("published_at"),
                sort_order=int(item.get("sort_order") or 0),
            )
            for item in ordered
        ],
        total=len(items),
    )
