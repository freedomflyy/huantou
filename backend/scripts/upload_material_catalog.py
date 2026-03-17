from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from app.services.storage import upload_binary

ROOT_DIR = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT_DIR / "贴纸、头像框"
OUTPUT_PATH = ROOT_DIR / "backend" / "app" / "data" / "material_catalog.json"

STYLE_META = {
    "3D萌趣.png": {
        "id": "style-3d-cute",
        "title": "3D萌趣",
        "subtitle": "立体生动，灵动可爱",
        "badge": "立体生动",
        "object_key": "materials/home-styles/style-3d-cute.png",
    },
    "二次元.png": {
        "id": "style-anime",
        "title": "二次元",
        "subtitle": "梦幻动漫，适合年轻感头像",
        "badge": "梦幻动漫",
        "object_key": "materials/home-styles/style-anime.png",
    },
    "动漫风.png": {
        "id": "style-cartoon",
        "title": "动漫风",
        "subtitle": "线条鲜明，角色感更强，适合年轻化头像",
        "badge": "人气动漫",
        "object_key": "materials/home-styles/style-cartoon.png",
    },
    "国潮古风.png": {
        "id": "style-guochao",
        "title": "国潮古风",
        "subtitle": "东方审美和华丽配色，更有国风记忆点",
        "badge": "国潮古风",
        "object_key": "materials/home-styles/style-guochao.png",
    },
    "水彩油画.png": {
        "id": "style-watercolor-oil",
        "title": "水彩油画",
        "subtitle": "笔触柔和细腻，适合偏艺术感头像",
        "badge": "艺术笔触",
        "object_key": "materials/home-styles/style-watercolor-oil.png",
    },
    "清新插画.png": {
        "id": "style-fresh-illustration",
        "title": "清新插画",
        "subtitle": "柔和清透，适合日常头像",
        "badge": "清新插画",
        "object_key": "materials/home-styles/style-fresh-illustration.png",
    },
    "清新日常.png": {
        "id": "style-fresh-daily",
        "title": "清新日常",
        "subtitle": "自然明亮，更贴近日常社交头像氛围",
        "badge": "日常耐看",
        "object_key": "materials/home-styles/style-fresh-daily.png",
    },
    "赛博.png": {
        "id": "style-cyber",
        "title": "赛博风",
        "subtitle": "霓虹质感，更有个性记忆点",
        "badge": "赛博未来",
        "object_key": "materials/home-styles/style-cyber.png",
    },
}

STICKER_GROUPS = {
    "小怪物": {"id": "monster", "title": "小怪物"},
    "小樱图标": {"id": "sakura", "title": "小樱图标"},
    "小红帽": {"id": "redhood", "title": "小红帽"},
    "小黄鸡": {"id": "yellowchick", "title": "小黄鸡"},
    "玉桂狗": {"id": "cinnamoroll", "title": "玉桂狗"},
    "雪の图标": {"id": "snowicons", "title": "雪の图标"},
}

FRAME_SOURCE_OVERRIDES = {
    1: SOURCE_DIR / "头像框" / "河马素材35.png",
}

REMOVED_FRAME_SOURCES = {
    (SOURCE_DIR / "头像框" / "河马素材03.jpg").resolve(),
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


def _iter_frame_sources(frame_dir: Path) -> list[Path]:
    ordered: list[Path] = []
    used_paths: set[Path] = set()

    for index in sorted(FRAME_SOURCE_OVERRIDES):
        source_path = FRAME_SOURCE_OVERRIDES[index]
        if not source_path.exists():
            continue
        ordered.append(source_path)
        used_paths.add(source_path.resolve())

    for source_path in sorted(frame_dir.iterdir()):
        if not source_path.is_file():
            continue
        if source_path.resolve() in used_paths:
            continue
        if source_path.resolve() in REMOVED_FRAME_SOURCES:
            continue
        ordered.append(source_path)

    return ordered


def build_catalog() -> dict:
    home_styles: list[dict] = []
    frames: list[dict] = []
    sticker_groups: list[dict] = []

    for filename, meta in STYLE_META.items():
        source_path = SOURCE_DIR / "风格展示" / filename
        uploaded = _upload_file(source_path, meta["object_key"])
        home_styles.append(
            {
                "id": meta["id"],
                "title": meta["title"],
                "subtitle": meta["subtitle"],
                "badge": meta["badge"],
                **uploaded,
            }
        )

    frame_dir = SOURCE_DIR / "头像框"
    for index, source_path in enumerate(_iter_frame_sources(frame_dir), start=1):
        object_key = f"materials/frames/frame-{index:02d}{source_path.suffix.lower()}"
        uploaded = _upload_file(source_path, object_key)
        frames.append(
            {
                "id": f"frame-{index:02d}",
                "title": f"头像框 {index:02d}",
                "category": "头像框",
                **uploaded,
            }
        )

    sticker_root = SOURCE_DIR / "贴纸"
    for folder_name, group_meta in STICKER_GROUPS.items():
        group_dir = sticker_root / folder_name
        if not group_dir.exists():
            continue
        items: list[dict] = []
        for index, source_path in enumerate(sorted(group_dir.iterdir()), start=1):
            if not source_path.is_file():
                continue
            object_key = f"materials/stickers/{group_meta['id']}/item-{index:02d}{source_path.suffix.lower()}"
            uploaded = _upload_file(source_path, object_key)
            items.append(
                {
                    "id": f"{group_meta['id']}-{index:02d}",
                    "title": f"{group_meta['title']} {index:02d}",
                    "category": group_meta["title"],
                    **uploaded,
                }
            )
        sticker_groups.append(
            {
                "id": group_meta["id"],
                "title": group_meta["title"],
                "items": items,
            }
        )

    return {
        "home_styles": home_styles,
        "frame_items": frames,
        "sticker_groups": sticker_groups,
    }


def main() -> None:
    catalog = build_catalog()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"catalog_written={OUTPUT_PATH}")
    print(f"home_styles={len(catalog['home_styles'])}")
    print(f"frames={len(catalog['frame_items'])}")
    print(f"sticker_groups={len(catalog['sticker_groups'])}")
    print(f"stickers={sum(len(group['items']) for group in catalog['sticker_groups'])}")


if __name__ == "__main__":
    main()
