"""The built front end: hashed chunks cache forever, the page itself is always checked again, and a
chunk from an older build is a 404 (never index.html, which a browser would fail to run as a script)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bluewatch.api import app as app_module
from bluewatch.api.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def built(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.js").write_text("export {};")
    (tmp_path / "index.html").write_text("<!doctype html><title>BlueWatch</title>")
    monkeypatch.setattr(app_module, "FRONTEND_DIST", tmp_path)


def test_hashed_chunk_is_cached_as_immutable():
    res = client.get("/assets/index-abc123.js")
    assert res.status_code == 200
    assert "immutable" in res.headers["cache-control"]


def test_missing_chunk_is_404_not_the_page():
    res = client.get("/assets/funding-OLDHASH.js")
    assert res.status_code == 404
    assert "text/html" not in res.headers["content-type"]


@pytest.mark.parametrize("path", ["/", "/surfacing", "/index.html"])
def test_page_is_always_revalidated(path):
    res = client.get(path)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert res.headers["cache-control"] == "no-cache"
