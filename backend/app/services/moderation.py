from __future__ import annotations

import base64
from dataclasses import dataclass

from qcloud_cos import CosConfig, CosS3Client

from app.core.config import settings


class ModerationError(Exception):
    pass


@dataclass(frozen=True)
class ModerationResult:
    blocked: bool
    label: str | None
    state: str | None
    reason: str | None = None


def _blocked_labels() -> set[str]:
    raw = settings.moderation_block_labels or ""
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def is_blocked_label(label: str | None) -> bool:
    if not label:
        return False
    lower = label.strip().lower()
    if lower == "normal":
        return False
    blocked = _blocked_labels()
    if not blocked:
        return lower != "normal"
    return lower in blocked


def _build_cos_client() -> CosS3Client:
    if not settings.cos_secret_id or not settings.cos_secret_key:
        raise ModerationError("COS credentials are missing")
    if not settings.cos_region:
        raise ModerationError("COS_REGION is missing")

    cfg = CosConfig(
        Region=settings.cos_region,
        SecretId=settings.cos_secret_id,
        SecretKey=settings.cos_secret_key,
        Scheme="https",
    )
    return CosS3Client(cfg)


def moderate_text(content: str) -> ModerationResult:
    if settings.moderation_provider.lower() == "mock":
        return ModerationResult(blocked=False, label="Normal", state="Success")
    if settings.moderation_provider.lower() not in {"tencent", "cos", "tencent_cos"}:
        raise ModerationError(f"Unsupported moderation provider: {settings.moderation_provider}")
    if not settings.cos_bucket:
        raise ModerationError("COS_BUCKET is missing")

    client = _build_cos_client()
    try:
        resp = client.ci_auditing_text_submit(
            Bucket=settings.cos_bucket,
            Content=content.encode("utf-8"),
            DetectType=settings.moderation_text_detect_type,
            BizType=settings.moderation_tencent_biz_type,
            CallbackVersion="Simple",
        )
    except Exception as exc:
        raise ModerationError(f"Text moderation request failed: {exc}") from exc

    detail = resp.get("JobsDetail") or {}
    state = detail.get("State")
    label = detail.get("Label")
    if state and state != "Success":
        raise ModerationError(f"Text moderation failed: state={state}")
    return ModerationResult(blocked=is_blocked_label(label), label=label, state=state)


def moderate_image_url(image_url: str) -> ModerationResult:
    if settings.moderation_provider.lower() == "mock":
        return ModerationResult(blocked=False, label="Normal", state="Success")
    if settings.moderation_provider.lower() not in {"tencent", "cos", "tencent_cos"}:
        raise ModerationError(f"Unsupported moderation provider: {settings.moderation_provider}")
    if not settings.cos_bucket:
        raise ModerationError("COS_BUCKET is missing")

    client = _build_cos_client()
    try:
        resp = client.ci_auditing_image_batch(
            Bucket=settings.cos_bucket,
            Input=[{"Url": image_url}],
            DetectType=settings.moderation_image_detect_type,
            BizType=settings.moderation_tencent_biz_type,
            Async=0,
        )
    except Exception as exc:
        raise ModerationError(f"Image moderation request failed: {exc}") from exc

    details = (resp.get("JobsDetail") or [{}])[0]
    state = details.get("State")
    label = details.get("Label")
    code = details.get("Code")
    message = details.get("Message")
    if state and state != "Success":
        raise ModerationError(
            f"Image moderation failed: state={state}, code={code}, message={message}"
        )
    return ModerationResult(blocked=is_blocked_label(label), label=label, state=state)


def moderate_image_bytes(image_bytes: bytes) -> ModerationResult:
    if settings.moderation_provider.lower() == "mock":
        return ModerationResult(blocked=False, label="Normal", state="Success")
    if settings.moderation_provider.lower() not in {"tencent", "cos", "tencent_cos"}:
        raise ModerationError(f"Unsupported moderation provider: {settings.moderation_provider}")
    if not settings.cos_bucket:
        raise ModerationError("COS_BUCKET is missing")

    client = _build_cos_client()
    try:
        resp = client.ci_auditing_image_batch(
            Bucket=settings.cos_bucket,
            Input=[{"Content": base64.b64encode(image_bytes).decode("utf-8")}],
            DetectType=settings.moderation_image_detect_type,
            BizType=settings.moderation_tencent_biz_type,
            Async=0,
        )
    except Exception as exc:
        raise ModerationError(f"Image moderation request failed: {exc}") from exc

    details = (resp.get("JobsDetail") or [{}])[0]
    state = details.get("State")
    label = details.get("Label")
    code = details.get("Code")
    message = details.get("Message")
    if state and state != "Success":
        raise ModerationError(
            f"Image moderation failed: state={state}, code={code}, message={message}"
        )
    return ModerationResult(blocked=is_blocked_label(label), label=label, state=state)
