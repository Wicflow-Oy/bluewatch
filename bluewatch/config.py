"""Settings from environment variables only.

For local development, put keys in `.env.local` at the repo root (gitignored); it is loaded into
the environment at import without overriding variables that are already set. On the server, the
compose file passes `.env`; `.env.example` lists the variables. Keys are never read from other
projects, logged or sent to the browser.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED_DIR = DATA_DIR / "seed"
FIXTURES_DIR = DATA_DIR / "fixtures"
CACHE_DIR = Path(os.environ.get("BLUEWATCH_CACHE_DIR") or str(DATA_DIR / "cache"))
OUTBOX_DIR = Path(os.environ.get("BLUEWATCH_OUTBOX_DIR") or str(DATA_DIR / "outbox"))
FRONTEND_DIST = Path(os.environ.get("BLUEWATCH_FRONTEND_DIST") or str(ROOT / "frontend" / "dist"))

# Generic User-Agent: never put a person's name, e-mail or company in requests.
USER_AGENT = "BlueWatch/0.1 (+https://bluewatch.demo.wicflow.com)"
HTTP_TIMEOUT_S = 25.0
# The partners' time zone: "today", deadlines and the weekly digest follow the Finnish calendar.
HELSINKI = ZoneInfo("Europe/Helsinki")


def load_env_local(path: Path = ROOT / ".env.local") -> None:
    """Load KEY=VALUE lines from .env.local into os.environ (existing variables win)."""
    if os.environ.get("BLUEWATCH_SKIP_ENV_LOCAL") == "1" or not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_local()


def _env(name: str, default: str = "") -> str:
    """An env var, treating an empty value (as left by .env.example) as unset."""
    value = os.environ.get(name, "").strip()
    return value or default


def _split(value: str | None) -> list[str]:
    return [v.strip().lower() for v in (value or "").split(",") if v.strip()]


def _flag(name: str, default: str) -> bool:
    return _env(name, default) == "1"


def _today() -> date:
    value = _env("BLUEWATCH_TODAY")
    return date.fromisoformat(value) if value else datetime.now(HELSINKI).date()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = field(default_factory=lambda: _env("ANTHROPIC_API_KEY") or None)
    classifier_model: str = field(default_factory=lambda: _env("BLUEWATCH_CLASSIFIER_MODEL", "claude-haiku-5-5"))
    writer_model: str = field(default_factory=lambda: _env("BLUEWATCH_WRITER_MODEL", "claude-sonnet-5-5"))
    # The deployed public app: no e-mail is ever sent, visitor input is never stored or logged.
    public_mode: bool = field(default_factory=lambda: _flag("BLUEWATCH_PUBLIC", "0"))
    # Outreach stays in demo mode: in private demos it sends only to this allowlist (our own inboxes);
    # in public mode it never sends at all.
    outreach_mode: str = field(default_factory=lambda: _env("OUTREACH_MODE", "demo"))
    outreach_allowlist: tuple[str, ...] = field(default_factory=lambda: tuple(_split(_env("OUTREACH_ALLOWLIST"))))
    smtp_host: str | None = field(default_factory=lambda: _env("SMTP_HOST") or None)
    smtp_port: int = field(default_factory=lambda: int(_env("SMTP_PORT", "587")))
    smtp_user: str | None = field(default_factory=lambda: _env("SMTP_USER") or None)
    smtp_password: str | None = field(default_factory=lambda: _env("SMTP_PASSWORD") or None)
    smtp_from: str | None = field(default_factory=lambda: _env("SMTP_FROM") or None)
    # Network: the precomputed demo and all tests run offline from recorded data.
    offline: bool = field(default_factory=lambda: _flag("BLUEWATCH_OFFLINE", "1"))
    # The live company lookup and founder view may call the public registers even when offline=1.
    live_lookups: bool = field(default_factory=lambda: _flag("BLUEWATCH_LIVE_LOOKUPS", "0"))
    # Generous per IP because a venue shares one IP; the total per minute and the spend cap bound the load.
    lookups_per_ip_per_hour: int = field(default_factory=lambda: int(_env("BLUEWATCH_LOOKUPS_PER_IP_PER_HOUR", "300")))
    lookups_per_minute_total: int = field(
        default_factory=lambda: int(_env("BLUEWATCH_LOOKUPS_PER_MINUTE_TOTAL", "120"))
    )
    daily_spend_cap_usd: float = field(default_factory=lambda: float(_env("BLUEWATCH_DAILY_SPEND_CAP_USD", "40")))
    # Idea Harbour: whether a team may ask Claude to read its answers (it still opts in per submission),
    # and the switch for a private pilot that keeps consented ideas on disk (never in public mode).
    ideas_model: bool = field(default_factory=lambda: _flag("BLUEWATCH_IDEAS_MODEL", "0"))
    ideas_persist: bool = field(default_factory=lambda: _flag("BLUEWATCH_IDEAS_PERSIST", "0"))
    ideas_persist_path: Path = field(
        default_factory=lambda: Path(_env("BLUEWATCH_IDEAS_PERSIST_PATH") or str(CACHE_DIR / "ideas_shared.jsonl"))
    )
    # The deployed commit, shown in /api/meta so anyone can check the site runs the latest code.
    build: str = field(default_factory=lambda: _env("BLUEWATCH_BUILD", "dev"))
    # Today in Helsinki; BLUEWATCH_TODAY pins a date so a recording or a test reads the same every run.
    today: date = field(default_factory=_today)


def settings() -> Settings:
    return Settings()
