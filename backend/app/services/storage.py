from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from qcloud_cos import CosConfig, CosS3Client

from app.core.config import settings
from app.models import StorageProvider

APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR.parent
LOCAL_ASSET_ROOT = BACKEND_DIR / "storage" / "assets"


class StorageError(Exception):
    pass


@dataclass
class StoredObject:
    storage_provider: StorageProvider
    object_key: str
    file_url: str
    mime_type: str | None
    size_bytes: int


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def _build_cos_client() -> CosS3Client:
    if not settings.cos_secret_id or not settings.cos_secret_key:
        raise StorageError("COS credentials are missing")
    if not settings.cos_bucket or not settings.cos_region:
        raise StorageError("COS_BUCKET/COS_REGION is missing")

    config = CosConfig(
        Region=settings.cos_region,
        SecretId=settings.cos_secret_id,
        SecretKey=settings.cos_secret_key,
        Scheme="https",
    )
    return CosS3Client(config)


def _guess_mime_type(filename: str, fallback: str = "application/octet-stream") -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or fallback


def _build_local_url(object_key: str) -> str:
    encoded = quote(object_key)
    path = f"{settings.api_v1_prefix}/assets/local/{encoded}"
    if settings.public_base_url:
        return _join_url(settings.public_base_url, path)
    return path


def _build_cos_url(object_key: str) -> str:
    if settings.cos_public_base_url:
        return _join_url(settings.cos_public_base_url, object_key)
    if not settings.cos_bucket or not settings.cos_region:
        raise StorageError("COS_BUCKET/COS_REGION is missing")
    return f"https://{settings.cos_bucket}.cos.{settings.cos_region}.myqcloud.com/{object_key}"


def _upload_local(*, object_key: str, data: bytes, content_type: str) -> StoredObject:
    target = LOCAL_ASSET_ROOT / object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return StoredObject(
        storage_provider=StorageProvider.LOCAL,
        object_key=object_key,
        file_url=_build_local_url(object_key),
        mime_type=content_type,
        size_bytes=len(data),
    )


def _upload_cos(*, object_key: str, data: bytes, content_type: str) -> StoredObject:
    client = _build_cos_client()
    client.put_object(
        Bucket=settings.cos_bucket,
        Key=object_key,
        Body=data,
        ContentType=content_type,
    )
    return StoredObject(
        storage_provider=StorageProvider.COS,
        object_key=object_key,
        file_url=_build_cos_url(object_key),
        mime_type=content_type,
        size_bytes=len(data),
    )


def upload_binary(*, object_key: str, data: bytes, content_type: str | None = None) -> StoredObject:
    if not object_key:
        raise StorageError("object_key is required")
    if not data:
        raise StorageError("data is empty")

    mime_type = content_type or _guess_mime_type(object_key)
    provider = settings.storage_provider.lower()
    if provider == "cos":
        return _upload_cos(object_key=object_key, data=data, content_type=mime_type)
    return _upload_local(object_key=object_key, data=data, content_type=mime_type)


def build_access_url(
    *,
    storage_provider: StorageProvider,
    object_key: str,
    fallback_url: str | None = None,
) -> str:
    if storage_provider == StorageProvider.LOCAL:
        return fallback_url or _build_local_url(object_key)

    if storage_provider == StorageProvider.COS:
        if settings.cos_public_base_url:
            return _join_url(settings.cos_public_base_url, object_key)
        try:
            client = _build_cos_client()
            return client.get_presigned_download_url(
                Bucket=settings.cos_bucket,
                Key=object_key,
                Expired=max(300, settings.cos_sign_url_expire_seconds),
            )
        except Exception:
            if fallback_url:
                return fallback_url
            return _build_cos_url(object_key)

    return fallback_url or ""


def delete_object(*, storage_provider: StorageProvider, object_key: str) -> bool:
    if not object_key:
        return False

    if storage_provider == StorageProvider.LOCAL:
        path = get_local_file_path(object_key)
        if path.exists():
            path.unlink()
            return True
        return False

    if storage_provider == StorageProvider.COS:
        client = _build_cos_client()
        client.delete_object(Bucket=settings.cos_bucket, Key=object_key)
        return True

    return False


def get_local_file_path(object_key: str) -> Path:
    candidate = (LOCAL_ASSET_ROOT / object_key).resolve()
    root = LOCAL_ASSET_ROOT.resolve()
    if root not in candidate.parents and candidate != root:
        raise StorageError("invalid object key")
    return candidate
