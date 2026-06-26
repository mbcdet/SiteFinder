from __future__ import annotations

import time


class RateLimiter:
    """Minimal monotonic-clock rate limiter enforcing a minimum interval between calls.
    Used to respect Overpass/Nominatim fair-use (~1 req/s)."""

    def __init__(self, min_interval: float) -> None:
        self._min_interval = max(0.0, min_interval)
        self._last: float | None = None

    def wait(self) -> None:
        if self._min_interval == 0:
            return
        now = time.monotonic()
        if self._last is not None:
            elapsed = now - self._last
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
        self._last = time.monotonic()
