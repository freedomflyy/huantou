from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from urllib.parse import urlparse

import httpx
from PIL import Image

from app.models import GenerationTask
from app.services.storage import StoredObject, upload_binary


class ImageIngestError(Exception):
    pass


@dataclass
class IngestedImage:
    stored: StoredObject
    width: int | None
    height: int | None


def _content_type_to_extension(content_type: str | None) -> str:
    if not content_type:
        return "jpg"
    lower = content_type.lower()
    if "png" in lower:
        return "png"
    if "webp" in lower:
        return "webp"
    if "jpeg" in lower or "jpg" in lower:
        return "jpg"
    return "jpg"


def _guess_extension(url: str, content_type: str | None) -> str:
    parsed = urlparse(url)
    suffix = parsed.path.rsplit(".", 1)[-1].lower() if "." in parsed.path else ""
    if suffix in {"jpg", "jpeg", "png", "webp"}:
        return "jpg" if suffix == "jpeg" else suffix
    return _content_type_to_extension(content_type)


def _read_image_size(data: bytes) -> tuple[int | None, int | None]:
    try:
        img = Image.open(BytesIO(data))
        return img.width, img.height
    except Exception:
        return None, None


def _download_image(url: str) -> tuple[bytes, str]:
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            return resp.content, content_type
    except Exception as exc:
        raise ImageIngestError(f"Failed to download image: {url}, error: {exc}") from exc


def ingest_remote_images(task: GenerationTask, urls: list[str]) -> list[IngestedImage]:
    if not urls:
        return []
    now = datetime.now(UTC)
    items: list[IngestedImage] = []
    for idx, url in enumerate(urls, start=1):
        data, content_type = _download_image(url)
        ext = _guess_extension(url, content_type)
        object_key = (
            f"generated/{task.user_id}/{now.strftime('%Y%m%d')}/{task.id}/result-{idx}.{ext}"
        )
        stored = upload_binary(object_key=object_key, data=data, content_type=content_type)
        width, height = _read_image_size(data)
        items.append(IngestedImage(stored=stored, width=width, height=height))
    return items
