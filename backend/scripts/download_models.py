#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelSpec:
    key: str
    repo_id: str
    target_subdir: str
    description: str
    allow_patterns: tuple[str, ...] | None = None


CATALOG: dict[str, ModelSpec] = {
    "sdxl_base": ModelSpec(
        key="sdxl_base",
        repo_id="stabilityai/stable-diffusion-xl-base-1.0",
        target_subdir="base/sdxl-base-1.0",
        description="文生图/图生图基础模型",
    ),
    "sdxl_refiner": ModelSpec(
        key="sdxl_refiner",
        repo_id="stabilityai/stable-diffusion-xl-refiner-1.0",
        target_subdir="base/sdxl-refiner-1.0",
        description="可选精修模型（质量提升，速度更慢）",
    ),
    "sdxl_inpaint": ModelSpec(
        key="sdxl_inpaint",
        repo_id="diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        target_subdir="inpaint/sdxl-inpainting-0.1",
        description="局部重绘 Inpainting",
    ),
    "controlnet_canny_sdxl": ModelSpec(
        key="controlnet_canny_sdxl",
        repo_id="diffusers/controlnet-canny-sdxl-1.0",
        target_subdir="controlnet/canny-sdxl-1.0",
        description="ControlNet 边缘约束（结构保持）",
    ),
    "controlnet_depth_sdxl": ModelSpec(
        key="controlnet_depth_sdxl",
        repo_id="diffusers/controlnet-depth-sdxl-1.0",
        target_subdir="controlnet/depth-sdxl-1.0",
        description="ControlNet 深度约束（结构保持）",
    ),
    "ip_adapter_sdxl": ModelSpec(
        key="ip_adapter_sdxl",
        repo_id="h94/IP-Adapter",
        target_subdir="ip_adapter/h94-ip-adapter",
        description="参考图风格迁移（SDXL）",
        allow_patterns=(
            "README.md",
            "LICENSE",
            "models/image_encoder/*",
            "sdxl_models/*",
        ),
    ),
}

GROUPS: dict[str, tuple[str, ...]] = {
    "recommended": (
        "sdxl_base",
        "controlnet_canny_sdxl",
        "controlnet_depth_sdxl",
        "ip_adapter_sdxl",
        "sdxl_inpaint",
    ),
    "text2avatar": ("sdxl_base",),
    "img2img": ("sdxl_base", "controlnet_canny_sdxl", "controlnet_depth_sdxl"),
    "reference_style": ("sdxl_base", "ip_adapter_sdxl"),
    "inpainting": ("sdxl_inpaint",),
    "all": tuple(CATALOG.keys()),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download SDXL/ControlNet/IP-Adapter models into backend/models."
    )
    parser.add_argument(
        "--group",
        action="append",
        choices=sorted(GROUPS.keys()),
        help="Model group(s) to download. Default: recommended.",
    )
    parser.add_argument(
        "--model",
        action="append",
        choices=sorted(CATALOG.keys()),
        help="Additional single model key(s) to include.",
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).resolve().parent.parent / "models"),
        help="Root model directory (default: backend/models).",
    )
    parser.add_argument(
        "--hf-token",
        default=os.getenv("HF_TOKEN", ""),
        help="Hugging Face token. If omitted, uses HF_TOKEN env.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download existing files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan only without downloading.",
    )
    return parser.parse_args()


def resolve_selection(args: argparse.Namespace) -> list[ModelSpec]:
    selected: list[str] = []
    groups = args.group or ["recommended"]
    for group in groups:
        selected.extend(GROUPS[group])
    if args.model:
        selected.extend(args.model)

    # preserve order while de-duplicating
    ordered_keys = list(dict.fromkeys(selected))
    return [CATALOG[key] for key in ordered_keys]


def main() -> int:
    args = parse_args()
    models = resolve_selection(args)
    root_dir = Path(args.root_dir).resolve()
    root_dir.mkdir(parents=True, exist_ok=True)

    print("Model download plan:")
    for spec in models:
        print(f"- {spec.key}: {spec.repo_id} -> {root_dir / spec.target_subdir}")
    if args.dry_run:
        print("Dry-run enabled, skip download.")
        return 0

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Missing dependency: huggingface_hub")
        print("Run: pip install huggingface_hub")
        return 1

    token = args.hf_token.strip() or None

    for spec in models:
        target_dir = root_dir / spec.target_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nDownloading {spec.key} ({spec.description})...")
        snapshot_download(
            repo_id=spec.repo_id,
            local_dir=str(target_dir),
            token=token,
            allow_patterns=list(spec.allow_patterns) if spec.allow_patterns else None,
            force_download=args.force,
            max_workers=8,
        )
        print(f"Done: {target_dir}")

    print("\nAll requested models are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
