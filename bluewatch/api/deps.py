"""Request plumbing shared by the API routers: one rate limiter for every public endpoint, a size-capped body
reader, and the validated mode and preset parameters."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request

from bluewatch.api.guards import RateLimiter
from bluewatch.config import settings
from bluewatch.models import Mode
from bluewatch.rules.presets import preset_names

ModeParam = Mode
_limiter: RateLimiter | None = None


def limiter() -> RateLimiter:
    """The one limiter, so lookups and idea checks share a visitor's hourly budget."""
    global _limiter
    if _limiter is None:
        s = settings()
        _limiter = RateLimiter(per_ip_per_hour=s.lookups_per_ip_per_hour, total_per_minute=s.lookups_per_minute_total)
    return _limiter


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_check(request: Request, detail: str | None = None) -> None:
    """Raise 429 when the visitor or the whole server is over its limit; `detail` replaces the limiter's reason."""
    ok, why = limiter().allow(client_ip(request))
    if not ok:
        raise HTTPException(status_code=429, detail=detail or why)


async def read_capped(request: Request, limit: int, detail: str) -> bytes:
    """The request body, refused with 413 as soon as it would pass `limit` bytes.

    A declared Content-Length over the limit is refused before anything is read; without one (chunked, or a
    lying client) the body is read chunk by chunk and abandoned the moment the running total passes the limit,
    so an oversized upload never sits in memory whole."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail=detail)
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail=detail)
        chunks.append(chunk)
    return b"".join(chunks)


def preset_param(preset: str = Query("blue")) -> str:
    """A preset that exists in data/presets, so adding a preset file needs no code change."""
    if preset not in preset_names():
        raise HTTPException(status_code=422, detail=f"Unknown preset. Available: {', '.join(preset_names())}.")
    return preset


PresetParam = Annotated[str, Depends(preset_param)]
