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
from app.models import GenerationTask, User
from app.services.task_executor import execute_next_queued_task


def _ensure_user() -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.wx_openid == "queue_demo_user"))
        if not user:
            user = User(wx_openid="queue_demo_user", nickname="QueueDemoUser", points_balance=200)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user.id


def main() -> None:
    uid = _ensure_user()
    client = TestClient(app)
    headers = {"X-User-Id": str(uid)}

    create = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"task_type": "quick_edit", "provider": "mock", "input_image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imageToimage.png", "params": {"operations": {"rotate": 3}}},
    )
    create.raise_for_status()
    task_id = create.json()["id"]

    with SessionLocal() as db:
        result = execute_next_queued_task(db)
        processed_task_id = str(result.task.id) if result else None

    with SessionLocal() as db:
        task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
        status = task.status.value if task else None

    print(
        json.dumps(
            {
                "created_task_id": task_id,
                "processed_task_id": processed_task_id,
                "final_status": status,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
