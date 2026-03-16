from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import Asset, AssetFavorite, StorageProvider, User
from app.schemas.asset import AssetFavoriteActionResponse, AssetItem, AssetListResponse
from app.services.moderation import ModerationError, moderate_image_bytes
from app.services.storage import StorageError, build_access_url, get_local_file_path, upload_binary

router = APIRouter(prefix="/assets", tags=["assets"])


def _load_favorite_asset_ids(db: Session, *, user_id: int, asset_ids: list[UUID]) -> set[UUID]:
    if not asset_ids:
        return set()
    rows = db.scalars(
        select(AssetFavorite.asset_id).where(
            AssetFavorite.user_id == user_id,
            AssetFavorite.asset_id.in_(asset_ids),
        )
    ).all()
    return set(rows)


def _serialize_assets(db: Session, *, user_id: int, rows: list[Asset]) -> list[AssetItem]:
    asset_ids = [item.id for item in rows]
    favorite_ids = _load_favorite_asset_ids(db, user_id=user_id, asset_ids=asset_ids)
    items: list[AssetItem] = []
    for row in rows:
        item = AssetItem.model_validate(row)
        item.file_url = build_access_url(
            storage_provider=row.storage_provider,
            object_key=row.object_key,
            fallback_url=row.file_url,
        )
        item.thumbnail_url = build_access_url(
            storage_provider=row.storage_provider,
            object_key=row.object_key,
            fallback_url=row.thumbnail_url or row.file_url,
        )
        item.is_favorited = row.id in favorite_ids
        items.append(item)
    return items


def _get_my_asset(db: Session, *, user_id: int, asset_id: UUID) -> Asset:
    asset = db.scalar(
        select(Asset).where(
            Asset.id == asset_id,
            Asset.user_id == user_id,
        )
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


def _read_size(image_bytes: bytes) -> tuple[int | None, int | None]:
    try:
        img = Image.open(BytesIO(image_bytes))
        return img.width, img.height
    except Exception:
        return None, None


@router.post("/upload", response_model=AssetItem)
async def upload_asset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetItem:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is too large (>20MB)")

    try:
        verdict = moderate_image_bytes(content)
    except ModerationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if verdict.blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded image blocked by moderation: label={verdict.label}",
        )

    suffix = ""
    if file.filename and "." in file.filename:
        suffix = file.filename.rsplit(".", 1)[-1].lower()
    if suffix not in {"jpg", "jpeg", "png", "webp"}:
        suffix = "jpg"
    if suffix == "jpeg":
        suffix = "jpg"

    object_key = f"upload/{user.id}/{datetime.now(UTC).strftime('%Y%m%d')}/{uuid4()}.{suffix}"
    stored = upload_binary(object_key=object_key, data=content, content_type=file.content_type)
    width, height = _read_size(content)

    now = datetime.now(UTC)
    asset = Asset(
        user_id=user.id,
        source_task_id=None,
        storage_provider=stored.storage_provider,
        object_key=stored.object_key,
        file_url=stored.file_url,
        thumbnail_url=stored.file_url,
        mime_type=stored.mime_type,
        width=width,
        height=height,
        size_bytes=stored.size_bytes,
        expires_at=now + timedelta(days=settings.image_retention_days),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _serialize_assets(db, user_id=user.id, rows=[asset])[0]


@router.get("", response_model=AssetListResponse)
def list_assets(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_removed: bool = Query(default=False),
) -> AssetListResponse:
    stmt = select(Asset).where(Asset.user_id == user.id)
    total_stmt = select(func.count(Asset.id)).where(Asset.user_id == user.id)

    if not include_removed:
        stmt = stmt.where(Asset.is_removed.is_(False))
        total_stmt = total_stmt.where(Asset.is_removed.is_(False))

    stmt = stmt.where(Asset.object_key.notlike("mock/%"))
    total_stmt = total_stmt.where(Asset.object_key.notlike("mock/%"))

    rows = db.scalars(stmt.order_by(Asset.created_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(total_stmt) or 0
    return AssetListResponse(items=_serialize_assets(db, user_id=user.id, rows=rows), total=total)


@router.get("/favorites", response_model=AssetListResponse)
def list_favorite_assets(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AssetListResponse:
    stmt = (
        select(Asset)
        .join(AssetFavorite, AssetFavorite.asset_id == Asset.id)
        .where(
            AssetFavorite.user_id == user.id,
            Asset.user_id == user.id,
            Asset.is_removed.is_(False),
            Asset.object_key.notlike("mock/%"),
        )
        .order_by(AssetFavorite.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    total_stmt = (
        select(func.count(AssetFavorite.id))
        .join(Asset, AssetFavorite.asset_id == Asset.id)
        .where(
            AssetFavorite.user_id == user.id,
            Asset.user_id == user.id,
            Asset.is_removed.is_(False),
            Asset.object_key.notlike("mock/%"),
        )
    )
    rows = db.scalars(stmt).all()
    total = db.scalar(total_stmt) or 0
    return AssetListResponse(items=_serialize_assets(db, user_id=user.id, rows=rows), total=total)


@router.post("/{asset_id}/favorite", response_model=AssetFavoriteActionResponse)
def add_asset_favorite(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetFavoriteActionResponse:
    _get_my_asset(db, user_id=user.id, asset_id=asset_id)

    exists_row = db.scalar(
        select(AssetFavorite).where(
            AssetFavorite.user_id == user.id,
            AssetFavorite.asset_id == asset_id,
        )
    )
    if not exists_row:
        db.add(AssetFavorite(user_id=user.id, asset_id=asset_id))
        db.commit()
    return AssetFavoriteActionResponse(asset_id=asset_id, is_favorited=True)


@router.delete("/{asset_id}/favorite", response_model=AssetFavoriteActionResponse)
def remove_asset_favorite(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetFavoriteActionResponse:
    target = db.scalar(
        select(AssetFavorite).where(
            AssetFavorite.user_id == user.id,
            AssetFavorite.asset_id == asset_id,
        )
    )
    if target:
        db.delete(target)
        db.commit()
    return AssetFavoriteActionResponse(asset_id=asset_id, is_favorited=False)


@router.get("/local/{object_key:path}")
def get_local_asset_file(
    object_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    asset = db.scalar(
        select(Asset).where(
            Asset.user_id == user.id,
            Asset.object_key == object_key,
            Asset.storage_provider == StorageProvider.LOCAL,
        )
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    try:
        path = get_local_file_path(object_key)
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(path=path, media_type=asset.mime_type or "application/octet-stream")
