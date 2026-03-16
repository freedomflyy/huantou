from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    Asset,
    GenerationTask,
    ModerationAudit,
    PointsChangeType,
    TaskStatus,
    User,
    UserStatus,
)
from app.schemas.admin import (
    AdminAssetTakeDownRequest,
    AdminAssetTakeDownResponse,
    AdminOverviewResponse,
    AdminPointsAdjustRequest,
    AdminTaskRetryResponse,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserStatusUpdateRequest,
)
from app.schemas.asset import AssetItem
from app.schemas.moderation import ModerationAuditItem, ModerationAuditListResponse
from app.schemas.task import TaskResponse
from app.services.points import add_points_ledger

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverviewResponse)
def get_overview(
    _: bool = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminOverviewResponse:
    users_total = db.scalar(select(func.count(User.id))) or 0
    active_users_total = db.scalar(
        select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
    ) or 0
    disabled_users_total = db.scalar(
        select(func.count(User.id)).where(User.status == UserStatus.DISABLED)
    ) or 0

    counts_stmt = select(
        func.count(GenerationTask.id).label("total"),
        func.sum(case((GenerationTask.status == TaskStatus.QUEUED, 1), else_=0)).label("queued"),
        func.sum(case((GenerationTask.status == TaskStatus.RUNNING, 1), else_=0)).label("running"),
        func.sum(case((GenerationTask.status == TaskStatus.FAILED, 1), else_=0)).label("failed"),
        func.sum(case((GenerationTask.status == TaskStatus.SUCCEEDED, 1), else_=0)).label("succeeded"),
    )
    row = db.execute(counts_stmt).one()

    assets_total = db.scalar(select(func.count(Asset.id))) or 0
    assets_removed_total = db.scalar(
        select(func.count(Asset.id)).where(Asset.is_removed.is_(True))
    ) or 0

    return AdminOverviewResponse(
        users_total=users_total,
        active_users_total=active_users_total,
        disabled_users_total=disabled_users_total,
        tasks_total=int(row.total or 0),
        tasks_queued=int(row.queued or 0),
        tasks_running=int(row.running or 0),
        tasks_failed=int(row.failed or 0),
        tasks_succeeded=int(row.succeeded or 0),
        assets_total=assets_total,
        assets_removed_total=assets_removed_total,
    )


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    _: bool = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: UserStatus | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
) -> AdminUserListResponse:
    stmt = select(User)
    total_stmt = select(func.count(User.id))

    if status_filter:
        stmt = stmt.where(User.status == status_filter)
        total_stmt = total_stmt.where(User.status == status_filter)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where((User.nickname.ilike(like)) | (User.wx_openid.ilike(like)))
        total_stmt = total_stmt.where((User.nickname.ilike(like)) | (User.wx_openid.ilike(like)))

    rows = db.scalars(stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(total_stmt) or 0
    return AdminUserListResponse(items=[AdminUserItem.model_validate(item) for item in rows], total=total)


@router.post("/users/{user_id}/status", response_model=AdminUserItem)
def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdateRequest,
    _: bool = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserItem:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.status = payload.status
    db.commit()
    db.refresh(user)
    return AdminUserItem.model_validate(user)


@router.post("/users/{user_id}/points-adjust", response_model=AdminUserItem)
def adjust_user_points(
    user_id: int,
    payload: AdminPointsAdjustRequest,
    _: bool = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserItem:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        add_points_ledger(
            db,
            user=user,
            change_type=PointsChangeType.ADMIN_ADJUST,
            delta=payload.delta,
            reason=payload.reason,
            operator="admin",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    db.refresh(user)
    return AdminUserItem.model_validate(user)


@router.post("/tasks/{task_id}/retry", response_model=AdminTaskRetryResponse)
def admin_retry_task(
    task_id: UUID,
    _: bool = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminTaskRetryResponse:
    task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.status = TaskStatus.QUEUED
    task.retry_count += 1
    task.error_message = None
    task.queued_at = datetime.now(timezone.utc)
    task.started_at = None
    task.finished_at = None
    db.commit()
    db.refresh(task)
    return AdminTaskRetryResponse(task_id=task.id, status=task.status, retry_count=task.retry_count)


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    _: bool = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
) -> list[TaskResponse]:
    stmt = select(GenerationTask)
    if status_filter:
        stmt = stmt.where(GenerationTask.status == status_filter)
    rows = db.scalars(stmt.order_by(GenerationTask.created_at.desc()).limit(limit)).all()
    return [TaskResponse.model_validate(item) for item in rows]


@router.post("/assets/{asset_id}/take-down", response_model=AdminAssetTakeDownResponse)
def take_down_asset(
    asset_id: UUID,
    payload: AdminAssetTakeDownRequest,
    _: bool = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminAssetTakeDownResponse:
    asset = db.scalar(select(Asset).where(Asset.id == asset_id))
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    asset.is_removed = True
    asset.removed_reason = payload.reason
    db.commit()
    return AdminAssetTakeDownResponse(
        asset_id=asset.id,
        is_removed=asset.is_removed,
        removed_reason=asset.removed_reason,
    )


@router.get("/assets", response_model=list[AssetItem])
def list_assets(
    _: bool = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=200),
    user_id: int | None = Query(default=None),
    include_removed: bool = Query(default=True),
) -> list[AssetItem]:
    stmt = select(Asset)
    if user_id:
        stmt = stmt.where(Asset.user_id == user_id)
    if not include_removed:
        stmt = stmt.where(Asset.is_removed.is_(False))
    rows = db.scalars(stmt.order_by(Asset.created_at.desc()).limit(limit)).all()
    return [AssetItem.model_validate(item) for item in rows]


@router.get("/moderation-audits", response_model=ModerationAuditListResponse)
def list_moderation_audits(
    _: bool = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    blocked: bool | None = Query(default=None),
) -> ModerationAuditListResponse:
    stmt = select(ModerationAudit)
    total_stmt = select(func.count(ModerationAudit.id))
    if blocked is not None:
        stmt = stmt.where(ModerationAudit.blocked.is_(blocked))
        total_stmt = total_stmt.where(ModerationAudit.blocked.is_(blocked))

    rows = db.scalars(
        stmt.order_by(ModerationAudit.created_at.desc()).limit(limit).offset(offset)
    ).all()
    total = db.scalar(total_stmt) or 0
    return ModerationAuditListResponse(
        items=[ModerationAuditItem.model_validate(item) for item in rows],
        total=total,
    )


@router.get("/console", response_class=HTMLResponse)
def admin_console() -> HTMLResponse:
    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Huanto Admin Console</title>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif; margin: 20px; color:#1f2937; }}
    .row {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:10px; }}
    input,button,select {{ padding:8px; border:1px solid #d1d5db; border-radius:8px; }}
    button {{ background:#111827; color:#fff; cursor:pointer; }}
    pre {{ background:#0b1020; color:#d1d5db; padding:12px; border-radius:10px; overflow:auto; }}
  </style>
</head>
<body>
  <h2>Huanto Admin Console</h2>
  <div class="row">
    <input id="key" placeholder="ADMIN_API_KEY" style="min-width:320px" />
    <button onclick="loadOverview()">Load Overview</button>
    <button onclick="loadUsers()">Load Users</button>
    <button onclick="loadTasks()">Load Tasks</button>
    <button onclick="loadAssets()">Load Assets</button>
    <button onclick="loadAudits()">Load Audits</button>
  </div>
  <div class="row">
    <input id="uid" placeholder="user_id" />
    <input id="delta" placeholder="points delta, e.g. 20 / -10" />
    <button onclick="adjustPoints()">Adjust Points</button>
  </div>
  <div class="row">
    <input id="asset" placeholder="asset_id" style="min-width:320px" />
    <button onclick="takeDown()">Take Down Asset</button>
  </div>
  <pre id="out">Ready</pre>
  <script>
    const base = "{settings.api_v1_prefix}";
    function headers() {{
      return {{ "X-Admin-Key": document.getElementById("key").value, "Content-Type": "application/json" }};
    }}
    async function req(path, opts={{}}) {{
      const r = await fetch(base + path, {{ ...opts, headers: {{...headers(), ...(opts.headers||{{}})}} }});
      const t = await r.text();
      let data;
      try {{ data = JSON.parse(t); }} catch {{ data = t; }}
      document.getElementById("out").textContent = JSON.stringify({{status:r.status, data}}, null, 2);
    }}
    function loadOverview() {{ req("/admin/overview"); }}
    function loadUsers() {{ req("/admin/users?limit=20"); }}
    function loadTasks() {{ req("/admin/tasks?limit=20"); }}
    function loadAssets() {{ req("/admin/assets?limit=20"); }}
    function loadAudits() {{ req("/admin/moderation-audits?limit=20"); }}
    function adjustPoints() {{
      const uid = document.getElementById("uid").value;
      const delta = Number(document.getElementById("delta").value);
      req(`/admin/users/${{uid}}/points-adjust`, {{method:"POST", body: JSON.stringify({{delta, reason:"admin_console"}})}})
    }}
    function takeDown() {{
      const assetId = document.getElementById("asset").value;
      req(`/admin/assets/${{assetId}}/take-down`, {{method:"POST", body: JSON.stringify({{reason:"admin_console"}})}})
    }}
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)
