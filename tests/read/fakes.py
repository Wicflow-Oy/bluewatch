"""Test doubles for the reader: a fake bluewatch.net.get and a tiny HTML builder."""

from __future__ import annotations

from datetime import datetime, timezone

from bluewatch import net
from bluewatch.llm import ModelRequest, ModelResponse

FETCHED = datetime(2026, 10, 17, 9, 0, tzinfo=timezone.utc)


class FakeWeb:
    """Serves HTML by URL like bluewatch.net.get; unknown URLs behave like an offline cache miss."""

    def __init__(self, pages: dict[str, str | int | Exception]):
        self.pages = pages
        self.calls: list[str] = []

    def __call__(self, url: str, **kwargs) -> net.CachedResponse:
        self.calls.append(url)
        value = self.pages.get(url)
        if value is None:
            raise net.OfflineError(f"offline and not cached: GET {url}")
        if isinstance(value, Exception):
            raise value
        if isinstance(value, int):
            return net.CachedResponse(url, value, "", FETCHED, False)
        return net.CachedResponse(url, 200, value, FETCHED, True)


def html(title: str, body: str, description: str = "") -> str:
    meta = f'<meta name="description" content="{description}">' if description else ""
    return f"<html><head><title>{title}</title>{meta}</head><body>{body}</body></html>"


class ScriptedClient:
    """A ModelClient that returns one fixed response (or raises), e.g. the spend guard's budget refusal."""

    name = "scripted"

    def __init__(self, response: ModelResponse | Exception):
        self.response = response
        self.calls: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


BUDGET = ModelResponse(text="", refused=True, stop_reason="budget")
