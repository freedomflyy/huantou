from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from app.core.config import settings
from app.models import GenerationTask, TaskType


class VolcengineImageError(Exception):
    pass


CLIENT_METADATA_KEYS = {
    "style_name",
    "styleName",
    "ratio",
    "aspect_ratio",
    "preset",
    "tool",
    "output_count",
}


def _collect_urls(value: Any, bucket: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"url", "image_url"} and isinstance(item, str) and item.startswith("http"):
                bucket.append(item)
            _collect_urls(item, bucket)
        return

    if isinstance(value, list):
        for item in value:
            _collect_urls(item, bucket)


def _dedupe_preserve_order(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        result.append(url)
    return result


def _resolve_output_count(params: dict[str, Any]) -> int:
    raw = params.get("output_count")
    if raw is None:
        options = params.get("sequential_image_generation_options")
        if isinstance(options, dict):
            raw = options.get("max_images")
    try:
        count = int(raw) if raw is not None else 1
    except (TypeError, ValueError):
        count = 1
    return max(1, min(count, 6))


def _build_effective_prompt(task: GenerationTask, params: dict[str, Any]) -> str:
    prompt = (task.prompt or "").strip()
    extras: list[str] = []
    requested_count = _resolve_output_count(params)

    style_name = params.get("style_name") or params.get("styleName")
    preset = params.get("preset")
    tool = params.get("tool")

    if style_name and str(style_name) not in prompt:
        extras.append(f"风格为{style_name}")
    if preset and str(preset) not in prompt:
        extras.append(f"视觉预设为{preset}")
    if tool and str(tool) not in prompt:
        extras.append(f"处理方向为{tool}")
    if requested_count > 1:
        extras.append(
            f"请生成共{requested_count}张风格统一、主体一致但细节略有变化的候选图"
        )

    if extras:
        if prompt:
            return f"{prompt}，{'，'.join(extras)}"
        return "，".join(extras)
    return prompt


def _apply_multi_image_options(payload: dict[str, Any], params: dict[str, Any]) -> None:
    requested_count = _resolve_output_count(params)
    raw_mode = params.get("sequential_image_generation")
    mode = raw_mode if raw_mode in {"auto", "disabled"} else None
    options = params.get("sequential_image_generation_options")
    if not isinstance(options, dict):
        options = {}
    options = dict(options)

    if requested_count > 1:
        payload["sequential_image_generation"] = "auto"
        payload["sequential_image_generation_options"] = {
            **options,
            "max_images": requested_count,
        }
        return

    payload["sequential_image_generation"] = mode or "disabled"
    if options.get("max_images"):
        payload["sequential_image_generation_options"] = {
            **options,
            "max_images": requested_count,
        }


def _build_payload(task: GenerationTask) -> dict[str, Any]:
    params = dict(task.params or {})
    payload: dict[str, Any] = {
        "model": settings.volcengine_model,
        "prompt": _build_effective_prompt(task, params),
        "response_format": "url",
        "size": settings.volcengine_image_size,
        "stream": False,
        "watermark": settings.volcengine_watermark,
    }

    if task.task_type in {TaskType.IMG2IMG, TaskType.QUICK_EDIT}:
        payload["image"] = task.input_image_url
    elif task.task_type == TaskType.STYLE_TRANSFER:
        payload["image"] = [task.input_image_url, task.reference_image_url]

    _apply_multi_image_options(payload, params)

    # Filter out app-only metadata while allowing future Volcengine fields to pass through.
    for key in CLIENT_METADATA_KEYS:
        params.pop(key, None)

    if "stream" in params:
        # The backend waits for final URLs and stores outputs, so force non-streaming mode.
        params.pop("stream", None)

    # Allow per-task overrides while keeping sane defaults.
    payload.update(params)
    return payload


def generate_images(task: GenerationTask) -> list[str]:
    if not settings.volcengine_api_key:
        raise VolcengineImageError("VOLCENGINE_API_KEY is missing")

    endpoint = settings.volcengine_endpoint
    if not endpoint:
        raise VolcengineImageError("VOLCENGINE_ENDPOINT is missing")

    payload = _build_payload(task)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.volcengine_api_key}",
    }

    try:
        with httpx.Client(timeout=settings.volcengine_timeout_seconds) as client:
            resp = client.post(endpoint, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise VolcengineImageError(
                    f"Volcengine HTTP {resp.status_code}: {resp.text[:300]}"
                )
            data = resp.json()
    except VolcengineImageError:
        raise
    except Exception as exc:  # pragma: no cover
        raise VolcengineImageError(f"Volcengine request failed: {exc}") from exc

    urls: list[str] = []
    _collect_urls(data, urls)
    deduped = _dedupe_preserve_order(urls)
    if not deduped:
        raise VolcengineImageError("No image URL returned by Volcengine")
    return deduped
