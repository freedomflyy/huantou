from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO

import httpx
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.models import GenerationTask
from app.services.storage import StoredObject, upload_binary


class QuickEditError(Exception):
    pass


@dataclass
class QuickEditResult:
    stored: StoredObject
    width: int
    height: int


def _safe_float(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_source_image(url: str) -> Image.Image:
    if not url:
        raise QuickEditError("input_image_url is required")
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            image_bytes = resp.content
        img = Image.open(BytesIO(image_bytes))
        img.load()
        return img
    except Exception as exc:
        raise QuickEditError(f"Failed to load source image: {exc}") from exc


def _apply_crop(img: Image.Image, crop: dict) -> Image.Image:
    x = _safe_int(crop.get("x"), 0)
    y = _safe_int(crop.get("y"), 0)
    w = _safe_int(crop.get("width"), img.width)
    h = _safe_int(crop.get("height"), img.height)

    left = max(0, min(x, img.width - 1))
    top = max(0, min(y, img.height - 1))
    right = max(left + 1, min(left + max(1, w), img.width))
    bottom = max(top + 1, min(top + max(1, h), img.height))
    return img.crop((left, top, right, bottom))


def _apply_resize(img: Image.Image, resize: dict) -> Image.Image:
    width = _safe_int(resize.get("width"), img.width)
    height = _safe_int(resize.get("height"), img.height)
    width = max(1, width)
    height = max(1, height)
    return img.resize((width, height), Image.Resampling.LANCZOS)


def _apply_ops(img: Image.Image, ops: dict) -> Image.Image:
    if isinstance(ops.get("crop"), dict):
        img = _apply_crop(img, ops["crop"])

    if isinstance(ops.get("resize"), dict):
        img = _apply_resize(img, ops["resize"])

    rotate = _safe_float(ops.get("rotate"), 0.0)
    if rotate:
        img = img.rotate(-rotate, expand=True, resample=Image.Resampling.BICUBIC)

    if ops.get("flip_horizontal"):
        img = ImageOps.mirror(img)
    if ops.get("flip_vertical"):
        img = ImageOps.flip(img)

    saturation = _safe_float(ops.get("saturation"), 1.0)
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)

    brightness = _safe_float(ops.get("brightness"), 1.0)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)

    contrast = _safe_float(ops.get("contrast"), 1.0)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)

    sharpness = _safe_float(ops.get("sharpness"), 1.0)
    if sharpness != 1.0:
        img = ImageEnhance.Sharpness(img).enhance(sharpness)

    blur_radius = _safe_float(ops.get("blur_radius"), 0.0)
    if blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    return img


def _encode_output(img: Image.Image, output: dict) -> tuple[bytes, str, str]:
    fmt_raw = str(output.get("format", "jpeg")).lower()
    if fmt_raw in {"jpg", "jpeg"}:
        fmt = "JPEG"
        extension = "jpg"
        content_type = "image/jpeg"
    else:
        fmt = "PNG"
        extension = "png"
        content_type = "image/png"

    quality = max(30, min(_safe_int(output.get("quality"), 92), 100))
    out = BytesIO()
    save_kwargs: dict[str, object] = {"format": fmt}
    if fmt == "JPEG":
        if img.mode not in {"RGB", "L"}:
            img = img.convert("RGB")
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
    else:
        save_kwargs["optimize"] = True
    img.save(out, **save_kwargs)
    return out.getvalue(), extension, content_type


def run_quick_edit(task: GenerationTask) -> QuickEditResult:
    img = _load_source_image(task.input_image_url or "")
    params = task.params or {}
    ops = params.get("operations")
    if not isinstance(ops, dict):
        ops = params

    output = params.get("output")
    if not isinstance(output, dict):
        output = {}

    edited = _apply_ops(img, ops)
    data, extension, content_type = _encode_output(edited, output)

    now = datetime.now(UTC)
    object_key = f"quick_edit/{task.user_id}/{now.strftime('%Y%m%d')}/{task.id}.{extension}"
    stored = upload_binary(object_key=object_key, data=data, content_type=content_type)
    return QuickEditResult(stored=stored, width=edited.width, height=edited.height)
