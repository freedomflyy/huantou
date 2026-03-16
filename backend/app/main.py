import logging
import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import settings
from app.core.observability import log_event, request_metrics, setup_logging, setup_sentry
from app.core.rate_limit import rate_limiter
from app.services.embedded_task_worker import start_embedded_task_worker, stop_embedded_task_worker
from app.services.security import validate_runtime_security

app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix=settings.api_v1_prefix)
logger = logging.getLogger("huanto.api")


@app.on_event("startup")
def _on_startup() -> None:
    setup_logging()
    setup_sentry()
    validate_runtime_security()
    start_embedded_task_worker()
    log_event(logger, "startup", app_name=settings.app_name, app_env=settings.app_env)


@app.on_event("shutdown")
def _on_shutdown() -> None:
    stop_embedded_task_worker()


def _resolve_client_id(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _resolve_rate_limit_policy(request: Request) -> tuple[str, int]:
    path = request.url.path
    if path.startswith(f"{settings.api_v1_prefix}/health"):
        return ("health", 0)
    if path.startswith(f"{settings.api_v1_prefix}/auth/"):
        return ("auth", settings.rate_limit_auth_per_minute)
    if (
        request.method.upper() == "POST"
        and path.startswith(f"{settings.api_v1_prefix}/tasks/")
        and path.endswith("/execute")
    ):
        return ("task_execute", settings.rate_limit_task_execute_per_minute)
    return ("global", settings.rate_limit_global_per_minute)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid4())
    start = time.perf_counter()
    request.state.request_id = request_id
    if settings.rate_limit_enabled:
        policy_name, limit = _resolve_rate_limit_policy(request)
        if limit > 0:
            client_id = _resolve_client_id(request)
            key = f"{policy_name}:{request.method}:{client_id}"
            result = rate_limiter.check(key=key, limit=limit)
            if not result.allowed:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                response = JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many requests",
                        "request_id": request_id,
                        "retry_after_seconds": result.retry_after_seconds,
                    },
                )
                response.headers["X-Request-Id"] = request_id
                response.headers["X-RateLimit-Limit"] = str(result.limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["Retry-After"] = str(result.retry_after_seconds)
                log_event(
                    logger,
                    "request_rate_limited",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    policy=policy_name,
                    client_id=client_id,
                    limit=result.limit,
                    retry_after=result.retry_after_seconds,
                    elapsed_ms=elapsed_ms,
                )
                request_metrics.record(status_code=429, elapsed_ms=elapsed_ms, rate_limited=True)
                return response

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        log_event(
            logger,
            "request_error",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            elapsed_ms=elapsed_ms,
        )
        request_metrics.record(status_code=500, elapsed_ms=elapsed_ms)
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-Id"] = request_id
    request_metrics.record(status_code=response.status_code, elapsed_ms=elapsed_ms)
    log_event(
        logger,
        "request_complete",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    logger.exception("unhandled_exception request_id=%s", request_id)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Huanto API is running"}
