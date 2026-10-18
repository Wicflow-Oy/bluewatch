"""The verified demo pack -> contract objects (Company, Evidence, Signal), with honest tags.

Inputs: startups.json rows, the curated list rows (monday10_demo_2026-10-12.json, "why" lines with
their source links), signals_cache.json (PRH share-issue notices, TED awards, certificate hostnames)
and the Meriva gap ledger in bridges_seed.json.

Tags say where a claim comes from: "registry" (a company register), "ted", "read" (a page our
researchers opened), "site" (the company's own page, not quote-checked), "snippet" (a search
summary: always an assumption, never a fact) and "dossier" (the research pack with no page link).
Answer keys are deliberately never read here: they are the reference the rules are measured against.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone
from functools import lru_cache
from urllib.parse import urlparse

from bluewatch import seed
from bluewatch.models import (
    Company,
    EntityRef,
    Evidence,
    NextCheck,
    Registry,
    Resolution,
    Signal,
    Vertical,
)
from bluewatch.rules.evidence import FIELD_ALIASES
from bluewatch.rules.geo import country_code
from bluewatch.rules.text import approx_date, parse_date, slug

PACK_AT = datetime(2026, 10, 17, tzinfo=timezone.utc)  # the demo pack was normalised on 17 Oct 2026
LIST_RUN_AT = datetime(2026, 10, 12, 7, 0, tzinfo=timezone.utc)  # the curated list's Monday run
SIGNALS_AT = datetime(2026, 10, 17, 0, 51, tzinfo=timezone.utc)  # signals_cache.json fetched_at

VERTICALS = ("maritime_ports", "ocean_infra_clean_energy", "marine_intelligence", "blue_biotech_water", "other")
REGISTRY_PAGES = {
    "FI": "https://tietopalvelu.ytj.fi/yritys/{id}",
    "NO": "https://virksomhet.brreg.no/nb/oppslag/enheter/{id}",
    "EE": "https://ariregister.rik.ee/eng/company/{id}",
}
REGISTRY_SOURCE = {"FI": "prh", "NO": "brreg", "EE": "rik"}
REGISTRY_LABEL = {"FI": "PRH", "NO": "Brreg", "EE": "RIK"}
REGISTRY_HOSTS = ("avoindata.prh.fi", "ytj.fi", "data.brreg.no", "brreg.no", "ariregister.rik.ee")

# Hostnames in certificate logs that mean a product people use, versus one still being built.
LIVE_HOSTS = ("app", "api", "dashboard", "portal", "shop", "mqtt", "docs")
DEV_HOSTS = ("dev", "staging", "test", "beta", "admin")

LEGAL_FORMS = {
    "oyj": "OYJ",
    "abp": "OYJ",
    "oy": "OY",
    "ab": "AB",
    "publ": "AB (publ)",
    "asa": "ASA",
    "as": "AS",
    "aps": "APS",
    "ou": "OU",
    "oü": "OU",
    "ehf": "EHF",
    "sia": "SIA",
    "uab": "UAB",
    "gmbh": "GMBH",
    "plc": "PLC",
}
# The register's own words for a legal form (PRH gives Swedish or English, never the code).
REGISTER_FORMS = {
    "aktiebolag": "OY",
    "limited company": "OY",
    "osakeyhtiö": "OY",
    "publikt aktiebolag": "OYJ",
    "public limited company": "OYJ",
    "julkinen osakeyhtiö": "OYJ",
}
NATURAL_PERSON_FORMS = ("toiminimi", "enskild", "enk", "fie", "elinkeinonharjoittaja")

# First match wins: the order puts specific phrases ("invested in 20 vessels" is an order, an
# "Innovation Fund grant" is non-dilutive) ahead of the general ones.
FIELD_RULES: tuple[tuple[str, str], ...] = (
    (r"^founded\b", "founded"),
    (r"^registered in\b", "registered_office"),
    (r"own business id", "identity"),
    (r"\binvested in \d+|\bordered\b", "customers"),
    (r"\bpartner|\bsupporter", "partners"),
    (r"\bshare[- ]issue", "funding"),
    (r"\btenders?\b", "market"),
    (r"\bcontract award|\bwinner\b|\bwon\b|\bpublic wins?\b|\bted notice\b", "public_contracts"),
    (r"\bbiodiversity increase|\bemissions? reduction|\bco2 (reduction|savings)", "impact"),
    (r"\bteam\b|\bemploys?\b|\bemployees\b", "team"),
    (
        r"\bgrant\b|co-funded|\beu (funding|backing|co-funding)\b|\bpublic (backing|funding)\b|\bvoucher\b"
        r"|\bhorizon 2020\b|\beic accelerator\b",
        "grant",
    ),
    (
        r"\bseries [a-f]\b|\bfunding round\b|\bround of\b|\braised\b|\bnew capital\b|\binvestment\b"
        r"|redstone-managed|\bportfolio\b|\bacquired by\b|\bfund\b|\bcrowdfunding\b",
        "funding",
    ),
    (
        r"\bcohort\b|\bbatch\b|\baccelerator\b|\bprogramme\b|\bselected for\b|\binnovator\b|\bcampus\b"
        r"|\bspin-off\b",
        "programme",
    ),
    (r"\bawards?\b|\bprize\b|\breward\b|\branking\b|\branked\b|\bstartup map\b", "award"),
    (r"\bpilot\b|\bdemo\b|\bdemonstrator\b|\b(sea|field) trial\b|\bproof-of-concept\b", "pilot"),
    (r"\binstalled\b|\bdeployed\b|\bfleet\b|\bin operation\b|\bdeliver", "deployment"),
    (r"\bcustomers?\b|\bclients?\b", "customers"),
    (r"\bcertif|\bapproval\b|\bconformance\b", "certification"),
    (r"\bpatent", "tech"),
    (r"\bpresent at\b|\bexhibit", "marketing"),
    (r"\bdeletion notice|\bstatus needs checking|\bnot confirmed\b", "registry_status"),
    (r"\baddress\b|\blocation\b", "location"),
)
# A hedged claim is an assumption. Self-reported site claims stay facts (the site does say so);
# the rules lower their confidence instead.
HEDGES = re.compile(
    r"\bweak\b|\bunverified\b|\bnot verified\b|search[- ](result )?summary|search snippet|via search"
    r"|per search|aggregator|third-party directory|filename only|logo only|claim seen in search"
)
SELF_REPORTED = re.compile(r"self-reported|site claims|company claims")
SNIPPET_HINT = re.compile(r"search[- ](result )?summary|search snippet|via search|per search|aggregator")
# Curated-list lines that describe how the list run found a company ("keywords missed it: reader caught it").
DISCOVERY_NOTE = re.compile(r"caught it|keywords missed|found only through|\bprior\b|matched control|young \(")


# --------------------------------------------------------------------------- public entry points
def company_and_evidence(row: dict) -> tuple[Company, list[Evidence], list[Signal]]:
    """One demo-pack row (a startups.json row or a curated list row) as contract objects."""
    if "why" in row and "rank" in row:
        return _from_list_row(row)
    return _from_startup_row(row)


def demo_items() -> list[tuple[Company, list[Evidence], list[Signal]]]:
    """Every company in the pack once: startups.json rows, plus the curated list rows. A list row for
    a company that is already a startup row adds only the claims of fields that row lacks."""
    items: dict[str, tuple[Company, list[Evidence], list[Signal]]] = {}
    for row in seed.load("startups")["startups"]:
        company, evidence, signals = _from_startup_row(row)
        items.setdefault(company.id, (company, evidence, signals))
    for row in seed.load("demo_list_2026_10_12")["rows"]:
        company, evidence, signals = _from_list_row(row)
        if company.id not in items:
            items[company.id] = (company, evidence, signals)
            continue
        known, known_evidence, known_signals = items[company.id]
        have = {e.field for e in known_evidence}
        extra = [e for e in evidence if e.field not in have]
        merged = known.model_copy(update={"tags": sorted(set(known.tags) | set(company.tags))})
        items[company.id] = (merged, known_evidence + _renumber(extra, company.id, len(known_evidence)), known_signals)
    return list(items.values())


# --------------------------------------------------------------------------- startups.json rows
def _from_startup_row(row: dict) -> tuple[Company, list[Evidence], list[Signal]]:
    cc, reg_id = _registry_key(row)
    check = row.get("registry_check") or {}
    domain = _domain(row.get("website"))
    company_id = f"{cc or 'XX'}:{reg_id or slug(row['name'])}"
    tags = _startup_tags(row)
    evidence: list[Evidence] = []
    add = _Collector(company_id, evidence)

    founded = _registry_founded(check)
    if check and reg_id and cc in REGISTRY_PAGES:
        add.registry_facts(cc, reg_id, check, founded)
    elif row.get("founded"):
        add.founded_claim(row["founded"], row.get("website"), domain)

    product_tag, product_state = _one_liner_tag(row)
    if row.get("one_liner"):
        url = row.get("website") or _first_url(row, exclude=REGISTRY_HOSTS)
        add(
            field="product",
            claim=row["one_liner"],
            url=url,
            tag=product_tag,
            state=product_state,
            family=_family_for(url, domain, cc, product_tag),
        )
    if (row.get("site_check") or {}).get("own_id_on_homepage"):
        add(
            field="identity",
            claim="Shows its own business ID on its site (strict entity match)",
            url=row.get("website"),
            tag="read",
            family=_site_family(domain),
        )

    read_ok = bool(set(row.get("source_tags") or []) & {"read", "company-site", "company_site", "news_article"})
    for text, when, url in _stage_signals(row):
        add.stage_signal(text, when, url, domain, cc, read_ok)

    signals = _cached_signals(row, company_id, cc, reg_id, add)
    if founded and _recent(founded):
        signals.append(_founded_signal(cc, reg_id, founded, PACK_AT))

    company = Company(
        id=company_id,
        names=_names(row["name"], row.get("legal_name"), check.get("name")),
        registry=Registry(
            country=cc or "XX",
            id=reg_id or "",
            name=check.get("name") or row.get("legal_name") or row["name"],
            founded=founded,
            form=_legal_form(check.get("form"), check.get("name") or row.get("legal_name") or row["name"]),
            industry_code=check.get("tol"),
            industry_scheme=("TOL2008" if cc == "FI" else "NACE") if check.get("tol") else None,
            municipality=check.get("municipality") or row.get("postal_city"),
            website=check.get("website") or row.get("website"),
            status=check.get("status"),
            natural_person=_is_natural_person(check.get("form"), row.get("legal_name")),
            employees=check.get("employees"),
        ),
        domain=domain,
        vertical=row.get("vertical") if row.get("vertical") in VERTICALS else None,
        vertical_note=row.get("subsector"),
        resolution=_resolution(row, check, reg_id, domain),
        signal_ids=[s.id for s in signals],
        tags=tags,
        one_liner=row.get("one_liner"),
    )
    return company, evidence, signals


def _registry_key(row: dict) -> tuple[str | None, str | None]:
    ids = row.get("registry_ids") or {}
    for key, values in ids.items():
        value = values[0] if isinstance(values, list) and values else values
        if not value:
            continue
        if key == "dk_vat":
            # A Danish VAT number is "DK" plus the company's 8-digit CVR number, its register ID.
            return "DK", str(value).removeprefix("DK")
        return key.upper(), value
    return country_code(row.get("country")), None


def _registry_founded(check: dict) -> date | None:
    return parse_date(check.get("founded") or check.get("registered"))


def _startup_tags(row: dict) -> list[str]:
    link = (row.get("judge_link") or "").lower()
    tags = {f"seed:{row['origin']}"}
    signals_text = " ".join(t for t, _, _ in _stage_signals(row)).lower()
    if row["origin"] == "judge_known_apelago" or "a'pelago" in link or "a'pelago" in signals_text:
        tags.add("apelago_cohort")
    if row["origin"] == "judge_known_redstone" or "redstone blue portfolio" in link or "redstone" in signals_text:
        tags.add("redstone_portfolio")
    if "famous" in link:
        tags.add("famous_control")
    return sorted(tags)


def _one_liner_tag(row: dict) -> tuple[str, str]:
    """(tag, state) for the row's one-line description."""
    text = (row.get("one_liner") or "").lower()
    tags = set(row.get("source_tags") or [])
    if text.startswith("registry only"):
        return "registry", "fact"
    if SNIPPET_HINT.search(text) or (
        tags & {"snippet", "search-summary", "search_snippet", "third_party_directory", "aggregator_cited_TED"}
        and not tags & {"read", "company-site", "company_site"}
    ):
        return "snippet", "assumption"
    if "ted_winner" in tags:
        return "ted", "fact"
    if tags & {
        "read",
        "company-site",
        "company_site",
        "news_article",
        "crowdfunding_listing",
        "apelago",
        "sjavarklasinn",
        "katapult",
        "aqua-spark",
        "redstone",
        "notable-nordic-ocean-tech",
        "brreg",
    }:
        return "read", "fact"
    return "dossier", "fact"


def _stage_signals(row: dict) -> list[tuple[str, str | None, str | None]]:
    """(text, date text, url) per stage signal; the pack stores them as dicts or plain strings."""
    out = []
    for s in row.get("stage_signals") or []:
        if isinstance(s, str):
            out.append((s, None, None))
        else:
            text = s.get("detail") or s.get("signal") or ""
            out.append((text, s.get("date"), s.get("source") or s.get("source_url")))
    return [o for o in out if o[0]]


def _resolution(row: dict, check: dict, reg_id: str | None, domain: str | None) -> Resolution:
    if check and (row.get("site_check") or {}).get("own_id_on_homepage"):
        return Resolution(state="resolved", reason="Business ID shown on the company's own site")
    if check and domain and _domain(check.get("website")) == domain:
        return Resolution(state="resolved", reason="The register's website field matches the company domain")
    if check:
        return Resolution(state="probable", reason="Register record found; site ownership not confirmed")
    if reg_id:
        return Resolution(state="probable", reason="Register ID from the research pack; not re-checked")
    return Resolution(state="unresolved", reason="No register record found in the research pack")


# --------------------------------------------------------------------------- curated list rows
def _from_list_row(row: dict) -> tuple[Company, list[Evidence], list[Signal]]:
    registry_name, reg_id = row["registry"].split()
    cc = {"PRH": "FI", "Brreg": "NO", "RIK": "EE"}[registry_name]
    company_id = f"{cc}:{reg_id}"
    founded = parse_date(row.get("founded"))
    site = next((u for u in row["sources"] if not any(h in u for h in REGISTRY_HOSTS + ("ted.europa.eu",))), None)
    domain = _domain(site)
    municipality = re.sub(r"\s*\(.*\)$|^see .*", "", row.get("municipality") or "").strip()  # "see PRH" is a note
    vertical, note = _list_vertical(row.get("vertical") or "")
    tags = {"seed:demo_list"}
    if "pre-launch" in row["chip"].lower():
        tags.add("pre_launch")

    evidence: list[Evidence] = []
    add = _Collector(company_id, evidence, first_seen=LIST_RUN_AT, retrieved=PACK_AT)
    ledger = _gap_ledger(company_id)
    if ledger:
        add.ledger(ledger, domain)
    else:
        if founded:
            where = f" in {municipality}" if municipality else ""
            add(
                field="founded",
                claim=f"Founded {founded:%d %b %Y}{where} ({REGISTRY_LABEL[cc]})",
                value=founded.isoformat(),
                event_date=founded,
                url=REGISTRY_PAGES[cc].format(id=reg_id),
                tag="registry",
                family=REGISTRY_SOURCE[cc],
            )
        for line in row["why"]:
            add.list_line(line, row["sources"], cc, reg_id, domain)
        if row.get("fit_note"):
            add(
                field="assessment_note",
                claim=row["fit_note"],
                tag="dossier",
                state="assumption",
                family="research_pack",
                basis="Analyst note in the research pack",
            )
    own_id = any("own business id" in line.lower() for line in row["why"])
    if own_id:
        tags.add("own_id_on_site")

    signals = [_founded_signal(cc, reg_id, founded, LIST_RUN_AT)] if founded and _recent(founded) else []
    signals += _list_share_issue_signals(row, cc, reg_id)
    company = Company(
        id=company_id,
        names=[row["name"]],
        registry=Registry(
            country=cc,
            id=reg_id,
            name=row["name"],
            founded=founded,
            form=_legal_form(None, row["name"]),
            municipality=municipality or None,
            website=site,
        ),
        domain=domain,
        vertical=vertical,
        vertical_note=note,
        resolution=Resolution(state="resolved", reason="Business ID shown on the company's own site")
        if own_id
        else Resolution(state="probable", reason="Register record; site matched by name and read by hand"),
        signal_ids=[s.id for s in signals],
        tags=sorted(tags),
        one_liner=next((e.claim for e in evidence if e.field == "product"), None),
    )
    return company, evidence, signals


def _list_vertical(text: str) -> tuple[Vertical | None, str | None]:
    key, _, rest = text.partition(" ")
    note = rest.strip(" ()") or None
    if key in VERTICALS:
        return key, note  # type: ignore[return-value]
    return None, text or None


def _list_share_issue_signals(row: dict, cc: str, reg_id: str) -> list[Signal]:
    """Share issues named in the list's "why" lines (dated to the day when the line gives one)."""
    out = []
    for line in row["why"]:
        if "share-issue decision registered" in line.lower():
            when = _day_month_year(line)
            if when:
                out.append(
                    _signal(
                        "krek",
                        "share_issue",
                        cc,
                        reg_id,
                        when,
                        LIST_RUN_AT,
                        title="Share issue registered (PRH trade register notice)",
                        url=REGISTRY_PAGES[cc].format(id=reg_id),
                        sensitive=True,
                    )
                )
    return out


@lru_cache(maxsize=1)
def _ledgers() -> dict[str, dict]:
    out = {}
    for ledger in seed.load("bridges").get("gap_ledger_examples", []):
        reg = ledger["company"]["registry"]
        out[f"{reg['country']}:{reg['id']}"] = ledger
    return out


def _gap_ledger(company_id: str) -> dict | None:
    return _ledgers().get(company_id)


# --------------------------------------------------------------------------- signals_cache.json
@lru_cache(maxsize=1)
def _cache_index() -> dict[str, dict]:
    index = {}
    for entry in seed.load("signals_cache")["companies"]:
        if entry.get("fi_business_id"):
            index[f"id:{entry['fi_business_id']}"] = entry
        index[f"name:{entry['name'].lower()}"] = entry
    return index


def _cached_signals(row: dict, company_id: str, cc: str | None, reg_id: str | None, add: _Collector) -> list[Signal]:
    index = _cache_index()
    entry = index.get(f"id:{reg_id}") if cc == "FI" and reg_id else None
    entry = entry or index.get(f"name:{row['name'].lower()}")
    if not entry:
        return []
    signals: list[Signal] = []
    ref_id = reg_id or slug(row["name"])
    notices = entry.get("prh_notices")
    if cc == "FI" and reg_id and notices is not None:
        signals += add.share_issues(notices, cc, reg_id)
    ted = entry.get("ted")
    if ted is not None and cc == "FI" and reg_id:
        signals += add.ted_awards(ted, cc, reg_id)
    crt = entry.get("crt")
    if crt and crt.get("ok"):
        signals += add.hostnames(crt["val"], cc or "XX", ref_id, _domain(row.get("website")) or entry.get("domain"))
    return signals


# --------------------------------------------------------------------------- the evidence collector
class _Collector:
    """Builds Evidence with ids that are stable for the same input ("FI:3652359-1#03")."""

    def __init__(
        self, company_id: str, out: list[Evidence], *, first_seen: datetime = PACK_AT, retrieved: datetime = PACK_AT
    ) -> None:
        self.company_id = company_id
        self.out = out
        self.first_seen = first_seen
        self.retrieved = retrieved

    def __call__(
        self,
        *,
        field: str,
        claim: str,
        tag: str,
        family: str,
        url: str | None = None,
        state: str = "fact",
        event_date: date | None = None,
        value: str | None = None,
        basis: str | None = None,
        why_unknown: str | None = None,
        next_check: NextCheck | None = None,
        retrieved: datetime | None = None,
    ) -> Evidence:
        e = Evidence(
            id=f"{self.company_id}#{len(self.out) + 1:02d}",
            company_id=self.company_id,
            field=FIELD_ALIASES.get(field, field),
            claim=claim,
            value=value,
            url=_human_url(url),
            event_date=event_date,
            first_seen_at=self.first_seen,
            retrieved_at=retrieved or self.retrieved,
            source_family=family,
            tag=tag,  # type: ignore[arg-type]
            state=state,  # type: ignore[arg-type]
            basis=basis,
            why_unknown=why_unknown,
            next_check=next_check,
        )
        self.out.append(e)
        return e

    def registry_facts(self, cc: str, reg_id: str, check: dict, founded: date | None) -> None:
        url = REGISTRY_PAGES[cc].format(id=reg_id)
        family = REGISTRY_SOURCE[cc]
        label = REGISTRY_LABEL[cc]
        checked = _at(check.get("checked"))
        if founded:
            self(
                field="founded",
                claim=f"Registered {founded:%d %b %Y} ({label})",
                value=founded.isoformat(),
                event_date=founded,
                url=url,
                tag="registry",
                family=family,
                retrieved=checked,
            )
        if check.get("municipality") or check.get("city"):
            place = (check.get("municipality") or check["city"]).title()
            self(
                field="registered_office",
                claim=f"Registered office: {place} ({label})",
                url=url,
                tag="registry",
                family=family,
                retrieved=checked,
            )
        if check.get("tol"):
            desc = f" ({check['tol_desc']})" if check.get("tol_desc") else ""
            self(
                field="industry_code",
                claim=f"Industry code {check['tol']}{desc} ({label})",
                value=check["tol"],
                url=url,
                tag="registry",
                family=family,
                retrieved=checked,
            )

    def founded_claim(self, founded: dict | str, website: str | None, domain: str | None) -> None:
        if isinstance(founded, dict):
            value, basis, url = founded.get("value"), founded.get("basis"), founded.get("source") or website
        else:
            value, basis, url = founded, None, website
        if not value or not approx_date(str(value)):
            return
        hedged = bool(SNIPPET_HINT.search(f"{value} {basis or ''}".lower()))
        day = parse_date(str(value)) if len(str(value)) == 10 else None  # a whole ISO day reads as prose dates do
        claim = f"Founded {f'{day:%d %b %Y}' if day else value}" + (f" ({basis})" if basis else "")
        self(
            field="founded",
            claim=claim,
            value=str(value),
            event_date=parse_date(str(value)),
            url=url,
            tag="snippet" if hedged else "read",
            state="assumption" if hedged else "fact",
            family=_family_for(url, domain, None, "read"),
        )

    def stage_signal(
        self, text: str, when: str | None, url: str | None, domain: str | None, cc: str | None, read_ok: bool
    ) -> None:
        lowered = text.lower()
        self_reported = bool(SELF_REPORTED.search(lowered)) or "(company site" in lowered or "(site" in lowered
        hedged = not self_reported and bool(HEDGES.search(lowered))
        url_domain = _domain(url)
        if url and "ted.europa.eu" in url:
            tag = "ted"
        elif url and any(h in url for h in REGISTRY_HOSTS):
            tag = "registry"
        elif SNIPPET_HINT.search(lowered):
            tag = "snippet"
        elif url or read_ok:
            tag = "read"
        else:
            tag = "dossier"
        own_site = self_reported or (domain is not None and url_domain == domain)
        family = _site_family(domain or url_domain) if own_site else _family_for(url, domain, cc, tag)
        self(
            field=_classify(lowered),
            claim=text,
            url=url,
            event_date=parse_date(when),
            value=when,
            tag=tag,
            state="assumption" if hedged or tag == "snippet" else "fact",
            family=family,
            basis="Hedged in the source (search summary, logo or filename only)" if hedged else None,
        )

    def list_line(self, line: str, sources: list[str], cc: str, reg_id: str, domain: str | None) -> None:
        lowered = line.lower()
        registry_url = REGISTRY_PAGES[cc].format(id=reg_id)
        ted_ids = re.findall(r"\d{5,6}-\d{4}", line)
        site = _site_family(domain)
        if lowered.startswith("founded"):
            return  # the founding date is recorded once, from the register
        if DISCOVERY_NOTE.search(lowered):
            return  # how the list run found the company is a note about our search, not a claim about it
        if ted_ids:
            url = next(
                (s for s in sources if ted_ids[0] in s), f"https://ted.europa.eu/en/notice/-/detail/{ted_ids[0]}"
            )
            self(field=_classify(lowered), claim=line, url=url, tag="ted", family="ted")
        elif "prh notices" in lowered or "share issue" in lowered:
            self(
                field="funding",
                claim=line,
                url=registry_url,
                tag="registry",
                family="prh_notices",
                event_date=_day_month_year(line),
            )
        elif "blocks scripted fetch" in lowered:
            self(
                field="product",
                claim=line,
                tag="read",
                state="unknown",
                family=site,
                why_unknown="The site blocks scripted reading",
                next_check=NextCheck(kind="public_check", how="Read the site by hand"),
            )
        elif "regulation clock" in lowered:
            self(field="market", claim=line, tag="dossier", family="regulation")
        elif "own business id" in lowered:
            self(field="identity", claim=line, url=f"https://{domain}/" if domain else None, tag="read", family=site)
        else:
            self(
                field=_classify(lowered, default="product"),
                claim=line,
                url=f"https://{domain}/" if domain else None,
                tag="read",
                family=site,
            )

    def ledger(self, ledger: dict, domain: str | None) -> None:
        for fact in ledger.get("facts", []):
            tag = fact["tag"]
            family = _site_family(domain) if tag == "site" else "prh"
            self(
                field=_classify(fact["claim"].lower(), default="product"),
                claim=fact["claim"],
                url=fact.get("url"),
                event_date=parse_date(fact.get("event_date")),
                tag=tag,
                family=family,
            )
        for item in ledger.get("assumptions", []):
            self(
                field="business_model",
                claim=item["claim"],
                tag="dossier",
                state="assumption",
                family="research_pack",
                basis=item.get("basis"),
                next_check=NextCheck(kind="ask_founder", question=item.get("how_to_test")),
            )
        for item in ledger.get("unknowns", []):
            check = item.get("next_check") or {}
            field = FIELD_ALIASES.get(item["field"], item["field"])
            self(
                field=field,
                claim=f"{field.replace('_', ' ').capitalize()}: unknown",
                tag="dossier",
                state="unknown",
                family="research_pack",
                why_unknown=item.get("why_unknown"),
                next_check=NextCheck(
                    kind=check.get("kind", "ask_founder"), how=check.get("how"), question=item.get("ask_founder")
                ),
            )
        for item in ledger.get("not_applicable", []):
            self(
                field=item["field"],
                claim=f"{item['field'].upper()}: not applicable",
                tag="dossier",
                state="not_applicable",
                family="research_pack",
                why_unknown=item.get("why"),
            )

    def share_issues(self, notices: dict, cc: str, reg_id: str) -> list[Signal]:
        url = REGISTRY_PAGES[cc].format(id=reg_id)
        if not notices.get("ok"):
            self(
                field="funding",
                claim="Share-issue notices: the PRH notices service did not answer",
                tag="registry",
                state="unknown",
                family="prh_notices",
                why_unknown="Source unavailable when checked",
                next_check=NextCheck(kind="public_check", how="PRH notices by business ID"),
            )
            return []
        # Notice rows overcount filings (one filing has many rows), so count distinct filing dates.
        dates = sorted(
            {
                parse_date(v["date"])
                for v in notices.get("val") or []
                if "ANTIP" in (v.get("codes") or []) and parse_date(v.get("date"))
            }
        )
        if not dates:
            self(
                field="funding",
                claim="No share-issue notice in the PRH trade register (checked 17 Oct 2026)",
                value="none_found",
                url=url,
                tag="registry",
                family="prh_notices",
                retrieved=SIGNALS_AT,
            )
            return []
        signals = []
        for when in dates:
            claim = f"Share issue registered {when:%d %b %Y} (PRH trade register; amount not public)"
            self(
                field="funding",
                claim=claim,
                event_date=when,
                url=url,
                tag="registry",
                family="prh_notices",
                retrieved=SIGNALS_AT,
            )
            signals.append(
                _signal(
                    "krek",
                    "share_issue",
                    cc,
                    reg_id,
                    when,
                    SIGNALS_AT,
                    url=url,
                    sensitive=True,
                    title="Share issue registered (PRH trade register notice)",
                )
            )
        return signals

    def ted_awards(self, ted: dict, cc: str, reg_id: str) -> list[Signal]:
        if not ted.get("ok"):
            return []
        notices = (ted.get("val") or {}).get("notices") or []
        if not notices:
            self(
                field="public_contracts",
                claim="No TED award found by business ID (checked 17 Oct 2026)",
                value="none_found",
                tag="ted",
                family="ted",
                retrieved=SIGNALS_AT,
                url="https://ted.europa.eu/en/search",
            )
            return []
        signals = []
        for n in notices:
            when = parse_date(n.get("date"))
            url = f"https://ted.europa.eu/en/notice/-/detail/{n['pub']}"
            self(
                field="public_contracts",
                claim=f"Public contract award: {n['title']} (buyer: {n['buyer']})",
                event_date=when,
                url=url,
                tag="ted",
                family="ted",
                retrieved=SIGNALS_AT,
            )
            signals.append(
                _signal(
                    "ted",
                    "award",
                    cc,
                    reg_id,
                    when,
                    SIGNALS_AT,
                    url=url,
                    title=n["title"],
                    payload={"buyer": n["buyer"], "notice": n["pub"]},
                )
            )
        return signals

    def hostnames(self, crt: dict, cc: str, ref_id: str, domain: str | None) -> list[Signal]:
        signals = []
        for host, seen in sorted((crt.get("xray_first_seen") or {}).items()):
            when = parse_date(seen)
            since = f"{when.day} {when:%b %Y}" if when else seen
            if host in LIVE_HOSTS:
                claim = f"Certificate log shows a live product hostname '{host}.{domain}' since {since} (crt.sh)"
            elif host in DEV_HOSTS:
                claim = f"Certificate log shows a development hostname '{host}.{domain}' since {since} (crt.sh)"
            else:
                continue
            self(
                field="product",
                claim=claim,
                value=host,
                event_date=when,
                url=f"https://crt.sh/?q={domain}",
                tag="read",
                family="crtsh",
                retrieved=SIGNALS_AT,
            )
            signals.append(
                _signal(
                    "crtsh",
                    "new_hostname",
                    cc,
                    ref_id,
                    when,
                    SIGNALS_AT,
                    url=f"https://crt.sh/?q={domain}",
                    title=f"{host}.{domain}",
                    payload={"host": host},
                )
            )
        return signals


def _renumber(extra: list[Evidence], company_id: str, start: int) -> list[Evidence]:
    return [e.model_copy(update={"id": f"{company_id}#{start + i + 1:02d}"}) for i, e in enumerate(extra)]


# --------------------------------------------------------------------------- small helpers
def _classify(text: str, default: str = "product") -> str:
    for pattern, field in FIELD_RULES:
        if re.search(pattern, text):
            return field
    return default


def _signal(
    source: str,
    kind: str,
    cc: str,
    ref_id: str,
    when: date | None,
    seen: datetime,
    *,
    url: str | None = None,
    title: str | None = None,
    sensitive: bool = False,
    payload: dict | None = None,
) -> Signal:
    sid = f"{source}:{cc}:{ref_id}:{kind}:{when.isoformat() if when else 'undated'}"
    if payload and payload.get("host"):
        sid += f":{payload['host']}"
    registry = REGISTRY_SOURCE.get(cc)
    return Signal(
        id=sid,
        source=source,
        type=kind,  # type: ignore[arg-type]
        entity_ref=EntityRef(registry=registry, id=ref_id) if registry else EntityRef(name=ref_id),
        event_date=when,
        first_seen_at=seen,
        url=url,
        hash=hashlib.sha256(f"{sid}|{title or ''}".encode("utf-8")).hexdigest()[:16],
        sensitivity="founder_sensitive" if sensitive else "public",
        title=title,
        payload=payload or {},
    )


def _founded_signal(cc: str | None, reg_id: str | None, founded: date, seen: datetime) -> Signal:
    source = REGISTRY_SOURCE.get(cc or "", "manual")
    return _signal(
        source,
        "newly_founded",
        cc or "XX",
        reg_id or "unknown",
        founded,
        seen,
        url=REGISTRY_PAGES[cc].format(id=reg_id) if cc in REGISTRY_PAGES and reg_id else None,
        title="Newly founded",
    )


def _recent(founded: date) -> bool:
    """Founding counts as a dated signal only within a year of the pack date."""
    return (PACK_AT.date() - founded).days <= 365


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url if "//" in url else f"https://{url}").netloc.lower().removeprefix("www.")
    # The pack sometimes holds a note ("not read in this run") where a URL would be.
    return host if re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", host) else None


RAW_REGISTRY_URL = (
    (re.compile(r"avoindata\.prh\.fi/opendata-ytj-api/v3/companies\?businessId=([\d-]+)"), "FI"),
    (re.compile(r"avoindata\.prh\.fi/opendata-registerednotices-api/v3/([\d-]+)"), "FI"),
    (re.compile(r"data\.brreg\.no/enhetsregisteret/api/enheter/(\d+)"), "NO"),
)


def _human_url(url: str | None) -> str | None:
    """Raw register API links become the register's own page, which a person can read."""
    for pattern, cc in RAW_REGISTRY_URL:
        m = pattern.search(url or "")
        if m:
            return REGISTRY_PAGES[cc].format(id=m.group(1))
    return url


def _site_family(domain: str | None) -> str:
    return f"site:{domain or 'unknown'}"


def _family_for(url: str | None, domain: str | None, cc: str | None, tag: str) -> str:
    url_domain = _domain(url)
    if tag == "registry" and cc in REGISTRY_SOURCE:
        return REGISTRY_SOURCE[cc]
    if tag == "ted":
        return "ted"
    if url_domain and url_domain == domain:
        return f"site:{domain}"
    return url_domain or "research_pack"


def _first_url(row: dict, *, exclude: tuple[str, ...]) -> str | None:
    return next((u for u in row.get("evidence_urls") or [] if not any(h in u for h in exclude)), None)


def _names(*names: str | None) -> list[str]:
    out: list[str] = []
    for n in names:
        if n and ";" not in n and "(" not in n and n not in out:
            out.append(n)
    return out or [next(n for n in names if n)]


def _legal_form(form: str | None, name: str) -> str | None:
    if form:
        key = form.lower()
        if key in REGISTER_FORMS or key in LEGAL_FORMS:
            return REGISTER_FORMS.get(key) or LEGAL_FORMS[key]
    words = re.findall(r"[\w/.]+", name.lower())
    # Bilingual Finnish names read "Oy X Ab": the first word decides; "X AB (publ)" ends in its form.
    for word in words[:1] + words[-1:]:
        if word in LEGAL_FORMS:
            return LEGAL_FORMS[word]
    return None


def _is_natural_person(form: str | None, legal_name: str | None) -> bool:
    text = f"{form or ''} {legal_name or ''}".lower()
    return any(re.search(rf"\b{f}\b", text) for f in NATURAL_PERSON_FORMS)


def _at(day: str | None) -> datetime:
    parsed = parse_date(day)
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=timezone.utc) if parsed else PACK_AT


_MONTHS = {
    m: i
    for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), start=1)
}


def _day_month_year(text: str) -> date | None:
    """'20 Aug 2026' -> date(2026, 8, 20); month-only mentions return None."""
    m = re.search(r"\b(\d{1,2}) ([A-Za-z]{3})[a-z]* (\d{4})\b", text)
    if not m or m.group(2).lower() not in _MONTHS:
        return None
    return date(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
