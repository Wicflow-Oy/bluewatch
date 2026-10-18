"""Test guards: no live network (loopback only), offline settings, a fixed 'today'."""

from __future__ import annotations

import os

os.environ["BLUEWATCH_SKIP_ENV_LOCAL"] = "1"  # tests never read real keys from .env.local
os.environ["BLUEWATCH_TODAY"] = "2026-10-17"  # the expected dates and countdowns are written for this day

import socket  # noqa: E402
from datetime import date  # noqa: E402

import pytest  # noqa: E402

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_real_connect = socket.socket.connect
_real_create_connection = socket.create_connection


def _host(address) -> str | None:
    if isinstance(address, tuple) and address:
        return str(address[0])
    return None  # unix sockets and the like


def _guarded_connect(self, address):
    host = _host(address)
    if host is not None and host not in _LOOPBACK:
        raise RuntimeError(f"Live network is disabled in tests (tried {host}); use a recorded fixture.")
    return _real_connect(self, address)


def _guarded_create_connection(address, *args, **kwargs):
    host = _host(address)
    if host is not None and host not in _LOOPBACK:
        raise RuntimeError(f"Live network is disabled in tests (tried {host}); use a recorded fixture.")
    return _real_create_connection(address, *args, **kwargs)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("BLUEWATCH_OFFLINE", "1")
    monkeypatch.setenv("OUTREACH_MODE", "demo")
    monkeypatch.setenv("BLUEWATCH_LIVE_LOOKUPS", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    # Loopback stays allowed: asyncio on Windows needs it for its internal socket pair.
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket, "create_connection", _guarded_create_connection)


@pytest.fixture
def today() -> date:
    return date(2026, 10, 17)
