from __future__ import annotations

import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.main import app
from app.models import User


def _ensure_demo_user() -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.wx_openid == "demo_quick_edit_user"))
        if not user:
            user = User(
                wx_openid="demo_quick_edit_user",
                nickname="DemoQuickEditUser",
                points_balance=300,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user.id


def main() -> None:
    user_id = _ensure_demo_user()
    client = TestClient(app)
    headers = {"X-User-Id": str(user_id)}

    create_payload = {
        "task_type": "quick_edit",
        "provider": "mock",
        "input_image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imageToimage.png",
        "params": {
            "operations": {
                "crop": {"x": 24, "y": 24, "width": 700, "height": 700},
                "rotate": 6,
                "saturation": 1.1,
                "brightness": 1.05,
                "contrast": 1.08,
            },
            "output": {"format": "jpeg", "quality": 90},
        },
    }

    create_resp = client.post("/api/v1/tasks", json=create_payload, headers=headers)
    create_resp.raise_for_status()
    task_id = create_resp.json()["id"]

    execute_resp = client.post(f"/api/v1/tasks/{task_id}/execute", headers=headers)
    execute_resp.raise_for_status()
    execute_payload = execute_resp.json()

    assets_resp = client.get("/api/v1/assets?limit=5", headers=headers)
    assets_resp.raise_for_status()
    assets_payload = assets_resp.json()
    latest_asset_id = assets_payload["items"][0]["id"]

    fav_resp = client.post(f"/api/v1/assets/{latest_asset_id}/favorite", headers=headers)
    fav_resp.raise_for_status()

    fav_list_resp = client.get("/api/v1/assets/favorites?limit=5", headers=headers)
    fav_list_resp.raise_for_status()
    fav_list_payload = fav_list_resp.json()

    unfav_resp = client.delete(f"/api/v1/assets/{latest_asset_id}/favorite", headers=headers)
    unfav_resp.raise_for_status()

    output = {
        "user_id": user_id,
        "task_id": task_id,
        "task_status": execute_payload["task"]["status"],
        "output_urls": execute_payload["output_urls"],
        "assets_total": assets_payload["total"],
        "favorite_total_after_add": fav_list_payload["total"],
        "favorite_remove_state": unfav_resp.json()["is_favorited"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
