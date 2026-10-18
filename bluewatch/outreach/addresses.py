"""Organisation addresses only.

An address is kept only when its local part is a generic organisation inbox (info@, press@, ...) or a
role inbox (ceo@, founder@, ...) on the company's own domain. Anything else counts as personal: it is
recorded as `personal_blocked` with no address, so nobody can "unblock" it later by accident
(Act 917/2014 §200 needs prior consent for natural persons).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from bluewatch.models import Channel, ChannelKind

GENERIC_LOCAL_PARTS = frozenset(
    {"info", "hello", "hej", "hei", "kontakt", "contact", "yhteys", "office", "team", "sales", "myynti", "post"}
)
PRESS_LOCAL_PARTS = frozenset({"press", "media", "viestinta", "pr", "communications"})
ROLE_LOCAL_PARTS = frozenset(
    {"ceo", "founder", "founders", "cofounder", "toimitusjohtaja", "vd", "dagligleder", "cto", "coo"}
)
FREE_MAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "msn.com",
        "yahoo.com",
        "icloud.com",
        "me.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
        "gmx.com",
        "gmx.de",
        "web.de",
        "yandex.com",
        "mail.ru",
        "suomi24.fi",
        "luukku.com",
        "online.no",
        "telia.com",
    }
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


@dataclass(frozen=True)
class AddressCheck:
    kind: ChannelKind
    address: str | None  # normalised; always None for personal addresses
    on_company_domain: bool | None  # None when the company's domain is unknown
    reason: str


def domain_of(value: str | None) -> str | None:
    """Host of a URL, a bare domain or an e-mail address, lower case, without 'www.'."""
    if not value:
        return None
    value = value.strip().lower()
    if "@" in value and "://" not in value:
        host = value.rsplit("@", 1)[1]
    else:
        host = urlparse(value if "://" in value else f"//{value}").hostname or ""
    host = host.removeprefix("www.").strip(".")
    return host or None


def on_domain(host: str | None, company_domain: str | None) -> bool | None:
    if company_domain is None:
        return None
    return host is not None and (host == company_domain or host.endswith("." + company_domain))


def check_address(raw: str, *, company_domain: str | None) -> AddressCheck:
    """Classify one contact address. Personal-looking addresses are never returned."""
    company_domain = domain_of(company_domain)
    value = raw.strip().removeprefix("mailto:").strip()
    if value.lower().startswith(("http://", "https://")):
        host = domain_of(value)
        parsed = urlparse(value)
        form_url = f"https://{parsed.hostname}{parsed.path}" if parsed.hostname else None
        own = on_domain(host, company_domain)
        return AddressCheck("contact_form", form_url, own, "the organisation's contact form")
    if not EMAIL_RE.fullmatch(value):
        return AddressCheck("personal_blocked", None, None, "not a valid e-mail address")
    local, host = value.lower().rsplit("@", 1)
    if host in FREE_MAIL_DOMAINS:
        return AddressCheck("personal_blocked", None, None, f"a free-mail address ({host}) belongs to a person")
    own = on_domain(host, company_domain)
    if local in PRESS_LOCAL_PARTS:
        return AddressCheck("org_press", f"{local}@{host}", own, "the organisation's press address")
    if local in GENERIC_LOCAL_PARTS:
        return AddressCheck("org_generic", f"{local}@{host}", own, "the organisation's general address")
    if local in ROLE_LOCAL_PARTS:
        return AddressCheck("named_role", f"{local}@{host}", own, "a role address (founder or CEO)")
    return AddressCheck("personal_blocked", None, None, "the address looks like a person's own address")


def sanitise(channel: Channel, *, company_domain: str | None) -> Channel:
    """The channel as it may be stored: personal addresses removed, role addresses never treated as generic."""
    if channel.address is None:
        return channel
    blocked = Channel(kind="personal_blocked", source_url=channel.source_url)
    if channel.kind == "personal_blocked":
        return blocked
    check = check_address(channel.address, company_domain=company_domain)
    if check.kind == "personal_blocked":
        return blocked
    # The address decides the kind (a ceo@ address declared as generic still needs the role check),
    # except that a declared role or opt-in route keeps its stricter proof requirement.
    keep_declared = channel.kind in ("named_role", "opt_in") and check.kind != "named_role"
    kind = channel.kind if keep_declared else check.kind
    return channel.model_copy(update={"kind": kind, "address": check.address})


def channels_from_page(text: str, *, company_domain: str, source_url: str) -> list[Channel]:
    """Organisation channels found on the company's own page. Personal addresses are counted, not kept."""
    channels: list[Channel] = []
    seen: set[str] = set()
    personal_found = False
    for raw in EMAIL_RE.findall(text):
        check = check_address(raw, company_domain=company_domain)
        if check.kind == "personal_blocked":
            personal_found = True
        elif check.on_company_domain and check.address not in seen:
            seen.add(check.address)
            channels.append(Channel(kind=check.kind, address=check.address, source_url=source_url))
        # Organisation addresses on other domains (a web agency, a landlord) are not this company's: dropped.
    if personal_found:
        channels.append(Channel(kind="personal_blocked", source_url=source_url))
    return channels
