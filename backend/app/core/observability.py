from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    if settings.log_json:
        logger.info(json.dumps(payload, ensure_ascii=False, default=str))
    else:
        logger.info("%s | %s", event, payload)


def setup_sentry() -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except ImportError:
        logging.getLogger("huanto.api").warning(
            "SENTRY_DSN is set but sentry-sdk is not installed; error tracking disabled"
        )
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=max(0.0, min(settings.sentry_traces_sample_rate, 1.0)),
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        send_default_pii=False,
    )
    logging.getLogger("huanto.api").info("Sentry initialized")


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return round(sorted_values[0], 2)
    index = max(0, min(len(sorted_values) - 1, int(round((len(sorted_values) - 1) * p))))
    return round(sorted_values[index], 2)


@dataclass
class RequestMetricsSnapshot:
    total_requests: int
    total_errors: int
    total_rate_limited: int
    status_counts: dict[str, int]
    avg_elapsed_ms: float
    p50_elapsed_ms: float
    p95_elapsed_ms: float
    last_request_at: str | None


class RequestMetrics:
    def __init__(self, latency_sample_size: int = 500) -> None:
        self._lock = threading.Lock()
        self._latency_sample_size = latency_sample_size
        self._latencies_ms: list[float] = []
        self._total_requests = 0
        self._total_errors = 0
        self._total_rate_limited = 0
        self._sum_elapsed_ms = 0.0
        self._status_counts: dict[str, int] = {}
        self._last_request_at: datetime | None = None

    def record(self, *, status_code: int, elapsed_ms: float, rate_limited: bool = False) -> None:
        bucket = f"{status_code // 100}xx"
        now = datetime.now(timezone.utc)
        with self._lock:
            self._total_requests += 1
            self._sum_elapsed_ms += elapsed_ms
            if status_code >= 500:
                self._total_errors += 1
            if rate_limited:
                self._total_rate_limited += 1
            self._status_counts[bucket] = self._status_counts.get(bucket, 0) + 1
            self._latencies_ms.append(elapsed_ms)
            if len(self._latencies_ms) > self._latency_sample_size:
                self._latencies_ms = self._latencies_ms[-self._latency_sample_size :]
            self._last_request_at = now

    def snapshot(self) -> RequestMetricsSnapshot:
        with self._lock:
            latencies = sorted(self._latencies_ms)
            avg = round(self._sum_elapsed_ms / self._total_requests, 2) if self._total_requests else 0.0
            return RequestMetricsSnapshot(
                total_requests=self._total_requests,
                total_errors=self._total_errors,
                total_rate_limited=self._total_rate_limited,
                status_counts=dict(self._status_counts),
                avg_elapsed_ms=avg,
                p50_elapsed_ms=_percentile(latencies, 0.5),
                p95_elapsed_ms=_percentile(latencies, 0.95),
                last_request_at=self._last_request_at.isoformat() if self._last_request_at else None,
            )


request_metrics = RequestMetrics()
