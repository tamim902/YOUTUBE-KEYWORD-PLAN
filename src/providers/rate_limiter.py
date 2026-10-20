"""Rate limiter for outbound HTTP requests."""

import threading
import time
from typing import Optional


class RateLimiter:
    """Thread-safe rate limiter enforcing a minimum interval between requests."""

    def __init__(self, min_interval_seconds: float = 0.2) -> None:
        self.min_interval = max(0.0, float(min_interval_seconds))
        self._last_request_time: float = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until the minimum request interval has elapsed."""
        if self.min_interval <= 0:
            return

        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request_time = time.monotonic()
