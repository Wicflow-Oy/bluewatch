import socket
import threading
import time

import httpx
import pytest

from bluewatch import net
from bluewatch.llm import FakeModelClient, ModelRequest, ModelResponse
from bluewatch.models import Company, Registry, Resolution
from bluewatch.read import live
from tests.read.fakes import BUDGET, FETCHED, FakeWeb, ScriptedClient, html

WESI = Company(
    id="FI:2902007-2",
    names=["Arctic Fry Oy"],
    resolution=Resolution(state="resolved", reason="test"),
    registry=Registry(country="FI", id="2902007-2", name="Arctic Fry Oy", website="wesi.fi"),
)
WEB = FakeWeb(
    {
        "https://wesi.fi/": html(
            "WESI Solutions | Automated fish farming",
            "<p>WESI Solutions AI technology improves efficiency of fish farming.</p>"
            "<p>We serve fish farmers in Finland and Norway with a monthly subscription.</p>",
        )
    }
)
CLAUDE = FakeModelClient(
    {
        "classify_blue": {
            "blue": True,
            "vertical": "blue_biotech_water",
            "quote": "Automated fish farming",
            "reason": "Fish farming automation.",
        },
        "extract_claims": {
            "claims": [
                {
                    "field": "customers",
                    "claim": "Customers are fish farms.",
                    "value": "fish farmers",
                    "quote": "We serve fish farmers in Finland and Norway",
                },
                {
                    "field": "pricing",
                    "claim": "Sold as a subscription.",
                    "value": "subscription",
                    "quote": "with a yearly licence",  # not on the page
                },
            ]
        },
    }
)


def test_a_registered_site_is_read_into_quote_checked_evidence():
    site = live.read_site(WESI, model=CLAUDE, get=WEB)
    assert site.status.state == "read" and site.status.found_in_register
    assert (site.status.host, site.status.url, site.status.read_at) == ("wesi.fi", "https://wesi.fi/", FETCHED)
    assert site.vertical == "blue_biotech_water"
    assert {e.field for e in site.evidence} == {"vertical", "customers"}  # the unquoted pricing claim is gone
    assert all(e.verified_quote and e.url == "https://wesi.fi/" and e.retrieved_at == FETCHED for e in site.evidence)
    assert site.status.claims == 2


def test_pages_are_fetched_live_without_a_cache():
    seen: list[dict] = []

    def web(url: str, **kwargs):
        seen.append(kwargs)
        return WEB(url)

    live.read_site(WESI, model=CLAUDE, get=web)
    assert seen and all(k["offline"] is False and k["use_cache"] is False for k in seen)
    assert all(0 < k["timeout_s"] <= live.FETCH_TIMEOUT_S for k in seen)


def test_no_site_and_an_unreachable_site_keep_the_register_card():
    nameless = WESI.model_copy(update={"registry": WESI.registry.model_copy(update={"website": None, "name": None})})
    assert live.read_site(nameless, model=CLAUDE, get=FakeWeb({})).status.state == "no_site"
    down = live.read_site(WESI, model=CLAUDE, get=FakeWeb({"https://wesi.fi/": 503, "https://www.wesi.fi/": 503}))
    assert down.status.state == "unreachable" and down.status.host == "wesi.fi" and down.evidence == []


def test_a_spent_budget_is_said_and_nothing_is_guessed():
    site = live.read_site(WESI, model=ScriptedClient(BUDGET), get=WEB)
    assert site.status.state == "budget" and site.evidence == [] and site.vertical is None


def test_a_model_failure_is_said_and_nothing_is_guessed():
    broken = ScriptedClient(ModelResponse(text="", refused=True, stop_reason="connection_error"))
    assert live.read_site(WESI, model=broken, get=WEB).status.state == "failed"


def test_a_slow_model_gives_way_to_the_register_card():
    release = threading.Event()

    class Slow:
        name = "slow"

        def complete(self, request: ModelRequest) -> ModelResponse:
            release.wait(5)
            return ModelResponse(text="", refused=True, stop_reason="refusal")

    try:
        assert live.read_site(WESI, model=Slow(), get=WEB, budget_s=2.0).status.state == "timeout"
    finally:
        release.set()


def test_without_a_key_nothing_is_fetched(monkeypatch):
    monkeypatch.setenv("BLUEWATCH_LIVE_LOOKUPS", "1")
    web = FakeWeb({})
    assert live.read_site(WESI, get=web).status.state == "off" and web.calls == []
    assert not live.enabled()


@pytest.mark.parametrize("url", ["http://127.0.0.1:8787/", "https://localhost/", "http://10.0.0.5/", "http://[::1]/"])
def test_only_public_addresses_are_fetched(url):
    with pytest.raises(httpx.InvalidURL):
        live._require_public(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://n8n:5678/webhook/x",  # a container name on the shared Docker network
        "https://example.com:8443/",
        "ftp://example.com/",
        "http://169.254.169.254/latest/meta-data/",
        "http://172.18.0.2/",  # Docker's default bridge range
        "http://224.0.0.1/",
        "http://[::ffff:127.0.0.1]/",
    ],
)
def test_internal_ports_schemes_and_names_are_refused(url):
    with pytest.raises(httpx.InvalidURL):
        live._require_public(url)


class FakeInternet:
    """httpx.MockTransport behind bluewatch.net plus a fake DNS, recording every request that went out."""

    def __init__(self, monkeypatch, dns: dict[str, str], routes: dict[str, httpx.Response]):
        self.sent: list[str] = []
        real_client = httpx.Client

        def handler(request: httpx.Request) -> httpx.Response:
            self.sent.append(str(request.url))
            return routes[str(request.url)]

        def resolve(host, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (dns[host], 443))]

        monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
        monkeypatch.setattr(socket, "getaddrinfo", resolve)
        monkeypatch.setattr(net, "_pace", lambda *a, **k: None)

    def get(self, url: str) -> net.CachedResponse:
        return live._within(time.monotonic() + 10, live._public_get)(url)


def _redirect(to: str) -> httpx.Response:
    return httpx.Response(302, headers={"Location": to})


def test_a_redirect_into_the_servers_network_is_never_requested(monkeypatch):
    web = FakeInternet(
        monkeypatch,
        {"evil.example": "93.184.215.14", "inside.example": "172.18.0.5"},
        {
            "https://evil.example/": _redirect("http://n8n:5678/webhook/x"),
            "https://evil.example/2": _redirect("https://inside.example/"),
        },
    )
    with pytest.raises(httpx.InvalidURL):
        web.get("https://evil.example/")
    with pytest.raises(httpx.InvalidURL):
        web.get("https://evil.example/2")  # a public name that resolves inside
    assert web.sent == ["https://evil.example/", "https://evil.example/2"]


def test_public_redirects_are_followed_up_to_three_hops(monkeypatch):
    dns = {"a.example": "93.184.215.14", "b.example": "93.184.215.15"}
    routes = {
        "http://a.example/": _redirect("https://a.example/"),
        "https://a.example/": _redirect("/home"),
        "https://a.example/home": _redirect("https://b.example/"),
        "https://b.example/": httpx.Response(200, text="<html>ok</html>"),
        "https://b.example/loop": _redirect("https://b.example/loop"),
    }
    web = FakeInternet(monkeypatch, dns, routes)
    page = web.get("http://a.example/")
    assert (page.status, page.url, page.text) == (200, "https://b.example/", "<html>ok</html>")
    with pytest.raises(httpx.TooManyRedirects):
        web.get("https://b.example/loop")
    assert web.sent.count("https://b.example/loop") == live.MAX_REDIRECTS + 1
