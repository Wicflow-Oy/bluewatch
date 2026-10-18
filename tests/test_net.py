import httpx

from bluewatch import net


def test_public_mode_never_writes_disk(monkeypatch, tmp_path):
    monkeypatch.setenv("BLUEWATCH_PUBLIC", "1")
    monkeypatch.setattr(net, "CACHE_DIR", tmp_path)

    class FakeResp:
        status_code = 200
        text = '{"ok": true}'
        url = "https://example.test/x"
        headers: dict[str, str] = {}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def request(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr(net.httpx, "Client", FakeClient)
    monkeypatch.setattr(net, "_pace", lambda *a, **k: None)
    first = net.get("https://example.test/x", offline=False)
    second = net.get("https://example.test/x", offline=False)
    assert first.text == second.text
    assert not any(tmp_path.rglob("*")), "public mode wrote to disk"


def test_offline_without_cache_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(net, "CACHE_DIR", tmp_path)
    try:
        net.get("https://example.test/never-cached")
    except net.OfflineError:
        return
    raise AssertionError("expected OfflineError")


def test_a_redirect_can_be_returned_unfollowed(monkeypatch):
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(str(request.url))
        return httpx.Response(302, headers={"Location": "http://n8n:5678/"})

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(net, "_pace", lambda *a, **k: None)
    resp = net.get("https://example.test/r", offline=False, use_cache=False, follow_redirects=False)
    assert (resp.status, resp.location, sent) == (302, "http://n8n:5678/", ["https://example.test/r"])
