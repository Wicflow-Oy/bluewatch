"""Where a shared idea goes. Only the share button (explicit consent) puts anything here. Sharing is simulated:
nothing here is ever sent to A'Pelago.

- Default: in memory, per browser session id, for 60 minutes, at most 5 ideas per session and 500
  sessions. Never written to disk or logged; only the same browser session sees it, in its own review
  queue. Sharing an edited idea again replaces the earlier share. Withdrawing consent removes it at once.
- BLUEWATCH_IDEAS_PERSIST=1 (off by default) also appends consented submissions to a JSON-lines file
  (BLUEWATCH_IDEAS_PERSIST_PATH): the switch for a private pilot with real storage. It is ignored in
  public mode (BLUEWATCH_PUBLIC=1), where nothing typed may be kept.
"""

from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bluewatch.config import settings
from bluewatch.ideas.models import IdeaAssessment, IdeaSubmission
from bluewatch.ideas.pipeline import SIMILAR, idea_words
from bluewatch.ideas.text import similarity
from bluewatch.models import ShareConsent

TTL_S = 3600
MAX_SESSIONS = 500
PER_SESSION = 5


@dataclass(frozen=True)
class SharedIdea:
    submission: IdeaSubmission
    assessment: IdeaAssessment
    consent: ShareConsent


class SharedIdeas:
    def __init__(
        self,
        *,
        ttl_s: float = TTL_S,
        cap: int = MAX_SESSIONS,
        per_session: int = PER_SESSION,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sessions: OrderedDict[str, tuple[list[SharedIdea], float]] = OrderedDict()
        self._ttl, self._cap, self._per_session, self._clock = ttl_s, cap, per_session, clock
        self._lock = threading.Lock()

    def add(self, session_id: str, idea: SharedIdea) -> None:
        """Adds an idea, replacing an earlier share of the same idea; the oldest goes when a session has
        too many."""
        now = self._clock()
        with self._lock:
            self._expire(now)
            ideas = [i for i in self._sessions.pop(session_id, ([], 0.0))[0] if not same_idea(i, idea)]
            ideas = [*ideas, idea][-self._per_session :]
            self._sessions[session_id] = (ideas, now)
            while len(self._sessions) > self._cap:
                self._sessions.popitem(last=False)

    def ideas(self, session_id: str | None) -> list[SharedIdea]:
        if not session_id:
            return []
        with self._lock:
            self._expire(self._clock())
            return list(self._sessions.get(session_id, ([], 0.0))[0])

    def seconds_left(self, session_id: str) -> float | None:
        """How long the session's shared ideas are kept, or None when it has none."""
        with self._lock:
            now = self._clock()
            self._expire(now)
            found = self._sessions.get(session_id)
            return self._ttl - (now - found[1]) if found and found[0] else None

    def forget(self, session_id: str) -> int:
        with self._lock:
            return len(self._sessions.pop(session_id, ([], 0.0))[0])

    def __len__(self) -> int:
        return sum(len(ideas) for ideas, _ in self._sessions.values())

    def _expire(self, now: float) -> None:
        while self._sessions:
            oldest, (_, touched) = next(iter(self._sessions.items()))
            if now - touched <= self._ttl:
                return
            self._sessions.pop(oldest)


def same_idea(a: SharedIdea, b: SharedIdea) -> bool:
    """An edit of the same idea: the same title, or text that reads alike (near-duplicate overlap)."""
    if a.submission.title.casefold() == b.submission.title.casefold():
        return True
    return similarity(idea_words(a.submission), idea_words(b.submission)) >= SIMILAR


def persist_path() -> Path | None:
    """The JSON-lines file for real storage, or None when it is off (the default) or in public mode."""
    s = settings()
    return s.ideas_persist_path if s.ideas_persist and not s.public_mode else None


def persist(idea: SharedIdea, path: Path) -> None:
    """One line per consented share: the consent record, the submission and the tier it got."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "consent": idea.consent.model_dump(mode="json"),
        "submission": idea.submission.model_dump(mode="json"),
        "assessment_id": idea.assessment.id,
        "tier": idea.assessment.tier,
        "rubric_version": idea.assessment.rubric_version,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")
