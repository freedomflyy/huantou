from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.task_executor import execute_next_queued_task


def run_once(batch_size: int) -> int:
    processed = 0
    with SessionLocal() as db:
        for _ in range(batch_size):
            result = execute_next_queued_task(db)
            if not result:
                break
            processed += 1
            print(
                json.dumps(
                    {
                        "task_id": str(result.task.id),
                        "status": result.task.status.value,
                        "refund_granted": result.refund_granted,
                        "output_count": len(result.output_urls),
                    },
                    ensure_ascii=False,
                )
            )
    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Huanto queued task worker")
    parser.add_argument("--once", action="store_true", help="Process one batch and exit")
    parser.add_argument("--batch-size", type=int, default=settings.task_worker_batch_size)
    parser.add_argument("--poll-seconds", type=int, default=settings.task_worker_poll_seconds)
    args = parser.parse_args()

    if args.once:
        processed = run_once(max(1, args.batch_size))
        print(json.dumps({"mode": "once", "processed": processed}, ensure_ascii=False))
        return

    print(
        json.dumps(
            {
                "mode": "loop",
                "batch_size": max(1, args.batch_size),
                "poll_seconds": max(1, args.poll_seconds),
            },
            ensure_ascii=False,
        )
    )

    while True:
        processed = run_once(max(1, args.batch_size))
        if processed == 0:
            time.sleep(max(1, args.poll_seconds))


if __name__ == "__main__":
    main()
