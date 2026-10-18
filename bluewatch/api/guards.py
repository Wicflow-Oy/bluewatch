"""Guards for the public endpoints: per-IP and global rate limits, held in memory only.

Behind Traefik, uvicorn runs with --proxy-headers so request.client.host is the visitor's IP.
IPs are kept only as keys of counters that are dropped an hour after their last hit, and are never
logged or written to disk.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

IP_WINDOW_S = 3600
TOTAL_WINDOW_S = 60


@dataclass
class RateLimiter:
    per_ip_per_hour: int
    total_per_minute: int
    _ip_hits: dict[str, deque] = field(default_factory=dict)
    _all_hits: deque = field(default_factory=deque)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _last_sweep: float = 0.0

    def allow(self, ip: str, now: float | None = None) -> tuple[bool, str]:
        t = time.monotonic() if now is None else now
        with self._lock:
            self._sweep(t)
            while self._all_hits and t - self._all_hits[0] > TOTAL_WINDOW_S:
                self._all_hits.popleft()
            hits = self._ip_hits.get(ip, deque())  # a refused IP is not kept
            _expire(hits, t)
            if len(self._all_hits) >= self.total_per_minute:
                return False, "Busy right now: live lookups are paused for a minute. Precomputed data still works."
            if len(hits) >= self.per_ip_per_hour:
                return False, "Live lookup limit reached for this hour. Precomputed companies still work."
            hits.append(t)
            self._ip_hits[ip] = hits
            self._all_hits.append(t)
            return True, ""

    def _sweep(self, t: float) -> None:
        """Forget every IP without an allowed hit in the last hour. Runs at most once a minute, so at most
        about 61 minutes of the per-minute total are ever held, and the scan is not paid per request."""
        if t - self._last_sweep < TOTAL_WINDOW_S:
            return
        self._last_sweep = t
        for ip, hits in list(self._ip_hits.items()):
            _expire(hits, t)
            if not hits:
                del self._ip_hits[ip]


def _expire(hits: deque, t: float) -> None:
    while hits and t - hits[0] > IP_WINDOW_S:
        hits.popleft()
