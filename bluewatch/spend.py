"""Daily spend cap for model calls (the public app's $40/day guard).

BudgetedModelClient wraps any ModelClient. Before a call it reserves the worst case (the prompt plus
max_tokens of output) under today's cap, in one step under the ledger's lock, so calls running side
by side cannot all pass the check; after the call it settles the reservation to the real cost from
the token counts. When the cap is reached it returns refused=True with stop_reason="budget", and
callers fall back to precomputed or keyword results. The Anthropic Console workspace limit is the
second, independent guard.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from bluewatch.config import CACHE_DIR, settings
from bluewatch.llm import ModelClient, ModelRequest, ModelResponse

# USD per million tokens (input, output), read 17 Oct 2026; override with BLUEWATCH_PRICE_<KEY>.
PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}
UNKNOWN_MODEL_PRICE = (4.00, 20.00)  # charge unknown models at the most expensive rate


def price(model: str) -> tuple[float, float]:
    env = os.environ.get(f"BLUEWATCH_PRICE_{model.upper().replace('-', '_')}")
    if env and "," in env:
        a, b = env.split(",", 1)
        return float(a), float(b)
    return PRICES.get(model, UNKNOWN_MODEL_PRICE)


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = price(model)
    return (input_tokens * pin + output_tokens * pout) / 1_000_000


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)  # conservative: about 3 characters per token


@dataclass
class SpendLedger:
    """Spend in USD per UTC day. Persists numbers only (never prompts or responses)."""

    path: Path | None = None
    _by_day: dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if self.path and self.path.exists():
            try:
                self._by_day = {k: float(v) for k, v in json.loads(self.path.read_text(encoding="utf-8")).items()}
            except (ValueError, OSError):
                self._by_day = {}

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def spent_today(self) -> float:
        return self._by_day.get(self._today(), 0.0)

    def add(self, usd: float, day: str | None = None) -> None:
        """Book usd (negative to give some back) on day, an ISO date, or today."""
        with self._lock:
            self._book(day or self._today(), usd)

    def reserve(self, usd: float, cap_usd: float) -> str | None:
        """Book usd on today only if it keeps today under cap_usd. Returns the day booked, or None."""
        with self._lock:
            day = self._today()
            if self._by_day.get(day, 0.0) + usd > cap_usd:
                return None
            self._book(day, usd)
            return day

    def _book(self, day: str, usd: float) -> None:
        self._by_day[day] = self._by_day.get(day, 0.0) + usd
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._by_day), encoding="utf-8")
            tmp.replace(self.path)  # a crash mid-write never leaves a broken ledger behind
        except OSError:
            pass  # no writable state directory: the in-memory total still applies


@dataclass
class BudgetedModelClient:
    inner: ModelClient
    cap_usd: float
    ledger: SpendLedger = field(default_factory=SpendLedger)
    name: str = "budgeted"

    def complete(self, request: ModelRequest) -> ModelResponse:
        worst = cost_usd(request.model, estimate_tokens(request.system + request.prompt), request.max_tokens)
        day = self.ledger.reserve(worst, self.cap_usd)
        if day is None:
            return ModelResponse(text="", model=request.model, stop_reason="budget", refused=True)
        # If the call raises, the worst case stays booked: the request may still have been billed.
        response = self.inner.complete(request)
        in_tok = response.input_tokens or estimate_tokens(request.system + request.prompt)
        out_tok = response.output_tokens or request.max_tokens
        self.ledger.add(cost_usd(request.model, in_tok, out_tok) - worst, day)
        return response


@lru_cache(maxsize=1)
def ledger() -> SpendLedger:
    """The one ledger for every model call in this process (Idea Harbour now, the live card reader next),
    so the daily cap counts them together. Kept in CACHE_DIR/spend.json; the deployed container points
    BLUEWATCH_CACHE_DIR at a small volume so a restart does not reset the day to $0."""
    return SpendLedger(path=CACHE_DIR / "spend.json")


def capped(inner: ModelClient) -> BudgetedModelClient:
    """inner behind today's cap (BLUEWATCH_DAILY_SPEND_CAP_USD), booked in the shared ledger."""
    return BudgetedModelClient(inner, cap_usd=settings().daily_spend_cap_usd, ledger=ledger())
