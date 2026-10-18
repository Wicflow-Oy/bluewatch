"""Find a registered company's own website, and refuse sites that only share its name.

Order: the registry's website field, then hostnames guessed from the name. A guessed site attaches only
with ownership evidence: the company's own registry ID or VAT number on the page, or its name on the
page plus a local domain (.fi for a Finnish company) or its registered municipality. Name-only matches
on foreign sites (a Florida company, a Crete boat operator) are rejected.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from bluewatch import net
from bluewatch.models import Registry
from bluewatch.read.fetch import Page, fetch_page
from bluewatch.resolve.ids import normalise_id, parse_token
from bluewatch.resolve.names import GUESS_TLDS, domain_guesses, domain_of, name_on_page

MAX_GUESSES = 6
REGISTRY_FIELD = "registry website field"


@dataclass
class SiteCandidate:
    url: str
    page: Page
    how: str  # REGISTRY_FIELD or "guessed from the name"
    ownership: str  # the evidence that the site is the company's own
    confident: bool  # own ID/VAT on the page, or the registry names the site


def fetch_site(
    host_or_url: str, *, offline: bool | None = None, get: Callable[..., net.CachedResponse] = net.get
) -> Page:
    """The site's front page, trying the bare host and then www. (Clewat registered only www.)."""
    host = domain_of(host_or_url) or host_or_url
    page = fetch_page(f"https://{host}/", offline=offline, get=get)
    if not page.ok:
        www = fetch_page(f"https://www.{host}/", offline=offline, get=get)
        page = www if www.ok else page
    return page


def _shows_own_id(page: Page, registry: Registry) -> bool:
    own = (registry.country.upper(), normalise_id(registry.country, registry.id))
    return any(parse_token(t) == own for t in page.ids_found)


def _shows_any_local_id(page: Page, registry: Registry) -> bool:
    country = registry.country.upper()
    return any((p := parse_token(t)) and p[0] == country for t in page.ids_found)


def _ownership(page: Page, registry: Registry) -> tuple[str, bool] | None:
    """(evidence, confident) when the page belongs to the company, else None."""
    if _shows_own_id(page, registry):
        return f"the page shows its {registry.country} registry ID or VAT number", True
    if _shows_any_local_id(page, registry) or not registry.name:  # another company's site
        return None
    text = "\n".join(page.quotable())
    if not name_on_page(registry.name, text):
        return None
    local_tlds = GUESS_TLDS.get(registry.country.upper(), ())[:1]
    if any((page.domain or "").endswith(tld) for tld in local_tlds):
        return f"its name is on a local {local_tlds[0]} site", False
    if registry.municipality and name_on_page(registry.municipality, text):
        return f"its name and its registered municipality ({registry.municipality}) are on the page", False
    return None


def find_site(
    registry: Registry, *, offline: bool | None = None, get: Callable[..., net.CachedResponse] = net.get
) -> SiteCandidate | None:
    """The company's site, or None. A registered website that fails to load is still returned (with
    page.error set) so the card can say why, e.g. a failing TLS certificate."""
    if registry.website:
        page = fetch_site(registry.website, offline=offline, get=get)
        evidence = "the registry lists it as the company's website"
        if page.ok and _shows_own_id(page, registry):
            evidence += ", and the page shows the company's own ID"
        return SiteCandidate(page.url, page, REGISTRY_FIELD, evidence, True)
    if not registry.name:
        return None
    for host in domain_guesses(registry.name, registry.country)[:MAX_GUESSES]:
        page = fetch_page(f"https://{host}/", offline=offline, get=get)
        if not page.ok:
            continue
        owned = _ownership(page, registry)
        if owned:
            return SiteCandidate(page.url, page, "guessed from the name", owned[0], owned[1])
    return None
