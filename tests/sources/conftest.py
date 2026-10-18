"""A stand-in for bluewatch.net so the live code paths run without a network."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from bluewatch import net


@pytest.fixture
def fake_net(monkeypatch):
    """Answer net.get / net.post from `routes` ({url part: body, (status, body) or an exception})."""
    routes: dict = {}
    calls: list = []

    def answer(method: str, url: str, **kwargs):
        calls.append(SimpleNamespace(method=method, url=url, params=kwargs.get("params"), body=kwargs.get("json_body")))
        for part, reply in routes.items():
            if part in url:
                if isinstance(reply, BaseException):
                    raise reply
                status, body = reply if isinstance(reply, tuple) else (200, reply)
                return net.CachedResponse(url, status, json.dumps(body), datetime.now(timezone.utc), False)
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(net, "get", lambda url, **kw: answer("GET", url, **kw))
    monkeypatch.setattr(net, "post", lambda url, json_body, **kw: answer("POST", url, json_body=json_body, **kw))
    return SimpleNamespace(routes=routes, calls=calls)
