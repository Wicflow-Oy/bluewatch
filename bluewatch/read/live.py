"""Read a looked-up company's own website for its live card, and keep only quote-checked claims.

Runs only when the server allows live lookups and has a model key (`enabled`). Everything happens within
READ_BUDGET_S, so the visitor never waits long for a card the register already answered:
- the site comes from the register's website field, or a guessed hostname with ownership evidence
  (site_finder.py);
- pages are fetched live, never cached and only from public addresses;
- the two model calls run side by side behind the shared daily spend cap;
- page text is data for the model, never instructions (prompts.py), and every claim must quote the page.
Nothing from the read is stored or logged. When the read cannot finish, the status says why and the
card keeps its register facts.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

import httpx
from pydantic import BaseModel

from bluewatch import net, spend
from bluewatch.config import settings
from bluewatch.llm import ModelClient
from bluewatch.models import Company, Evidence, Vertical
from bluewatch.read.classify import Classification, classification_evidence, classify_blue
from bluewatch.read.extract import read_claims
from bluewatch.read.fetch import Page
from bluewatch.read.site_finder import REGISTRY_FIELD, find_site

READ_BUDGET_S = 15.0
FETCH_TIMEOUT_S = 5.0
MIN_FETCH_S = 1.0  # less time than this left: give up instead of starting a fetch that cannot finish
MAX_REDIRECTS = 3
REDIRECTS = {301, 302, 303, 307, 308}

ReadState = Literal["read", "no_site", "unreachable", "timeout", "budget", "failed", "off"]

# Abandoned model calls finish here in the background; the SDK's own timeout (the read budget) ends them.
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="site-read")

Get = Callable[..., net.CachedResponse]


class SiteRead(BaseModel):
    """What the card says about the website read."""

    state: ReadState
    host: str | None = None
    url: str | None = None
    read_at: datetime | None = None
    found_in_register: bool = False  # else matched by name, with ownership evidence on the page
    claims: int = 0


@dataclass
class SiteReading:
    status: SiteRead
    evidence: list[Evidence] = field(default_factory=list)  # quote-checked, empty unless the site was read
    vertical: Vertical | None = None  # set when the site shows ocean or water work


def enabled() -> bool:
    s = settings()
    return s.live_lookups and bool(s.anthropic_api_key)


def read_site(
    company: Company, *, model: ModelClient | None = None, budget_s: float = READ_BUDGET_S, get: Get | None = None
) -> SiteReading:
    """The company's own site, read once. model and get stand in for Claude and the web in tests."""
    if model is None:
        if not enabled():
            return SiteReading(SiteRead(state="off"))
        if spend.ledger().spent_today() >= settings().daily_spend_cap_usd:
            return SiteReading(SiteRead(state="budget"))
        model = _claude(budget_s)
    deadline = time.monotonic() + budget_s
    site = find_site(company.registry, get=_within(deadline, get or _public_get))
    if site is None:
        return SiteReading(SiteRead(state="timeout" if _spent(deadline) else "no_site"))
    page = site.page
    status = SiteRead(
        state="read",
        host=page.domain,
        url=page.final_url,
        read_at=page.fetched_at,
        found_in_register=site.how == REGISTRY_FIELD,
    )
    if not page.ok:
        return SiteReading(status.model_copy(update={"state": "timeout" if _spent(deadline) else "unreachable"}))
    outcome = _ask(company, page, model, deadline)
    if isinstance(outcome, str):
        return SiteReading(status.model_copy(update={"state": outcome}))
    classification, claims = outcome
    found = [classification_evidence(company, page, classification, retrieved_at=page.fetched_at), *claims]
    evidence = list({e.id: e for e in found if e is not None}.values())  # both calls may quote the same line
    return SiteReading(
        status.model_copy(update={"claims": len(evidence)}),
        evidence,
        classification.vertical if classification.blue else None,
    )


def _ask(
    company: Company, page: Page, model: ModelClient, deadline: float
) -> tuple[Classification, list[Evidence]] | ReadState:
    """Classification and claims from the model, or why there are none ("timeout", "budget", "failed")."""
    model_id = settings().classifier_model
    classify = _pool.submit(classify_blue, page, model, model_id=model_id, company_names=company.names)
    extract = _pool.submit(read_claims, company, page, model, model_id=model_id, retrieved_at=page.fetched_at)
    done, _ = wait([classify, extract], timeout=max(0.0, deadline - time.monotonic()))
    if len(done) < 2:
        return "timeout"
    classification = classify.result()
    claims, problem = extract.result()
    # A model that could not answer leaves only the keyword reader's guess, which a live card does not show.
    problem = problem or classification.fallback
    if problem:
        return "budget" if "budget" in problem else "timeout" if "timeout" in problem else "failed"
    return classification, claims


def _claude(timeout_s: float) -> ModelClient:
    import anthropic  # only when a read may happen

    from bluewatch.read.anthropic_client import AnthropicModelClient

    sdk = anthropic.Anthropic(api_key=settings().anthropic_api_key, timeout=timeout_s, max_retries=0)
    return spend.capped(AnthropicModelClient(client=sdk))


def _spent(deadline: float) -> bool:
    return deadline - time.monotonic() < MIN_FETCH_S


def _within(deadline: float, get: Get) -> Get:
    """get, live and uncached, following up to MAX_REDIRECTS redirects itself, each hop cut to the time
    left in the read. get sees every hop's URL before it is requested, so _public_get can refuse it."""

    def fetch(url: str, **_: object) -> net.CachedResponse:
        for _hop in range(MAX_REDIRECTS + 1):
            if _spent(deadline):
                raise httpx.TimeoutException("the read's time budget is spent")
            left = deadline - time.monotonic()
            response = get(
                url, offline=False, use_cache=False, timeout_s=min(FETCH_TIMEOUT_S, left), follow_redirects=False
            )
            if response.status not in REDIRECTS or not response.location:
                return response
            url = str(httpx.URL(url).join(response.location))
        raise httpx.TooManyRedirects(f"more than {MAX_REDIRECTS} redirects")

    return fetch


def _public_get(url: str, **kwargs: object) -> net.CachedResponse:
    """net.get for addresses on the public internet only. A register's website field is written by whoever
    registered the company, so neither it nor a redirect it leads to may reach this server's own network.
    httpx never follows a redirect here: _within brings each hop back through this check."""
    _require_public(url)
    return net.get(url, **{**kwargs, "follow_redirects": False})


def _require_public(url: str) -> None:
    """Refuse anything but http(s) on the default ports to a dotted host name whose every address is public.
    The name is resolved here and again by httpx, so this narrows rather than closes DNS rebinding."""
    parsed = httpx.URL(url)
    if parsed.scheme not in ("http", "https") or parsed.port not in (None, 80, 443):
        raise httpx.InvalidURL("only http and https on the default ports")
    host = parsed.host
    if "." not in host.strip(".") and ":" not in host:  # "n8n", "localhost": container and LAN names
        raise httpx.InvalidURL("not a public web address")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, parsed.port or 443, proto=socket.IPPROTO_TCP)}
    except OSError as error:
        raise httpx.ConnectError(f"could not resolve {host}") from error
    if not addresses or not all(_is_public(a) for a in addresses):
        raise httpx.InvalidURL("not a public web address")


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    # is_global already excludes private (Docker's 172.16/12 too), loopback, link-local and reserved ranges.
    return ip.is_global and not ip.is_multicast
