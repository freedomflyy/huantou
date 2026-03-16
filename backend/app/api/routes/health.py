from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.observability import request_metrics
from app.core.rate_limit import rate_limiter
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics")
def health_metrics(_: bool = Depends(require_admin)) -> dict[str, object]:
    metrics = request_metrics.snapshot()
    return {
        "requests": {
            "total_requests": metrics.total_requests,
            "total_errors": metrics.total_errors,
            "total_rate_limited": metrics.total_rate_limited,
            "status_counts": metrics.status_counts,
            "avg_elapsed_ms": metrics.avg_elapsed_ms,
            "p50_elapsed_ms": metrics.p50_elapsed_ms,
            "p95_elapsed_ms": metrics.p95_elapsed_ms,
            "last_request_at": metrics.last_request_at,
        },
        "rate_limiter": rate_limiter.snapshot(),
    }
