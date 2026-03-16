from __future__ import annotations

from typing import Any
from urllib.parse import unquote, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, ModerationAudit
from app.services.moderation import is_blocked_label


def _to_details(payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    details = payload.get("JobsDetail")
    if isinstance(details, dict):
        return [details]
    if isinstance(details, list):
        return [item for item in details if isinstance(item, dict)]
    return []


def _extract_object_key_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    path = (parsed.path or "").lstrip("/")
    if not path:
        return None
    return unquote(path)


def _is_blocked_from_detail(detail: dict[str, Any]) -> bool:
    label = detail.get("Label")
    if is_blocked_label(label):
        return True
    suggestion = str(detail.get("Suggestion") or "").strip().lower()
    if suggestion in {"block", "review"}:
        return True
    result = str(detail.get("Result") or "").strip()
    if result and result not in {"0", "normal"}:
        return True
    return False


def _guess_target_type(payload: dict[str, Any] | list[dict[str, Any]], detail: dict[str, Any]) -> str:
    payload_dict = payload if isinstance(payload, dict) else {}
    raw_type = str(detail.get("Type") or payload_dict.get("Type") or "").lower()
    if "text" in raw_type:
        return "text"
    if "image" in raw_type:
        return "image"
    if detail.get("Object") or detail.get("Url"):
        return "image"
    return "unknown"


def _find_asset(db: Session, *, object_key: str | None, url: str | None) -> Asset | None:
    if object_key:
        asset = db.scalar(
            select(Asset)
            .where(Asset.object_key == object_key)
            .order_by(Asset.created_at.desc())
            .limit(1)
        )
        if asset:
            return asset
    if url:
        asset = db.scalar(
            select(Asset)
            .where(Asset.file_url == url)
            .order_by(Asset.created_at.desc())
            .limit(1)
        )
        if asset:
            return asset
    return None


def ingest_tencent_ci_callback(
    db: Session,
    *,
    payload: dict[str, Any] | list[dict[str, Any]],
    source: str = "callback",
) -> int:
    details = _to_details(payload)
    if not details:
        return 0

    processed = 0
    event_name = payload.get("EventName") if isinstance(payload, dict) else None
    for detail in details:
        object_key = str(detail.get("Object") or "").strip() or None
        url = str(detail.get("Url") or "").strip() or None
        if not object_key:
            object_key = _extract_object_key_from_url(url)

        asset = _find_asset(db, object_key=object_key, url=url)
        blocked = _is_blocked_from_detail(detail)
        label = detail.get("Label")
        state = detail.get("State")
        job_id = detail.get("JobId")
        code = detail.get("Code")
        message = detail.get("Message")
        target_ref = object_key or url or str(detail.get("Text") or "")[:200]

        if blocked and asset and not asset.is_removed:
            asset.is_removed = True
            asset.removed_reason = f"moderation_callback:{label or 'unknown'}"

        db.add(
            ModerationAudit(
                provider="tencent_ci",
                source=source,
                target_type=_guess_target_type(payload, detail),
                target_ref=target_ref,
                state=state,
                label=label,
                blocked=blocked,
                job_id=job_id,
                detail_code=code,
                detail_message=message,
                user_id=asset.user_id if asset else None,
                asset_id=asset.id if asset else None,
                raw_payload={
                    "event": event_name,
                    "detail": detail,
                },
            )
        )
        processed += 1
    return processed
