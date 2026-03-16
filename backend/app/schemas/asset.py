from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import StorageProvider


class AssetItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    source_task_id: UUID | None
    storage_provider: StorageProvider
    object_key: str
    file_url: str
    thumbnail_url: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    size_bytes: int | None
    is_removed: bool
    removed_reason: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_favorited: bool = False


class AssetListResponse(BaseModel):
    items: list[AssetItem]
    total: int


class AssetFavoriteActionResponse(BaseModel):
    asset_id: UUID
    is_favorited: bool
