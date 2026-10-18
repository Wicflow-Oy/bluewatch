"""Fetch one company page through bluewatch.net and turn the HTML into readable parts.

Only bluewatch.net touches the network or the disk cache: this module never writes page text anywhere.
A failed fetch is a Page with `error` set, never an exception, so a card can say why a site is missing.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser

import httpx

from bluewatch import net
from bluewatch.resolve.ids import find_ids
from bluewatch.resolve.names import domain_of

MAX_TEXT_CHARS = 100_000
# Pages we must not scrape, and which never belong to the company anyway.
REFUSED_HOSTS = ("linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "crunchbase.com")
META_KEYS = ("description", "og:title", "og:description", "og:site_name", "twitter:description")

_SKIP = {"script", "style", "noscript", "template", "svg", "iframe", "object", "canvas"}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_BLOCK = {
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "nav",
    "main",
    "aside",
    "li",
    "ul",
    "ol",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "tr",
    "td",
    "th",
    "form",
    "blockquote",
    "address",
    "br",
}


@dataclass
class Page:
    url: str
    final_url: str
    status: int  # HTTP status; 0 when nothing was fetched
    title: str
    text: str
    meta: dict[str, str]
    ids_found: list[str]
    fetched_at: datetime | None
    lang: str | None = None
    from_cache: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300 and bool(self.text or self.title or self.meta)

    @property
    def domain(self) -> str | None:
        return domain_of(self.final_url or self.url)

    def quotable(self) -> list[str]:
        """The parts a quote may come from: title, meta descriptions and body text."""
        return [self.title, *self.meta.values(), self.text]


def failed_page(url: str, error: str, status: int = 0) -> Page:
    return Page(
        url=url, final_url=url, status=status, title="", text="", meta={}, ids_found=[], fetched_at=None, error=error
    )


@dataclass
class _Parsed:
    title: str = ""
    text: str = ""
    meta: dict[str, str] = field(default_factory=dict)
    lang: str | None = None
    jsonld: list[str] = field(default_factory=list)


class _Reader(HTMLParser):
    """Visible text only: scripts, styles and hidden elements are skipped, so hidden instructions and
    tracking code do not reach the reader."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out = _Parsed()
        self._parts: list[str] = []
        self._title: list[str] = []
        self._in_title = False
        self._skip_tag: str | None = None
        self._skip_depth = 0
        self._jsonld: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip_tag:
            self._skip_depth += tag == self._skip_tag
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html" and a.get("lang"):
            self.out.lang = a["lang"].split("-")[0].lower()
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key in META_KEYS and a.get("content", "").strip() and key not in self.out.meta:
                self.out.meta[key] = a["content"].strip()
        elif tag == "title":
            self._in_title = True
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._jsonld = []
        if tag not in _VOID and (tag in _SKIP or _hidden(a)):
            self._skip_tag, self._skip_depth = tag, 1
            return
        if tag in _BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_tag:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if self._skip_depth == 0:
                    if self._jsonld is not None:
                        self.out.jsonld.append("".join(self._jsonld))
                        self._jsonld = None
                    self._skip_tag = None
            return
        if tag == "title":
            self._in_title = False
        elif tag in _BLOCK:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_tag:
            if self._jsonld is not None:
                self._jsonld.append(data)
        elif self._in_title:
            self._title.append(data)
        else:
            self._parts.append(data)

    def result(self) -> _Parsed:
        self.out.title = re.sub(r"\s+", " ", "".join(self._title)).strip()
        lines = (re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in "".join(self._parts).split("\n"))
        self.out.text = "\n".join(line for line in lines if line)[:MAX_TEXT_CHARS]
        return self.out


def _hidden(attrs: dict[str, str]) -> bool:
    style = attrs.get("style", "").replace(" ", "").lower()
    return (
        "hidden" in attrs
        or attrs.get("aria-hidden") == "true"
        or "display:none" in style
        or "visibility:hidden" in style
    )


def _jsonld_facts(blocks: list[str]) -> tuple[str | None, list[str]]:
    """The organisation description and any VAT/tax numbers declared in JSON-LD."""
    description, numbers = None, []
    stack: list[object] = []
    for block in blocks[:5]:
        try:
            stack.append(json.loads(block))
        except ValueError:
            continue  # malformed JSON-LD is common and carries nothing we can trust
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            if description is None and isinstance(node.get("description"), str):
                description = node["description"].strip() or None
            numbers += [str(node[k]) for k in ("vatID", "taxID") if node.get(k)]
            stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
    return description, numbers


def parse_html(html: str) -> _Parsed:
    reader = _Reader()
    reader.feed(html or "")
    reader.close()
    parsed = reader.result()
    if not parsed.title:
        parsed.title = parsed.meta.get("og:title", "")
    description, numbers = _jsonld_facts(parsed.jsonld)
    if description:
        parsed.meta.setdefault("jsonld:description", description)
    if numbers:
        parsed.meta.setdefault("jsonld:vat", " ".join(numbers))
    return parsed


def page_from_html(
    url: str,
    html: str,
    *,
    status: int = 200,
    final_url: str | None = None,
    fetched_at: datetime | None = None,
    from_cache: bool = False,
) -> Page:
    parsed = parse_html(html)
    ids = find_ids("\n".join([parsed.title, *parsed.meta.values(), parsed.text]))
    return Page(
        url=url,
        final_url=final_url or url,
        status=status,
        title=parsed.title,
        text=parsed.text,
        meta=parsed.meta,
        ids_found=ids,
        fetched_at=fetched_at,
        lang=parsed.lang,
        from_cache=from_cache,
    )


def _describe(error: Exception) -> str:
    message = str(error)
    if "CERTIFICATE_VERIFY_FAILED" in message or "certificate verify failed" in message.lower():
        return "the site's TLS certificate fails"
    if isinstance(error, httpx.TimeoutException):
        return "no answer before the timeout"
    if isinstance(error, httpx.ConnectError):
        return "could not connect (DNS or network)"
    return f"{type(error).__name__}: {message[:120]}"


def fetch_page(url: str, *, offline: bool | None = None, get: Callable[..., net.CachedResponse] = net.get) -> Page:
    """GET one page (cached snapshot when offline). Returns a Page; check `page.ok` and `page.error`."""
    url = url.strip()
    if "//" not in url:
        url = f"https://{url}"
    host = domain_of(url) or ""
    if not host:
        return failed_page(url, "not a web address")
    if any(host == h or host.endswith("." + h) for h in REFUSED_HOSTS):
        return failed_page(url, "a social or aggregator page; paste the company's own website")
    try:
        resp = get(url, offline=offline)
    except net.OfflineError:
        return failed_page(url, "offline, and no cached copy of this page")
    except (httpx.HTTPError, httpx.InvalidURL) as error:
        return failed_page(url, _describe(error))
    if resp.status >= 400:
        return failed_page(url, f"HTTP {resp.status}", status=resp.status)
    if resp.text.startswith("\x1f"):
        # net.py hands us text only, so a gzip body sent without its header cannot be recovered here.
        return failed_page(url, "compressed body without a Content-Encoding header", status=resp.status)
    return page_from_html(
        url, resp.text, status=resp.status, final_url=resp.url, fetched_at=resp.fetched_at, from_cache=resp.from_cache
    )
