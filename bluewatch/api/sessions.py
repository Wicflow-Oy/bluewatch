"""Per-visitor outreach desks for the public demo: in memory only, gone after an hour, with a hard cap.

Each visitor's browser sends a random session id it made itself, so two visitors never see each other's
drafts. A desk here is a SQLite database in memory with public-mode settings: its send step never calls
a sender, so no e-mail can leave from the public app whatever the environment says.
"""

from __future__ import annotations

import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import replace

from bluewatch.config import settings
from bluewatch.outreach.desk import Desk
from bluewatch.outreach.senders import OutboundMessage, SendRefused
from bluewatch.store import Store

SESSION_TTL_S = 3600
MAX_SESSIONS = 500
SESSION_ID = re.compile(r"[A-Za-z0-9-]{16,64}")


class NeverSends:
    """The sender of every demo desk. Public mode already stops before a sender; this is the second lock."""

    def send(self, message: OutboundMessage):
        raise SendRefused("The demo desk never sends e-mail.")


def demo_desk() -> Desk:
    return Desk(Store(":memory:"), sender=NeverSends(), settings=replace(settings(), public_mode=True))


class DeskSessions:
    def __init__(
        self, *, ttl_s: float = SESSION_TTL_S, cap: int = MAX_SESSIONS, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._desks: OrderedDict[str, tuple[Desk, float]] = OrderedDict()
        self._ttl, self._cap, self._clock = ttl_s, cap, clock
        self._lock = threading.Lock()

    def desk(self, session_id: str) -> Desk:
        if not SESSION_ID.fullmatch(session_id):
            raise ValueError("The demo session id must be 16 to 64 letters, digits or dashes.")
        now = self._clock()
        with self._lock:
            self._expire(now)
            desk = self._desks.pop(session_id, (None, 0.0))[0] or demo_desk()
            self._desks[session_id] = (desk, now)  # most recently used last
            while len(self._desks) > self._cap:
                self._desks.popitem(last=False)
            return desk

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._desks.pop(session_id, None)

    def __len__(self) -> int:
        return len(self._desks)

    def _expire(self, now: float) -> None:
        while self._desks:
            oldest_id, (_, used) = next(iter(self._desks.items()))
            if now - used <= self._ttl:
                return
            self._desks.pop(oldest_id)
