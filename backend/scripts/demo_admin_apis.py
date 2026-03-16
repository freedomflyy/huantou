from __future__ import annotations

import json
import os
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


def _load_env() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _ensure_demo_user() -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.wx_openid == "admin_demo_user"))
        if not user:
            user = User(
                wx_openid="admin_demo_user",
                nickname="AdminDemoUser",
                points_balance=100,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user.id


def main() -> None:
    _load_env()
    admin_key = os.environ.get("ADMIN_API_KEY")
    if not admin_key:
        raise SystemExit("ADMIN_API_KEY is required in env for admin demo")

    target_user_id = _ensure_demo_user()
    client = TestClient(app)
    headers = {"X-Admin-Key": admin_key}

    overview = client.get("/api/v1/admin/overview", headers=headers)
    overview.raise_for_status()

    users = client.get("/api/v1/admin/users?limit=5", headers=headers)
    users.raise_for_status()

    points = client.post(
        f"/api/v1/admin/users/{target_user_id}/points-adjust",
        headers=headers,
        json={"delta": 5, "reason": "admin_demo_plus_5"},
    )
    points.raise_for_status()

    status_resp = client.post(
        f"/api/v1/admin/users/{target_user_id}/status",
        headers=headers,
        json={"status": "active"},
    )
    status_resp.raise_for_status()

    result = {
        "overview_keys": sorted(overview.json().keys()),
        "users_total": users.json().get("total"),
        "target_user_points": points.json().get("points_balance"),
        "target_user_status": status_resp.json().get("status"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
