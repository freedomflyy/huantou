from __future__ import annotations

import logging
from threading import Event, Lock, Thread

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.task_executor import execute_next_queued_task

logger = logging.getLogger("huanto.worker")

_worker_lock = Lock()
_worker_thread: Thread | None = None
_stop_event = Event()


def _worker_loop() -> None:
    logger.info(
        "embedded_task_worker_started batch_size=%s poll_seconds=%s",
        max(1, settings.task_worker_batch_size),
        max(1, settings.task_worker_poll_seconds),
    )
    while not _stop_event.is_set():
        processed = 0
        with SessionLocal() as db:
            for _ in range(max(1, settings.task_worker_batch_size)):
                result = execute_next_queued_task(db)
                if not result:
                    break
                processed += 1
                logger.info(
                    "embedded_task_worker_processed task_id=%s status=%s output_count=%s",
                    result.task.id,
                    result.task.status.value,
                    len(result.output_urls),
                )
        if processed == 0:
            _stop_event.wait(max(1, settings.task_worker_poll_seconds))
    logger.info("embedded_task_worker_stopped")


def start_embedded_task_worker() -> None:
    global _worker_thread

    if not settings.task_worker_embedded_enabled:
        logger.info("embedded_task_worker_disabled")
        return

    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return
        _stop_event.clear()
        _worker_thread = Thread(
            target=_worker_loop,
            name="huanto-embedded-task-worker",
            daemon=True,
        )
        _worker_thread.start()


def stop_embedded_task_worker(timeout: float = 5.0) -> None:
    global _worker_thread

    with _worker_lock:
        thread = _worker_thread
        if not thread:
            return
        _worker_thread = None
        _stop_event.set()

    thread.join(timeout=timeout)
