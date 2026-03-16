from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    Asset,
    GenerationTask,
    PointsChangeType,
    StorageProvider,
    TaskProvider,
    TaskStatus,
    User,
)
from app.schemas.task import (
    MockTaskCompleteRequest,
    MockTaskFailRequest,
    MockTaskFailResponse,
    TaskCreateRequest,
    TaskExecuteResponse,
    TaskListResponse,
    TaskResponse,
)
from app.services.moderation import ModerationError, moderate_text
from app.services.points import add_points_ledger, get_task_cost, has_task_refund
from app.services.task_executor import execute_task_now

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_my_task(db: Session, user_id: int, task_id: UUID) -> GenerationTask:
    task = db.scalar(
        select(GenerationTask).where(
            GenerationTask.id == task_id,
            GenerationTask.user_id == user_id,
        )
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


def _resolve_task_provider(task_provider: TaskProvider | None) -> TaskProvider:
    if task_provider is not None:
        return task_provider
    try:
        return TaskProvider(settings.ai_provider_default.lower())
    except ValueError:
        return TaskProvider.MOCK


def _finalize_task_failure(
    db: Session,
    *,
    user: User,
    task: GenerationTask,
    error_message: str,
    refund_points: bool = True,
) -> bool:
    now = datetime.now(timezone.utc)
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


@router.post("", response_model=TaskResponse)
def create_task(
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    cost = get_task_cost(payload.task_type)
    if cost > user.points_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient points",
        )
    try:
        for text in [payload.prompt, payload.negative_prompt]:
            if not text:
                continue
            verdict = moderate_text(text)
            if verdict.blocked:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Prompt blocked by moderation: label={verdict.label}",
                )
    except ModerationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)
    initial_status = TaskStatus.QUEUED
    task = GenerationTask(
        user_id=user.id,
        task_type=payload.task_type,
        provider=_resolve_task_provider(payload.provider),
        status=initial_status,
        prompt=payload.prompt,
        negative_prompt=payload.negative_prompt,
        input_image_url=payload.input_image_url,
        reference_image_url=payload.reference_image_url,
        params=payload.params,
        cost_points=cost,
        queued_at=now,
    )
    db.add(task)
    db.flush()

    if cost > 0:
        add_points_ledger(
            db,
            user=user,
            task_id=task.id,
            change_type=PointsChangeType.GENERATION_COST,
            delta=-cost,
            reason=f"{payload.task_type.value}_create",
            operator="system",
        )

    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TaskListResponse:
    stmt = (
        select(GenerationTask)
        .where(GenerationTask.user_id == user.id)
        .order_by(GenerationTask.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    total_stmt = select(func.count(GenerationTask.id)).where(GenerationTask.user_id == user.id)

    rows = db.scalars(stmt).all()
    total = db.scalar(total_stmt) or 0
    return TaskListResponse(
        items=[TaskResponse.model_validate(item) for item in rows],
        total=total,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = _get_my_task(db, user.id, task_id)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/retry", response_model=TaskResponse)
def retry_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = _get_my_task(db, user.id, task_id)
    if task.status not in {TaskStatus.FAILED, TaskStatus.CANCELED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed/canceled tasks can be retried",
        )

    task.status = TaskStatus.QUEUED
    task.retry_count += 1
    task.error_message = None
    task.queued_at = datetime.now(timezone.utc)
    task.started_at = None
    task.finished_at = None
    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/execute", response_model=TaskExecuteResponse)
def execute_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskExecuteResponse:
    task = _get_my_task(db, user.id, task_id)
    result = execute_task_now(db, task=task, user=user)
    return TaskExecuteResponse(
        task=TaskResponse.model_validate(result.task),
        output_urls=result.output_urls,
        refund_granted=result.refund_granted,
    )


@router.post("/{task_id}/mock-complete", response_model=TaskResponse)
def mock_complete_task(
    task_id: UUID,
    payload: MockTaskCompleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = _get_my_task(db, user.id, task_id)
    if task.provider != TaskProvider.MOCK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only mock provider can use mock-complete",
        )
    if task.status == TaskStatus.SUCCEEDED:
        return TaskResponse.model_validate(task)

    default_key = f"mock/{task.id}/result-1.jpg"
    file_url = payload.file_url or f"https://mock.huanto.local/{default_key}"
    db.add(
        Asset(
            user_id=user.id,
            source_task_id=task.id,
            storage_provider=StorageProvider.LOCAL,
            object_key=default_key,
            file_url=file_url,
            thumbnail_url=payload.thumbnail_url or file_url,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.image_retention_days),
        )
    )
    task.status = TaskStatus.SUCCEEDED
    task.finished_at = datetime.now(timezone.utc)
    task.error_message = None

    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/mock-fail", response_model=MockTaskFailResponse)
def mock_fail_task(
    task_id: UUID,
    payload: MockTaskFailRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MockTaskFailResponse:
    task = _get_my_task(db, user.id, task_id)
    if task.provider != TaskProvider.MOCK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only mock provider can use mock-fail",
        )

    refund_granted = _finalize_task_failure(
        db,
        user=user,
        task=task,
        error_message=payload.error_message,
        refund_points=payload.refund_points,
    )

    db.commit()
    db.refresh(task)
    return MockTaskFailResponse(task=TaskResponse.model_validate(task), refund_granted=refund_granted)
