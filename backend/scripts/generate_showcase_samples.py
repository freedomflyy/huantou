from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Asset, GenerationTask, TaskProvider, TaskStatus, TaskType, User  # noqa: E402
from app.services.task_executor import execute_task_now  # noqa: E402

OUTPUT_PATH = ROOT_DIR / "app" / "data" / "showcase_gallery.json"
OFFICIAL_OPENID = "official_showcase_bot"
OFFICIAL_NICKNAME = "幻头官方"

STYLE_CASES: list[dict[str, Any]] = [
    {
        "style_name": "3D萌趣",
        "badge": "3D萌趣",
        "subtitle": "立体感柔和，适合年轻友好的社交头像",
        "prompt": "生成三张不同细节的亚洲年轻人头像，微信头像构图，3D萌趣风格，奶油光影，面部清晰，表情亲和，纯净背景，半身近景，适合小程序头像展示",
        "titles": ["3D萌趣 · 元气少女", "3D萌趣 · 邻家少年", "3D萌趣 · 微笑女孩"],
    },
    {
        "style_name": "二次元",
        "badge": "二次元",
        "subtitle": "梦幻动漫氛围，更适合偏年轻感头像",
        "prompt": "生成三张不同细节的二次元人物头像，动漫光影，五官精致，线条柔和，色彩梦幻，人物居中，清晰面部，适合作为微信头像",
        "titles": ["二次元 · 樱色少女", "二次元 · 清冷少年", "二次元 · 柔光侧颜"],
    },
    {
        "style_name": "动漫风",
        "badge": "动漫风",
        "subtitle": "角色感更强，适合明亮个性的头像表达",
        "prompt": "生成三张不同细节的动漫风头像，角色感强，服装简洁，背景干净，亮色氛围，人物直视镜头，适合用作头像封面",
        "titles": ["动漫风 · 校园主角", "动漫风 · 活力少年", "动漫风 · 治愈女孩"],
    },
    {
        "style_name": "国潮古风",
        "badge": "国潮古风",
        "subtitle": "东方审美和华丽配色，更有文化记忆点",
        "prompt": "生成三张不同细节的国潮古风头像，东方审美，华丽发饰，精致妆容，人物半身，古典背景虚化，颜色高级，适合社交头像",
        "titles": ["国潮古风 · 桃夭", "国潮古风 · 月白", "国潮古风 · 锦年"],
    },
    {
        "style_name": "水彩油画",
        "badge": "水彩油画",
        "subtitle": "艺术笔触和肌理感更强，适合展示型头像",
        "prompt": "生成三张不同细节的水彩油画头像，柔和笔触，肌理丰富，人物清晰，色彩高级，背景干净，适合文艺气质的头像展示",
        "titles": ["水彩油画 · 午后光影", "水彩油画 · 温柔侧脸", "水彩油画 · 复古气质"],
    },
    {
        "style_name": "清新插画",
        "badge": "清新插画",
        "subtitle": "柔和清透，适合治愈感和日常头像",
        "prompt": "生成三张不同细节的清新插画头像，浅色背景，人物五官自然，线条简洁，治愈氛围，头像构图，适合社交软件头像",
        "titles": ["清新插画 · 晨光", "清新插画 · 轻氧", "清新插画 · 干净笑容"],
    },
    {
        "style_name": "清新日常",
        "badge": "清新日常",
        "subtitle": "自然明亮，更贴近日常社交头像氛围",
        "prompt": "生成三张不同细节的清新日常真人写真风头像，明亮自然光，真实五官，简洁服饰，背景柔和，适合微信头像",
        "titles": ["清新日常 · 通勤", "清新日常 · 周末", "清新日常 · 轻熟气质"],
    },
    {
        "style_name": "赛博风",
        "badge": "赛博风",
        "subtitle": "霓虹质感和未来感，更有个性辨识度",
        "prompt": "生成三张不同细节的赛博风头像，霓虹边光，未来感人物肖像，高对比色彩，面部清晰，黑色背景，适合作为个性头像",
        "titles": ["赛博风 · 蓝紫霓虹", "赛博风 · 未来少年", "赛博风 · 冷感主角"],
    },
]


def ensure_official_user(db) -> User:
    user = db.scalar(select(User).where(User.wx_openid == OFFICIAL_OPENID))
    if user:
        if user.nickname != OFFICIAL_NICKNAME:
            user.nickname = OFFICIAL_NICKNAME
            db.commit()
            db.refresh(user)
        return user

    user = User(
        wx_openid=OFFICIAL_OPENID,
        nickname=OFFICIAL_NICKNAME,
        avatar_url=None,
        points_balance=999999,
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_task(user: User, case: dict[str, Any]) -> GenerationTask:
    now = datetime.now(UTC)
    return GenerationTask(
        user_id=user.id,
        task_type=TaskType.TXT2IMG,
        provider=TaskProvider.VOLCENGINE,
        status=TaskStatus.QUEUED,
        prompt=case["prompt"],
        params={
            "style_name": case["style_name"],
            "ratio": "1:1",
            "output_count": 3,
            "official_showcase": True,
        },
        cost_points=0,
        queued_at=now,
    )


def collect_task_assets(db, task_id) -> list[Asset]:
    return db.scalars(
        select(Asset)
        .where(Asset.source_task_id == task_id)
        .order_by(Asset.created_at.asc(), Asset.id.asc())
    ).all()


def build_item(*, order: int, case: dict[str, Any], asset: Asset, task: GenerationTask, title: str) -> dict[str, Any]:
    return {
        "id": f"official-{order:02d}",
        "title": title,
        "subtitle": case["subtitle"],
        "badge": case["badge"],
        "creator_name": OFFICIAL_NICKNAME,
        "style_name": case["style_name"],
        "storage_provider": asset.storage_provider.value,
        "object_key": asset.object_key,
        "file_url": asset.file_url,
        "thumbnail_url": asset.thumbnail_url or asset.file_url,
        "published_at": (asset.created_at or datetime.now(UTC)).isoformat(),
        "sort_order": order,
        "source_task_id": str(task.id),
        "source_asset_id": str(asset.id),
    }


def write_catalog(items: list[dict[str, Any]]) -> None:
    OUTPUT_PATH.write_text(
        json.dumps({"items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    db = SessionLocal()
    generated_items: list[dict[str, Any]] = []
    try:
        user = ensure_official_user(db)
        order = 1
        failures: list[str] = []

        for case in STYLE_CASES:
            task = create_task(user, case)
            db.add(task)
            db.commit()
            db.refresh(task)

            result = execute_task_now(db, task=task, user=user)
            if result.task.status != TaskStatus.SUCCEEDED:
                failures.append(f"{case['style_name']}: {result.task.error_message or 'unknown error'}")
                continue

            assets = collect_task_assets(db, task.id)
            for idx, asset in enumerate(assets[:3]):
                generated_items.append(
                    build_item(
                        order=order,
                        case=case,
                        asset=asset,
                        task=task,
                        title=case["titles"][idx] if idx < len(case["titles"]) else f"{case['style_name']} · 样本 {idx + 1}",
                    )
                )
                order += 1

        write_catalog(generated_items)
        print(
            json.dumps(
                {
                    "generated_total": len(generated_items),
                    "failures": failures,
                    "output": str(OUTPUT_PATH),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
