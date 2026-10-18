"""Find a company by name in the Finnish, Norwegian and Estonian registers and in the precomputed set.

What a visitor types goes only to the registers it searches; it is never stored, logged or cached. Sole traders
are people and never appear (the registers' loose matching means they can't even be counted honestly). A register
that can't answer is reported as unavailable, so an empty list never hides a failure.

A company is found by any of its names (a former name shows as "formerly ..."), and the list puts what a scout is
looking for first: trading companies before closed ones, and businesses before associations, foundations and
housing companies.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from types import ModuleType
from typing import Literal

from pydantic import BaseModel

from bluewatch.models import Company, ConnectorResult, Registry, SourceStatus
from bluewatch.sources import brreg, prh, rik, status
from bluewatch.sources.common import NamedRecord, is_closed, name_rank

SearchCountry = Literal["FI", "NO", "EE"]
REGISTERS: dict[str, ModuleType] = {"FI": prh, "NO": brreg, "EE": rik}
MIN_LENGTH = 3
MAX_LENGTH = 100
MAX_CANDIDATES = 12
# Forms that are not businesses a scout looks for, by country: they stay findable but come last.
NOT_VENTURES = {
    "FI": {"Housing corporation", "Mutual real estate limited company", "Non-profit association", "Foundation"},
    "NO": {"FLI", "STI", "BRL", "BBL", "ESEK", "SAM", "KOMM", "KIRK", "ORGL", "PERS"},
    "EE": {"MTÜ", "SA"},
}
FOREIGN_BRANCH, FOREIGN_ENTITY = "NUF", "UTLA"  # Brreg lists a foreign company's Norwegian branch twice


class SearchCandidate(BaseModel):
    country: str
    business_id: str  # "" for a precomputed company that has no register ID yet
    name: str
    registered: date | None = None
    form: str | None = None
    municipality: str | None = None
    status: str | None = None
    closed: bool = False  # the register lists it as ceased, deleted, bankrupt or being wound up
    formerly: str | None = None  # the former name the search matched
    also_known_as: str | None = None  # another name in use (parallel or trading name) the search matched
    company_id: str | None = None  # set when the company is in the precomputed set


class SearchResult(BaseModel):
    candidates: list[SearchCandidate]
    sources: list[SourceStatus]  # one per register searched
    more: bool = False  # more matches than shown: typing more of the name narrows them


def clean_query(raw: str) -> str:
    text = " ".join((raw or "").split())
    if len(text) < MIN_LENGTH:
        raise ValueError(f"Type at least {MIN_LENGTH} letters of the company name.")
    if len(text) > MAX_LENGTH:
        raise ValueError(f"A company name has at most {MAX_LENGTH} characters.")
    return text


@dataclass(frozen=True)
class _Match:
    rank: int
    formerly: str | None = None
    also_known_as: str | None = None


def _match(query: str, name: str | None, former: list[str], other: list[str]) -> _Match | None:
    """The closest of a company's names; on a tie its own name, then a former name."""
    names = [(name, {}), *((f, {"formerly": f}) for f in former), *((o, {"also_known_as": o}) for o in other)]
    ranked = [(rank, i, how) for i, (n, how) in enumerate(names) if (rank := name_rank(query, n)) is not None]
    if not ranked:
        return None
    rank, _, how = min(ranked)
    return _Match(rank, **how)


def _candidate(registry: Registry, name: str, match: _Match, company_id: str | None) -> tuple[SearchCandidate, int]:
    candidate = SearchCandidate(
        country=registry.country,
        business_id=registry.id,
        name=name,
        registered=registry.founded,
        form=registry.form,
        municipality=registry.municipality,
        status=registry.status,
        closed=is_closed(registry.status),
        formerly=match.formerly,
        also_known_as=match.also_known_as,
        company_id=company_id,
    )
    return candidate, match.rank


def _from_register(query: str, record: Registry, company_id: str | None) -> tuple[SearchCandidate, int] | None:
    former, other = (record.former_names, record.other_names) if isinstance(record, NamedRecord) else ([], [])
    match = _match(query, record.name, former, other)
    return None if match is None else _candidate(record, record.name or record.id, match, company_id)


def _from_precomputed(query: str, company: Company) -> tuple[SearchCandidate, int] | None:
    match = _match(query, company.names[0], [], company.names[1:])
    return None if match is None else _candidate(company.registry, company.names[0], match, company.id)


def _order(candidate: SearchCandidate, rank: int) -> tuple[bool, bool, int, bool, int, str]:
    """Trading before closed, businesses before associations and the like, then the closest name; on a tie, an
    assessed company first, then the shorter name."""
    not_venture = candidate.form in NOT_VENTURES.get(candidate.country, ())
    return (
        candidate.closed,
        not_venture,
        rank,
        candidate.company_id is None,
        len(candidate.name),
        candidate.name.casefold(),
    )


def _drop_double_branches(found: dict[str, tuple[SearchCandidate, int]]) -> None:
    """A foreign company's Norwegian branch (NUF) also appears as a foreign entity (UTLA); keep the branch."""
    branches = {c.name.casefold() for c, _ in found.values() if c.form == FOREIGN_BRANCH}
    for key, (candidate, _) in list(found.items()):
        if candidate.form == FOREIGN_ENTITY and candidate.name.casefold() in branches:
            del found[key]


def _search_register(country: str, query: str) -> ConnectorResult:
    register = REGISTERS[country]
    return status.run(register.SOURCE, lambda: register.search_result(query))


def search(raw_query: str, country: SearchCountry | None = None) -> SearchResult:
    """Best matches first, from every register asked plus the precomputed set; at most MAX_CANDIDATES."""
    from bluewatch import demo

    query = clean_query(raw_query)
    countries = [country] if country else list(REGISTERS)
    with ThreadPoolExecutor(max_workers=len(countries)) as pool:  # the registers answer in parallel
        results = list(pool.map(lambda c: _search_register(c, query), countries))

    precomputed = demo.build().companies
    found: dict[str, tuple[SearchCandidate, int]] = {}
    for record in (r for result in results for r in result.records if not r.natural_person):
        key = f"{record.country}:{record.id}"
        if hit := _from_register(query, record, key if key in precomputed else None):
            found[key] = hit
    for company in precomputed.values():
        in_scope = country is None or company.registry.country == country
        if in_scope and company.id not in found and (hit := _from_precomputed(query, company)):
            found[company.id] = hit
    _drop_double_branches(found)

    ranked = [c for c, _ in sorted(found.values(), key=lambda hit: _order(*hit))]
    return SearchResult(
        candidates=ranked[:MAX_CANDIDATES], sources=[r.status for r in results], more=len(ranked) > MAX_CANDIDATES
    )
