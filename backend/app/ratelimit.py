"""In-memory sliding-window rate limiting.

Good enough for a single backend process. With several workers or servers, move the counters to
a shared store such as Redis.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float, name: str):
        self.limit = limit
        self.window = window_seconds
        self.name = name
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> None:
        """Record one request for `key`; raise 429 when the limit is exceeded."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, int(self.window - (now - hits[0])) + 1)
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    f"Too many {self.name} attempts. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


auth_limiter = RateLimiter(limit=10, window_seconds=60, name="sign-in")
review_limiter = RateLimiter(limit=30, window_seconds=60, name="review")
import_limiter = RateLimiter(limit=20, window_seconds=60, name="import")

ALL_LIMITERS = (auth_limiter, review_limiter, import_limiter)
