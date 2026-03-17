from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ShowcaseItem(BaseModel):
    id: str
    title: str
    subtitle: str
    badge: str
    creator_name: str
    style_name: str
    file_url: str
    thumbnail_url: str
    published_at: datetime | None = None
    sort_order: int = 0


class ShowcaseListResponse(BaseModel):
    items: list[ShowcaseItem]
    total: int
