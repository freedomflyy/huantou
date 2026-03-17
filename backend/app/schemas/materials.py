from __future__ import annotations

from pydantic import BaseModel


class MaterialItem(BaseModel):
    id: str
    title: str
    object_key: str
    file_url: str
    mime_type: str | None = None
    category: str | None = None
    subtitle: str | None = None
    badge: str | None = None


class MaterialGroup(BaseModel):
    id: str
    title: str
    items: list[MaterialItem]


class MaterialCatalogResponse(BaseModel):
    home_styles: list[MaterialItem]
    frame_items: list[MaterialItem]
    sticker_groups: list[MaterialGroup]
