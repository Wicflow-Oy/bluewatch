"""Won it before, open again: a TED award by winner business ID x an open tender in the same class."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bluewatch import seed
from bluewatch.bridges.common import fmt_day, fmt_month, make_bridge, today_or_default
from bluewatch.bridges.companies import COUNTRY_CODES, DemoCompany, by_registry_id
from bluewatch.models import Bridge, BridgeEvidence, BridgeParty

# CPV 2008 labels as TED prints them in titles ("Finland – Boats – ..."). Award records carry the
# label but not the code; codes were checked against recorded notices that carry both, except
# Fire vessels, which comes from the CPV 2008 list.
CPV_BY_LABEL = {
    "Ships and boats": "34500000",
    "Fire vessels": "34513650",
    "Rescue vessels": "34513700",
    "Floating structures": "34515000",
    "Marker buoys": "34515100",
    "Boats": "34520000",
    "Specialised boats": "34521000",
    "Lifeboats": "34521400",
    "Navigation equipment": "34933000",
    "Ice-breaking services": "63726200",
}
ISO3 = {"FIN": "FI", "SWE": "SE", "NOR": "NO", "DNK": "DK", "EST": "EE", "LVA": "LV", "LTU": "LT"}
AWARD_WINDOW_YEARS = 2  # "won before" means an award published this year or in the two before
# Procurement boilerplate and words already covered by the class token, as 5-letter stems.
STOP_STEMS = {
    "hanki",
    "ilmoi",
    "jalki",
    "jälki",
    "tulok",
    "keske",
    "sisäl",
    "optio",
    "vuosi",
    "hyvin",
    "kilpa",
    "palve",
    "luokk",
    "luoka",
    "klass",
    "class",
    "uppha",
    "procu",
    "frame",
    "agree",
    "ramav",
    "contr",
    "servi",
}


@dataclass(frozen=True)
class Award:
    pub: str
    when: date | None
    buyer: str
    country: str | None
    label: str
    text: str

    @property
    def cpv(self) -> str | None:
        return CPV_BY_LABEL.get(self.label)

    @property
    def year(self) -> int:
        return self.when.year if self.when else int(self.pub.rsplit("-", 1)[1])


def ted_url(pub: str) -> str:
    return f"https://ted.europa.eu/en/notice/-/detail/{pub}"


def title_terms(text: str) -> set[str]:
    """Distinctive title terms: vessel-class codes ('C-luokka' -> 'class c') and 5-letter stems."""
    lowered = text.lower()
    terms = {f"class {code}" for code in re.findall(r"\b([a-z0-9]{1,3})-(?:luok|klass|class)", lowered)}
    stems = {word[:5] for word in re.findall(r"[^\W\d_]{5,}", lowered)}
    return terms | (stems - STOP_STEMS)


def shared_words(award_text: str, tender_title: str) -> list[str]:
    """The shared terms as words a reader recognises: 'C-luokka', 'Öljyntorjunta'."""
    shared = title_terms(award_text) & title_terms(tender_title)
    words = re.findall(r"[0-9a-zA-Z]{1,3}-(?:luok|klass|class)\w*|[^\W\d_]{5,}", award_text)
    picked = [w for w in words if w[:5].lower() in shared or f"class {w.split('-')[0].lower()}" in shared]
    return list(dict.fromkeys(picked))


def _award(pub: str, when: date | None, buyer: str, title: str) -> Award | None:
    parts = title.split(" – ")
    if len(parts) < 3:
        return None
    return Award(pub, when, buyer, COUNTRY_CODES.get(parts[0]), parts[1], " – ".join(parts[2:]))


def awards_by_company() -> dict[str, list[Award]]:
    """TED awards per demo company, from the per-company winner query and the Finnish awards probe."""
    found: dict[str, dict[str, Award]] = {}
    for row in seed.load("signals_cache")["companies"]:
        company = by_registry_id(row["fi_business_id"]) if row.get("fi_business_id") else None
        for notice in ((row.get("ted") or {}).get("val") or {}).get("notices", []):
            award = _award(notice["pub"], date.fromisoformat(notice["date"]), notice["buyer"], notice["title"])
            if company and award:
                found.setdefault(company.company_id, {})[award.pub] = award
    for notice in seed.fixture("sources/ted_fi_awards_probe.json")["notices"]:
        titles, buyers = notice["notice-title"], notice["buyer-name"]
        title = titles.get("eng") or titles.get("fin") or ""
        buyer = next(iter(buyers.values()))[0]
        for winner_id in notice.get("winner-identifier") or []:
            company = by_registry_id(winner_id)
            award = _award(notice["publication-number"], None, buyer, title)
            if company and award:
                found.setdefault(company.company_id, {}).setdefault(award.pub, award)
    return {key: sorted(awards.values(), key=lambda a: a.pub) for key, awards in found.items()}


def open_tenders(today: date) -> list[dict]:
    """Recorded open tenders whose deadline has not passed, with the deadline as a date."""
    tenders = []
    for tender in seed.fixture("sources/ted_open_tenders_blue_nordic_baltic.json")["open"]:
        future = [d for d in map(date.fromisoformat, tender["deadlines"]) if d >= today]
        if future:
            tenders.append({**tender, "deadline": min(future), "countries": {ISO3[c] for c in tender["country"]}})
    return tenders


def join(award: Award, tender: dict) -> str | None:
    """Exact: same CPV group and two shared title terms. Partial: same 5-digit CPV class only."""
    if not award.cpv:
        return None
    if (
        any(c[:3] == award.cpv[:3] for c in tender["cpv"])
        and len(title_terms(award.text) & title_terms(tender["title"])) >= 2
    ):
        return "exact"
    if any(c[:5] == award.cpv[:5] for c in tender["cpv"]):
        return "partial"
    return None


def _award_evidence(award: Award) -> BridgeEvidence:
    when = fmt_month(award.when) if award.when else str(award.year)
    return BridgeEvidence(
        claim=f"TED award: {award.label}, {award.text} ({award.buyer}, {when})",
        url=ted_url(award.pub),
        date=award.when.isoformat() if award.when else str(award.year),
        tag="ted",
    )


def _tender_evidence(tender: dict) -> BridgeEvidence:
    return BridgeEvidence(
        claim=f"Open tender: {tender['title']}",
        url=tender["url"],
        date=tender["date"],
        deadline=tender["deadline"],
        tag="ted",
    )


def _bridge(company: DemoCompany, buyer: str, matches: list[tuple[Award, dict]], level: str) -> Bridge:
    awards = sorted({a.pub: a for a, _ in matches}.values(), key=lambda a: a.pub)
    tenders = sorted({t["pub"]: t for _, t in matches}.values(), key=lambda t: t["deadline"])
    days = sorted({t["deadline"] for t in tenders})
    deadlines = f"deadline{'s' if len(days) > 1 else ''} {' and '.join(fmt_day(d) for d in days)}"
    latest = max(awards, key=lambda a: (a.year, a.when or date.min))
    won = fmt_month(latest.when) if latest.when else str(latest.year)
    if level == "exact":
        terms = ", ".join(shared_words(latest.text, tenders[0]["title"]))
        reason = f"Won '{latest.text}' from {latest.buyer} ({won}); {buyer} now tenders the same class ({terms})"
        action = f"Send the {buyer} tender with the {won} award as the reference ({deadlines})"
        caveat = None
    else:
        count = f"{len(awards)} public award{'s' if len(awards) > 1 else ''}"
        reason = f"{count} in CPV class {latest.label} ({latest.cpv}); {buyer} tenders the same CPV class"
        action = f"Check which {buyer} lot fits the company's products ({deadlines})"
        caveat = "Lot fit not checked against the tender documents"
    return make_bridge(
        type="won_before_open_again",
        company=company.party(),
        counterparty=BridgeParty(name=buyer, kind="public_buyer", country=next(iter(tenders[0]["countries"]))),
        reason=reason,
        evidence_company=[_award_evidence(a) for a in awards],
        evidence_counterparty=[_tender_evidence(t) for t in tenders],
        join=level,
        deadline=tenders[0]["deadline"],
        action=action,
        caveat=caveat,
        anonymised_name=company.anonymised_name(),
    )


def won_before_open_again(*, today: date | None = None) -> list[Bridge]:
    today = today_or_default(today)
    tenders = open_tenders(today)
    bridges = []
    for company_id, awards in awards_by_company().items():
        company = by_registry_id(company_id.split(":", 1)[1])
        recent = [a for a in awards if today.year - a.year <= AWARD_WINDOW_YEARS]
        by_buyer: dict[str, list[tuple[Award, dict, str]]] = {}
        for award in recent:
            for tender in tenders:
                level = join(award, tender)
                if level and award.country in tender["countries"]:  # only where it has won before
                    by_buyer.setdefault(tender["buyer"], []).append((award, tender, level))
        for buyer, found in sorted(by_buyer.items()):
            best = "exact" if any(level == "exact" for *_, level in found) else "partial"
            matches = [(a, t) for a, t, level in found if level == best]
            bridges.append(_bridge(company, buyer, matches, best))
    return bridges
