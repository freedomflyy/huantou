#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from huggingface_hub import HfApi

from download_models import CATALOG, GROUPS, ModelSpec


@dataclass(frozen=True)
class RepoFile:
    path: str
    size: int


@dataclass(frozen=True)
class ModelReport:
    key: str
    repo_id: str
    description: str
    target_dir: Path
    remote_total_bytes: int
    local_disk_bytes: int
    downloaded_bytes: int
    remaining_bytes: int
    total_files: int
    present_files: int
    missing_files: int
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report required disk space for local AI models without downloading them."
    )
    parser.add_argument(
        "--group",
        action="append",
        choices=sorted(GROUPS.keys()),
        help="Model group(s) to report. Default: recommended.",
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
    return parser.parse_args()


def resolve_selection(args: argparse.Namespace) -> list[ModelSpec]:
    selected: list[str] = []
    groups = args.group or ["recommended"]
    for group in groups:
        selected.extend(GROUPS[group])
    if args.model:
        selected.extend(args.model)
    ordered_keys = list(dict.fromkeys(selected))
    return [CATALOG[key] for key in ordered_keys]


def match_allowed(path: str, allow_patterns: tuple[str, ...] | None) -> bool:
    if not allow_patterns:
        return True
    return any(fnmatch.fnmatch(path, pattern) for pattern in allow_patterns)


def iter_local_files(target_dir: Path) -> Iterable[Path]:
    if not target_dir.exists():
        return []
    files: list[Path] = []
    for path in target_dir.rglob("*"):
        if not path.is_file():
            continue
        if any(part.startswith(".cache") for part in path.parts):
            continue
        files.append(path)
    return files


def get_repo_files(api: HfApi, spec: ModelSpec, token: str | None) -> list[RepoFile]:
    info = api.model_info(spec.repo_id, files_metadata=True, token=token)
    repo_files: list[RepoFile] = []
    for sibling in info.siblings or []:
        path = getattr(sibling, "rfilename", None)
        if not path or not match_allowed(path, spec.allow_patterns):
            continue
        size = getattr(sibling, "size", None)
        if size is None:
            lfs = getattr(sibling, "lfs", None)
            size = getattr(lfs, "size", 0) if lfs is not None else 0
        repo_files.append(RepoFile(path=path, size=int(size or 0)))
    return repo_files


def get_local_disk_bytes(target_dir: Path) -> int:
    if not target_dir.exists():
        return 0
    total = 0
    for path in target_dir.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total


def build_report(api: HfApi, spec: ModelSpec, root_dir: Path, token: str | None) -> ModelReport:
    target_dir = root_dir / spec.target_subdir
    repo_files = get_repo_files(api, spec, token)

    remote_total_bytes = 0
    downloaded_bytes = 0
    present_files = 0

    for repo_file in repo_files:
        remote_total_bytes += repo_file.size
        local_path = target_dir / repo_file.path
        if local_path.exists() and local_path.is_file():
            present_files += 1
            local_size = local_path.stat().st_size
            downloaded_bytes += min(local_size, repo_file.size)

    remaining_bytes = max(remote_total_bytes - downloaded_bytes, 0)
    missing_files = max(len(repo_files) - present_files, 0)
    local_disk_bytes = get_local_disk_bytes(target_dir)

    if remote_total_bytes == 0 and local_disk_bytes == 0:
        status = "empty"
    elif remaining_bytes == 0 and len(repo_files) > 0:
        status = "complete"
    elif downloaded_bytes > 0 or local_disk_bytes > 0:
        status = "partial"
    else:
        status = "missing"

    return ModelReport(
        key=spec.key,
        repo_id=spec.repo_id,
        description=spec.description,
        target_dir=target_dir,
        remote_total_bytes=remote_total_bytes,
        local_disk_bytes=local_disk_bytes,
        downloaded_bytes=downloaded_bytes,
        remaining_bytes=remaining_bytes,
        total_files=len(repo_files),
        present_files=present_files,
        missing_files=missing_files,
        status=status,
    )


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def main() -> int:
    args = parse_args()
    specs = resolve_selection(args)
    root_dir = Path(args.root_dir).resolve()
    token = args.hf_token.strip() or None
    api = HfApi()

    reports = [build_report(api, spec, root_dir, token) for spec in specs]

    total_remote = sum(item.remote_total_bytes for item in reports)
    total_local_disk = sum(item.local_disk_bytes for item in reports)
    total_downloaded = sum(item.downloaded_bytes for item in reports)
    total_remaining = sum(item.remaining_bytes for item in reports)

    print("Model storage report")
    print(f"Root dir: {root_dir}")
    print(f"Selected models: {', '.join(item.key for item in reports)}")
    print()
    print(
        "TOTAL  "
        f"required={format_bytes(total_remote)}  "
        f"downloaded={format_bytes(total_downloaded)}  "
        f"local_disk={format_bytes(total_local_disk)}  "
        f"remaining={format_bytes(total_remaining)}"
    )
    print()

    for item in reports:
        print(f"[{item.status}] {item.key}")
        print(f"  repo: {item.repo_id}")
        print(f"  desc: {item.description}")
        print(f"  dir: {item.target_dir}")
        print(
            "  size: "
            f"required={format_bytes(item.remote_total_bytes)}  "
            f"downloaded={format_bytes(item.downloaded_bytes)}  "
            f"local_disk={format_bytes(item.local_disk_bytes)}  "
            f"remaining={format_bytes(item.remaining_bytes)}"
        )
        print(
            "  files: "
            f"present={item.present_files}/{item.total_files}  "
            f"missing={item.missing_files}"
        )
        print()

    pending = [item.key for item in reports if item.status != "complete"]
    if pending:
        print("Still needed:")
        for key in pending:
            print(f"- {key}")
    else:
        print("All selected models are fully present.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
