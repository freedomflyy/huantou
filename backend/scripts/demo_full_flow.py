from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import User, UserStatus


def _build_demo_image_bytes(*, size: tuple[int, int], rgb: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", size=size, color=rgb)
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _safe_preview(data: Any, max_len: int = 180) -> str:
    raw = json.dumps(data, ensure_ascii=False, default=str)
    if len(raw) <= max_len:
        return raw
    return f"{raw[:max_len]}...(truncated)"


def _pick_ai_provider(mode: str) -> str:
    if mode in {"mock", "volcengine"}:
        return mode
    return "volcengine" if settings.volcengine_api_key else "mock"


def _is_debug_header_enabled() -> bool:
    enabled = settings.auth_allow_debug_user_header
    if settings.app_env.lower() == "prod" and settings.auth_force_disable_debug_user_header_in_prod:
        enabled = False
    return enabled


def _ensure_debug_demo_user(run_id: str) -> int:
    openid = f"debug_demo_{run_id.replace('-', '_')[:48]}"
    with SessionLocal() as db:
        user = db.query(User).filter(User.wx_openid == openid).first()
        if user:
            return int(user.id)
        user = User(
            wx_openid=openid,
            nickname=f"DebugDemo-{run_id[-6:]}",
            status=UserStatus.ACTIVE,
            points_balance=300,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return int(user.id)


def _task_prompt(task_type: str) -> str:
    if task_type == "txt2img":
        return "写实头像，柔和光线，高清细节，自然肤色"
    if task_type == "img2img":
        return "保持人物主体，增强清晰度与质感，背景简洁"
    if task_type == "style_transfer":
        return "将图1转为图2的艺术风格，保持主体面部特征"
    return "quick edit demo"


def main() -> None:
    parser = argparse.ArgumentParser(description="Huanto full feature demo flow")
    parser.add_argument(
        "--ai-provider",
        choices=["auto", "mock", "volcengine"],
        default="auto",
        help="AI provider used by txt2img/img2img/style_transfer",
    )
    parser.add_argument(
        "--output",
        default="reports/demo_full_flow_latest.json",
        help="output report path relative to backend root",
    )
    parser.add_argument(
        "--wechat-code",
        default="",
        help="real wechat code for auth_login_mode=wechat (if empty, script may fall back to debug header)",
    )
    parser.add_argument(
        "--use-uploaded-input",
        action="store_true",
        help="use uploaded COS image URL as img2img/style/quick_edit input (default uses stable public sample URLs)",
    )
    args = parser.parse_args()

    output_path = (ROOT_DIR / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ai_provider = _pick_ai_provider(args.ai_provider)
    now = datetime.now(UTC).isoformat()
    run_id = f"demo-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
    report: dict[str, Any] = {
        "run_id": run_id,
        "time": now,
        "env": {
            "app_env": settings.app_env,
            "auth_login_mode": settings.auth_login_mode,
            "storage_provider": settings.storage_provider,
            "moderation_provider": settings.moderation_provider,
            "ai_provider_for_demo": ai_provider,
        },
        "steps": [],
    }

    def add_step(name: str, ok: bool, detail: str, data: Any | None = None) -> None:
        report["steps"].append(
            {
                "name": name,
                "ok": ok,
                "detail": detail,
                "data": data,
            }
        )

    client = TestClient(app)
    user_headers: dict[str, str] = {}
    admin_headers: dict[str, str] = {}
    access_token = ""
    refresh_token = ""
    user_id: int | None = None
    demo_asset_id: str | None = None
    demo_object_key: str | None = None
    demo_asset_url: str | None = None

    try:
        login_code = args.wechat_code.strip() or f"{run_id}-login"
        login_payload = {
            "code": login_code,
            "nickname": f"DemoUser-{run_id[-6:]}",
        }
        login_resp = client.post("/api/v1/auth/wechat-login", json=login_payload)
        if login_resp.status_code == 200:
            login_data = login_resp.json()
            access_token = login_data["access_token"]
            refresh_token = login_data["refresh_token"]
            user_id = int(login_data["user"]["id"])
            user_headers = {"Authorization": f"Bearer {access_token}"}
            add_step("auth_login", True, "login success", {"user_id": user_id})
        else:
            if _is_debug_header_enabled():
                if settings.auth_login_mode == "wechat" and not args.wechat_code.strip():
                    add_step(
                        "auth_login",
                        True,
                        "skipped real wechat login (no --wechat-code), fallback to debug header",
                        login_resp.json(),
                    )
                else:
                    add_step(
                        "auth_login",
                        False,
                        f"status={login_resp.status_code}",
                        login_resp.json(),
                    )
                user_id = _ensure_debug_demo_user(run_id)
                user_headers = {"X-User-Id": str(user_id)}
                add_step(
                    "auth_fallback_debug_header",
                    True,
                    "wechat login failed; fallback to debug user header",
                    {"user_id": user_id},
                )
            else:
                add_step(
                    "auth_login",
                    False,
                    f"status={login_resp.status_code}",
                    login_resp.json(),
                )
                raise RuntimeError("Login failed and debug header is disabled")

        balance_resp = client.get("/api/v1/points/balance", headers=user_headers)
        if balance_resp.status_code == 200:
            add_step(
                "points_balance",
                True,
                "balance fetched",
                {
                    "points_balance": balance_resp.json().get("points_balance"),
                    "rules": balance_resp.json().get("rules"),
                },
            )
        else:
            add_step("points_balance", False, f"status={balance_resp.status_code}", balance_resp.json())

        image_a = _build_demo_image_bytes(size=(640, 640), rgb=(40, 120, 220))
        image_b = _build_demo_image_bytes(size=(640, 640), rgb=(220, 120, 40))
        upload_a = client.post(
            "/api/v1/assets/upload",
            headers=user_headers,
            files={"file": ("demo-a.png", image_a, "image/png")},
        )
        upload_b = client.post(
            "/api/v1/assets/upload",
            headers=user_headers,
            files={"file": ("demo-b.png", image_b, "image/png")},
        )
        if upload_a.status_code == 200 and upload_b.status_code == 200:
            up_a_data = upload_a.json()
            up_b_data = upload_b.json()
            demo_asset_id = up_a_data.get("id")
            demo_object_key = up_a_data.get("object_key")
            demo_asset_url = up_a_data.get("file_url")
            add_step(
                "assets_upload",
                True,
                "2 demo images uploaded",
                {
                    "asset_a": {"id": up_a_data.get("id"), "url": up_a_data.get("file_url")},
                    "asset_b": {"id": up_b_data.get("id"), "url": up_b_data.get("file_url")},
                },
            )
        else:
            add_step(
                "assets_upload",
                False,
                f"status_a={upload_a.status_code}, status_b={upload_b.status_code}",
                {
                    "upload_a": upload_a.json() if upload_a.headers.get("content-type", "").startswith("application/json") else upload_a.text,
                    "upload_b": upload_b.json() if upload_b.headers.get("content-type", "").startswith("application/json") else upload_b.text,
                },
            )

        input_url = "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imageToimage.png"
        ref_url = "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imagesToimage_2.png"
        if args.use_uploaded_input and settings.storage_provider.lower() == "cos" and demo_asset_url:
            input_url = demo_asset_url

        task_cases = [
            {
                "name": "task_txt2img",
                "payload": {
                    "task_type": "txt2img",
                    "provider": ai_provider,
                    "prompt": _task_prompt("txt2img"),
                },
            },
            {
                "name": "task_img2img",
                "payload": {
                    "task_type": "img2img",
                    "provider": ai_provider,
                    "prompt": _task_prompt("img2img"),
                    "input_image_url": input_url,
                },
            },
            {
                "name": "task_style_transfer",
                "payload": {
                    "task_type": "style_transfer",
                    "provider": ai_provider,
                    "prompt": _task_prompt("style_transfer"),
                    "input_image_url": input_url,
                    "reference_image_url": ref_url,
                },
            },
            {
                "name": "task_quick_edit",
                "payload": {
                    "task_type": "quick_edit",
                    "provider": "mock",
                    "input_image_url": input_url,
                    "params": {
                        "operations": {
                            "rotate": 4,
                            "brightness": 1.08,
                            "saturation": 1.06,
                            "contrast": 1.05,
                        },
                        "output": {"format": "jpeg", "quality": 90},
                    },
                },
            },
        ]

        for case in task_cases:
            create_resp = client.post("/api/v1/tasks", headers=user_headers, json=case["payload"])
            if create_resp.status_code != 200:
                add_step(case["name"], False, f"create status={create_resp.status_code}", create_resp.json())
                continue
            task_id = create_resp.json()["id"]
            execute_resp = client.post(f"/api/v1/tasks/{task_id}/execute", headers=user_headers)
            if execute_resp.status_code != 200:
                add_step(
                    case["name"],
                    False,
                    f"execute status={execute_resp.status_code}",
                    {"task_id": task_id, "resp": execute_resp.json()},
                )
                continue
            execute_data = execute_resp.json()
            task_status = execute_data.get("task", {}).get("status")
            add_step(
                case["name"],
                task_status == "succeeded",
                f"task_status={task_status}",
                {
                    "task_id": task_id,
                    "output_count": len(execute_data.get("output_urls", [])),
                    "refund_granted": execute_data.get("refund_granted"),
                },
            )

        assets_resp = client.get("/api/v1/assets?limit=20", headers=user_headers)
        if assets_resp.status_code == 200:
            assets_data = assets_resp.json()
            total_assets = int(assets_data.get("total", 0))
            add_step("assets_list", True, "assets fetched", {"total": total_assets})
            if total_assets > 0:
                first_asset_id = assets_data["items"][0]["id"]
                fav_resp = client.post(f"/api/v1/assets/{first_asset_id}/favorite", headers=user_headers)
                fav_list_resp = client.get("/api/v1/assets/favorites?limit=20", headers=user_headers)
                unfav_resp = client.delete(
                    f"/api/v1/assets/{first_asset_id}/favorite",
                    headers=user_headers,
                )
                fav_ok = (
                    fav_resp.status_code == 200
                    and fav_list_resp.status_code == 200
                    and unfav_resp.status_code == 200
                )
                add_step(
                    "favorites_flow",
                    fav_ok,
                    f"favorite statuses={fav_resp.status_code}/{fav_list_resp.status_code}/{unfav_resp.status_code}",
                    {
                        "favorited_total": fav_list_resp.json().get("total") if fav_list_resp.status_code == 200 else None
                    },
                )
        else:
            add_step("assets_list", False, f"status={assets_resp.status_code}", assets_resp.json())

        if refresh_token:
            refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
            if refresh_resp.status_code == 200:
                refresh_data = refresh_resp.json()
                access_token = refresh_data["access_token"]
                refresh_token = refresh_data["refresh_token"]
                user_headers = {"Authorization": f"Bearer {access_token}"}
                add_step("auth_refresh", True, "refresh success")
            else:
                add_step("auth_refresh", False, f"status={refresh_resp.status_code}", refresh_resp.json())
        else:
            add_step("auth_refresh", True, "skipped: no refresh token session")

        if settings.admin_api_key:
            admin_headers = {"X-Admin-Key": settings.admin_api_key}
            overview = client.get("/api/v1/admin/overview", headers=admin_headers)
            users = client.get("/api/v1/admin/users?limit=20", headers=admin_headers)
            tasks = client.get("/api/v1/admin/tasks?limit=20", headers=admin_headers)
            assets = client.get("/api/v1/admin/assets?limit=20", headers=admin_headers)
            audits = client.get("/api/v1/admin/moderation-audits?limit=20", headers=admin_headers)
            metrics = client.get("/api/v1/health/metrics", headers=admin_headers)
            admin_ok = all(
                r.status_code == 200 for r in (overview, users, tasks, assets, audits, metrics)
            )
            add_step(
                "admin_and_metrics",
                admin_ok,
                (
                    "overview/users/tasks/assets/audits/metrics status="
                    f"{overview.status_code}/{users.status_code}/{tasks.status_code}/"
                    f"{assets.status_code}/{audits.status_code}/{metrics.status_code}"
                ),
            )

            if user_id is not None:
                adjust_resp = client.post(
                    f"/api/v1/admin/users/{user_id}/points-adjust",
                    headers=admin_headers,
                    json={"delta": 1, "reason": "demo_full_flow_plus_1"},
                )
                add_step(
                    "admin_points_adjust",
                    adjust_resp.status_code == 200,
                    f"status={adjust_resp.status_code}",
                    adjust_resp.json() if adjust_resp.status_code == 200 else _safe_preview(adjust_resp.text),
                )

            if demo_asset_id:
                take_down_resp = client.post(
                    f"/api/v1/admin/assets/{demo_asset_id}/take-down",
                    headers=admin_headers,
                    json={"reason": "demo_full_flow_manual_take_down"},
                )
                add_step(
                    "admin_asset_take_down",
                    take_down_resp.status_code == 200,
                    f"status={take_down_resp.status_code}",
                    take_down_resp.json()
                    if take_down_resp.status_code == 200
                    else _safe_preview(take_down_resp.text),
                )
        else:
            add_step("admin_and_metrics", False, "ADMIN_API_KEY is empty; skipped")

        if demo_asset_url or demo_object_key:
            callback_payload = {
                "EventName": "ObjectCreated:ImageAudit",
                "JobsDetail": {
                    "Code": "0",
                    "Message": "SUCCESS",
                    "JobId": f"{run_id}-callback",
                    "State": "Success",
                    "Label": "Porn",
                    "Suggestion": "Block",
                    "Result": 1,
                    "Type": "Image",
                    "Object": demo_object_key,
                    "Url": demo_asset_url,
                },
            }
            callback_path = "/api/v1/moderation/tencent/callback"
            if settings.moderation_callback_token:
                callback_path = f"{callback_path}?token={settings.moderation_callback_token}"
            callback_resp = client.post(callback_path, json=callback_payload)
            callback_ok = callback_resp.status_code == 200
            add_step(
                "moderation_callback_ingest",
                callback_ok,
                f"status={callback_resp.status_code}",
                callback_resp.json()
                if callback_resp.headers.get("content-type", "").startswith("application/json")
                else callback_resp.text,
            )
        else:
            add_step("moderation_callback_ingest", True, "skipped: no uploaded asset to bind callback")

        if admin_headers:
            audits_after = client.get("/api/v1/admin/moderation-audits?limit=10", headers=admin_headers)
            add_step(
                "moderation_audits_verify",
                audits_after.status_code == 200,
                f"status={audits_after.status_code}",
                {"total": audits_after.json().get("total")} if audits_after.status_code == 200 else audits_after.text,
            )

        ledgers_resp = client.get("/api/v1/points/ledgers?limit=20", headers=user_headers)
        add_step(
            "points_ledgers",
            ledgers_resp.status_code == 200,
            f"status={ledgers_resp.status_code}",
            {"total": ledgers_resp.json().get("total")}
            if ledgers_resp.status_code == 200
            else _safe_preview(ledgers_resp.text),
        )

        if refresh_token:
            logout_resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
            add_step(
                "auth_logout",
                logout_resp.status_code == 200 and bool(logout_resp.json().get("revoked")),
                f"status={logout_resp.status_code}",
                logout_resp.json() if logout_resp.status_code == 200 else _safe_preview(logout_resp.text),
            )
        else:
            add_step("auth_logout", True, "skipped: no refresh token session")

    except Exception as exc:
        add_step("demo_runtime", False, f"unhandled exception: {exc}")

    total = len(report["steps"])
    passed = len([s for s in report["steps"] if s["ok"] is True])
    failed = len([s for s in report["steps"] if s["ok"] is False])
    report["summary"] = {
        "total_steps": total,
        "passed": passed,
        "failed": failed,
    }

    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nreport written to: {output_path}")


if __name__ == "__main__":
    main()
