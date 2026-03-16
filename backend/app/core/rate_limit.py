from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class InMemorySlidingWindowRateLimiter:
    def __init__(self, window_seconds: int = 60, max_keys: int = 50000) -> None:
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = {}
        self._allowed_total = 0
        self._blocked_total = 0

    def check(self, key: str, limit: int) -> RateLimitResult:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = deque()
                self._buckets[key] = bucket

            self._trim_bucket(bucket, now)
            current = len(bucket)
            if current >= limit:
                self._blocked_total += 1
                retry_after = self.window_seconds
                if bucket:
                    retry_after = max(1, int(self.window_seconds - (now - bucket[0])) + 1)
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            bucket.append(now)
            self._allowed_total += 1
            remaining = max(0, limit - len(bucket))
            self._evict_if_needed()
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=remaining,
                retry_after_seconds=0,
            )

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "window_seconds": self.window_seconds,
                "active_keys": len(self._buckets),
                "allowed_total": self._allowed_total,
                "blocked_total": self._blocked_total,
            }

    def _trim_bucket(self, bucket: deque[float], now: float) -> None:
        while bucket and now - bucket[0] >= self.window_seconds:
            bucket.popleft()

    def _evict_if_needed(self) -> None:
        if len(self._buckets) <= self.max_keys:
            return
        to_remove: list[str] = []
        now = time.monotonic()
        for bucket_key, bucket in self._buckets.items():
            self._trim_bucket(bucket, now)
            if not bucket:
                to_remove.append(bucket_key)
            if len(self._buckets) - len(to_remove) <= self.max_keys:
                break
        for bucket_key in to_remove:
            self._buckets.pop(bucket_key, None)


rate_limiter = InMemorySlidingWindowRateLimiter()
