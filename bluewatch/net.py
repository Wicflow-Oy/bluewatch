"""Shared HTTP access: generic User-Agent, timeouts, a polite pace and a raw-snapshot cache.

Offline mode (the default, and always in tests) serves only cached snapshots and raises
OfflineError otherwise, so callers can report the source as "cached" or "unavailable".

Public mode (the deployed app) never writes to disk: live responses, which may come from a
visitor-entered business ID, are kept only in a small in-memory cache for 15 minutes.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from bluewatch.config import CACHE_DIR, HTTP_TIMEOUT_S, USER_AGENT, settings


class OfflineError(RuntimeError):
    """Raised when a live request is needed but the app runs offline."""


@dataclass
class CachedResponse:
    url: str
    status: int
    text: str
    fetched_at: datetime
    from_cache: bool
    location: str | None = None  # the Location header of a redirect that was not followed

    def json(self):
        return json.loads(self.text)


def _cache_path(method: str, url: str, body: str | None) -> Path:
    key = hashlib.sha256(f"{method} {url} {body or ''}".encode("utf-8")).hexdigest()[:32]
    return CACHE_DIR / "http" / f"{key}.json"


_last_call: dict[str, float] = {}
_memory: dict[str, tuple[float, CachedResponse]] = {}
MEMORY_TTL_S = 15 * 60
MEMORY_MAX = 1000


def _memory_get(key: str) -> CachedResponse | None:
    hit = _memory.get(key)
    if hit and time.monotonic() - hit[0] < MEMORY_TTL_S:
        return hit[1]
    _memory.pop(key, None)
    return None


def _memory_put(key: str, value: CachedResponse) -> None:
    if len(_memory) >= MEMORY_MAX:
        oldest = min(_memory, key=lambda k: _memory[k][0])
        _memory.pop(oldest, None)
    _memory[key] = (time.monotonic(), value)


def _pace(host: str, min_interval_s: float) -> None:
    now = time.monotonic()
    wait = _last_call.get(host, 0.0) + min_interval_s - now
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def request(
    method: str,
    url: str,
    *,
    json_body: dict | None = None,
    params: dict | None = None,
    offline: bool | None = None,
    use_cache: bool = True,
    min_interval_s: float = 1.0,
    timeout_s: float = HTTP_TIMEOUT_S,
    follow_redirects: bool = True,
) -> CachedResponse:
    """GET/POST with the generic User-Agent. Returns a cached snapshot when offline.

    follow_redirects=False returns a redirect as it is, with its target in `location`, so a caller
    can check every hop before requesting it.
    """
    if params:
        url = str(httpx.URL(url, params=params))
    body = json.dumps(json_body, sort_keys=True) if json_body is not None else None
    path = _cache_path(method, url, body)
    conf = settings()
    is_offline = conf.offline if offline is None else offline
    if use_cache and conf.public_mode:
        hit = _memory_get(path.name)
        if hit is not None:
            return hit
    if use_cache and path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        cached = CachedResponse(raw["url"], raw["status"], raw["text"], datetime.fromisoformat(raw["fetched_at"]), True)
        if is_offline:
            return cached
    if is_offline:
        raise OfflineError(f"offline and not cached: {method} {url}")
    _pace(httpx.URL(url).host, min_interval_s)
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, timeout=timeout_s, follow_redirects=follow_redirects
    ) as client:
        resp = client.request(method, url, content=body, headers={"Content-Type": "application/json"} if body else None)
    fetched = CachedResponse(
        str(resp.url), resp.status_code, resp.text, datetime.now(timezone.utc), False, resp.headers.get("location")
    )
    if use_cache and conf.public_mode:
        if resp.status_code < 500:
            _memory_put(path.name, fetched)
        return fetched  # public mode never writes visitor-driven responses to disk
    if use_cache and resp.status_code < 500:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "url": fetched.url,
                    "status": fetched.status,
                    "text": fetched.text,
                    "fetched_at": fetched.fetched_at.isoformat(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return fetched


def get(url: str, **kwargs) -> CachedResponse:
    return request("GET", url, **kwargs)


def post(url: str, json_body: dict, **kwargs) -> CachedResponse:
    return request("POST", url, json_body=json_body, **kwargs)
