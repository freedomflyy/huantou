from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from app.services.storage import upload_binary

ROOT_DIR = Path(__file__).resolve().parents[2]
SOURCE_ASSET_ROOT = ROOT_DIR / "backend" / "source_assets"
OUTPUT_PATH = ROOT_DIR / "backend" / "app" / "data" / "public_assets.json"

PUBLIC_ASSETS = {
    "login_logo": {
        "source_path": ROOT_DIR / "贴纸、头像框" / "OIP-C.jpg",
        "object_key": "materials/public/login-logo.jpg",
    },
    "review_login_icon": {
        "source_path": ROOT_DIR / "贴纸、头像框" / "贴纸" / "小樱图标" / "雪の图标 微博@草莓味的小熊抱28.png",
        "object_key": "materials/public/review-login-icon.png",
    },
    "home_hero": {
        "source_path": SOURCE_ASSET_ROOT / "home-hero-style-transfer.png",
        "object_key": "materials/public/home-hero-style-transfer.png",
    },
    "share_card": {
        "source_path": SOURCE_ASSET_ROOT / "home-hero-style-transfer.png",
        "object_key": "materials/public/share-card-style-transfer.png",
    },
}


def _upload_file(source_path: Path, object_key: str) -> dict:
    mime_type = mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
    stored = upload_binary(
        object_key=object_key,
        data=source_path.read_bytes(),
        content_type=mime_type,
    )
    return {
        "storage_provider": stored.storage_provider.value,
        "object_key": stored.object_key,
        "file_url": stored.file_url,
        "mime_type": stored.mime_type,
    }


def build_catalog() -> dict:
    catalog: dict[str, dict] = {}
    for key, meta in PUBLIC_ASSETS.items():
        catalog[key] = _upload_file(meta["source_path"], meta["object_key"])
    return catalog


def main() -> None:
    catalog = build_catalog()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"catalog_written={OUTPUT_PATH}")
    print(f"keys={','.join(sorted(catalog.keys()))}")


if __name__ == "__main__":
    main()
