from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Asset,
    GenerationTask,
    PointsChangeType,
    StorageProvider,
    TaskProvider,
    TaskStatus,
    TaskType,
    User,
)
from app.services.image_ingest import ImageIngestError, ingest_remote_images
from app.services.moderation import ModerationError, moderate_image_url, moderate_text
from app.services.points import add_points_ledger, has_task_refund
from app.services.quick_edit import QuickEditError, run_quick_edit
from app.services.volcengine_images import VolcengineImageError, generate_images


@dataclass
class TaskExecutionResult:
    task: GenerationTask
    output_urls: list[str]
    refund_granted: bool


def _finalize_task_success(
    db: Session,
    *,
    user: User,
    task: GenerationTask,
    output_items: list[dict[str, Any]],
) -> None:
    now = datetime.now(UTC)
    task.status = TaskStatus.SUCCEEDED
    task.started_at = task.started_at or now
    task.finished_at = now
    task.error_message = None

    expire_at = now + timedelta(days=settings.image_retention_days)
    default_storage_provider = (
        StorageProvider.COS if settings.storage_provider.lower() == "cos" else StorageProvider.LOCAL
    )
    for idx, item in enumerate(output_items, start=1):
        url = item.get("file_url")
        if not url:
            continue
        object_key = item.get("object_key") or f"{task.provider.value}/{task.id}/result-{idx}.jpg"
        db.add(
            Asset(
                user_id=user.id,
                source_task_id=task.id,
                storage_provider=item.get("storage_provider") or default_storage_provider,
                object_key=object_key,
                file_url=url,
                thumbnail_url=item.get("thumbnail_url") or url,
                mime_type=item.get("mime_type"),
                width=item.get("width"),
                height=item.get("height"),
                size_bytes=item.get("size_bytes"),
                expires_at=expire_at,
            )
        )


def _finalize_task_failure(
    db: Session,
    *,
    user: User,
    task: GenerationTask,
    error_message: str,
    refund_points: bool = True,
) -> bool:
    now = datetime.now(UTC)
    task.status = TaskStatus.FAILED
    task.started_at = task.started_at or now
    task.finished_at = now
    task.error_message = error_message[:1000]

    refund_granted = False
    if refund_points and task.cost_points > 0 and not has_task_refund(db, task_id=task.id):
        add_points_ledger(
            db,
            user=user,
            task_id=task.id,
            change_type=PointsChangeType.REFUND,
            delta=task.cost_points,
            reason="task_failed_refund",
            operator="system",
        )
        refund_granted = True
    return refund_granted


def _moderate_prompt_text(task: GenerationTask) -> None:
    for text in [task.prompt, task.negative_prompt]:
        if not text:
            continue
        verdict = moderate_text(text)
        if verdict.blocked:
            raise ModerationError(f"Prompt blocked by moderation: label={verdict.label}")


def _moderate_input_images(task: GenerationTask) -> None:
    image_urls = [task.input_image_url, task.reference_image_url]
    for image_url in image_urls:
        if not image_url:
            continue
        verdict = moderate_image_url(image_url)
        if verdict.blocked:
            raise ModerationError(f"Input image blocked by moderation: label={verdict.label}")


def _moderate_output_urls(urls: list[str]) -> None:
    for url in urls:
        verdict = moderate_image_url(url)
        if verdict.blocked:
            raise ModerationError(f"Output image blocked by moderation: label={verdict.label}")


def execute_task_now(db: Session, *, task: GenerationTask, user: User) -> TaskExecutionResult:
    if task.status == TaskStatus.SUCCEEDED:
        urls = db.scalars(
            select(Asset.file_url)
            .where(Asset.source_task_id == task.id, Asset.user_id == user.id)
            .order_by(Asset.created_at.asc())
        ).all()
        return TaskExecutionResult(task=task, output_urls=urls, refund_granted=False)

    task.status = TaskStatus.RUNNING
    task.started_at = task.started_at or datetime.now(UTC)

    try:
        _moderate_prompt_text(task)
        _moderate_input_images(task)

        if task.task_type == TaskType.QUICK_EDIT:
            edited = run_quick_edit(task)
            output_items = [
                {
                    "file_url": edited.stored.file_url,
                    "thumbnail_url": edited.stored.file_url,
                    "object_key": edited.stored.object_key,
                    "storage_provider": edited.stored.storage_provider,
                    "mime_type": edited.stored.mime_type,
                    "width": edited.width,
                    "height": edited.height,
                    "size_bytes": edited.stored.size_bytes,
                }
            ]
        elif task.provider == TaskProvider.MOCK:
            output_items = [{"file_url": f"https://mock.huanto.local/mock/{task.id}/result-1.jpg"}]
        elif task.provider == TaskProvider.VOLCENGINE:
            raw_urls = generate_images(task)
            _moderate_output_urls(raw_urls)
            ingested = ingest_remote_images(task, raw_urls)
            output_items = [
                {
                    "file_url": item.stored.file_url,
                    "thumbnail_url": item.stored.file_url,
                    "object_key": item.stored.object_key,
                    "storage_provider": item.stored.storage_provider,
                    "mime_type": item.stored.mime_type,
                    "width": item.width,
                    "height": item.height,
                    "size_bytes": item.stored.size_bytes,
                }
                for item in ingested
            ]
        else:
            raise RuntimeError(f"Provider not implemented yet: {task.provider.value}")

        _finalize_task_success(db, user=user, task=task, output_items=output_items)
        db.commit()
        db.refresh(task)
        output_urls = [str(item["file_url"]) for item in output_items if item.get("file_url")]
        return TaskExecutionResult(task=task, output_urls=output_urls, refund_granted=False)
    except (VolcengineImageError, ImageIngestError, QuickEditError, ModerationError, RuntimeError) as exc:
        refund_granted = _finalize_task_failure(
            db,
            user=user,
            task=task,
            error_message=str(exc),
            refund_points=True,
        )
        db.commit()
        db.refresh(task)
        return TaskExecutionResult(task=task, output_urls=[], refund_granted=refund_granted)
    except Exception as exc:
        refund_granted = _finalize_task_failure(
            db,
            user=user,
            task=task,
            error_message=f"Execute task error: {exc}",
            refund_points=True,
        )
        db.commit()
        db.refresh(task)
        return TaskExecutionResult(task=task, output_urls=[], refund_granted=refund_granted)


def claim_next_queued_task(db: Session) -> GenerationTask | None:
    task = db.scalar(
        select(GenerationTask)
        .where(GenerationTask.status == TaskStatus.QUEUED)
        .order_by(GenerationTask.queued_at.asc().nullsfirst(), GenerationTask.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not task:
        db.rollback()
        return None

    task.status = TaskStatus.RUNNING
    task.started_at = task.started_at or datetime.now(UTC)
    db.commit()
    db.refresh(task)
    return task


def execute_task_by_id(db: Session, *, task_id: UUID) -> TaskExecutionResult | None:
    task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
    if not task:
        return None
    user = db.scalar(select(User).where(User.id == task.user_id))
    if not user:
        task.status = TaskStatus.FAILED
        task.error_message = "Task owner not found"
        task.finished_at = datetime.now(UTC)
        db.commit()
        return TaskExecutionResult(task=task, output_urls=[], refund_granted=False)
    return execute_task_now(db, task=task, user=user)


def execute_next_queued_task(db: Session) -> TaskExecutionResult | None:
    task = claim_next_queued_task(db)
    if not task:
        return None
    return execute_task_by_id(db, task_id=task.id)
