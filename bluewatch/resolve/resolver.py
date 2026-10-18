"""Which registered company is meant, in a strict order, with one of five honest outcomes.

Order: registry ID with a valid checksum → VAT number → registry ID on
the company's own site → the registry's website field → exact whole-word name → candidates for a
person to pick → unresolved.

Only an identifier can make a company "resolved". "probable" needs an exact name plus an independent
link (the registry naming the site we read), or an ID given with a related but differing name. An ID
given with a name that shares no word with the registered one is "unconfirmed". Everything weaker
is "unconfirmed" or "ambiguous" with the candidates shown, because a wrong company is worse than a
question: a naive name search picks the wrong one for names like these (Kelluu → Kelluu Clothing,
Wolt → Woltter, Seaber → Seaberry).

Sole traders are natural persons: they are counted, so a name shared with them stays ambiguous, but
never listed, ranked or contacted.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from bluewatch.models import Candidate, Company, Registry, Resolution, ResolutionState, Vertical
from bluewatch.resolve.ids import normalise_id, normalise_vat, parse_token, vat_to_registry_id
from bluewatch.resolve.names import MatchLevel, domain_of, match_level, same_site

REGISTRIES = {"FI": "PRH", "NO": "Brreg", "EE": "RIK"}
ID_LABELS = {
    "FI": "business ID",
    "NO": "organisation number",
    "EE": "registry code",
    "SE": "organisation number",
    "DK": "CVR number",
}
_LEVEL_RANK = {"exact": 3, "partial": 2, "near": 1, "none": 0}
_MAX_LISTED = 8


@dataclass
class _Entry:
    """One registry record and every name it goes by (registered name plus auxiliary names)."""

    registry: Registry
    names: list[str] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, str]:
        r = self.registry
        return r.country.upper(), normalise_id(r.country, r.id) or r.id

    @property
    def label(self) -> str:
        return f"{self.registry.name or 'unnamed record'} ({self.registry.id})"


def _entries(candidates: Iterable[Registry | Candidate]) -> list[_Entry]:
    # A Candidate can carry an auxiliary name (PRH names[].type 3) for the record it wraps.
    by_key: dict[tuple[str, str], _Entry] = {}
    for item in candidates:
        registry, extra = (item.registry, item.name) if isinstance(item, Candidate) else (item, None)
        entry = _Entry(registry)
        entry = by_key.setdefault(entry.key, entry)
        for n in (registry.name, extra):
            if n and n not in entry.names:
                entry.names.append(n)
    return list(by_key.values())


def _best(query: str, entry: _Entry) -> tuple[MatchLevel, str]:
    """The best match level and the name (registered or auxiliary) that achieved it."""
    scored = [(match_level(query, n), n) for n in entry.names] or [("none", entry.registry.id)]
    return max(scored, key=lambda pair: _LEVEL_RANK[pair[0]])


def _level(query: str, entry: _Entry) -> MatchLevel:
    return _best(query, entry)[0]


def resolve(
    name: str,
    *,
    country: str,
    registry_id: str | None = None,
    domain: str | None = None,
    vat_id: str | None = None,
    page_ids: Iterable[str] = (),
    candidates: Iterable[Registry | Candidate] = (),
    site_note: str | None = None,
) -> Resolution:
    """Resolve a company name to a registry record.

    domain: the company site that was actually read; pass None when it could not be fetched and say
        why in site_note ("TLS certificate fails", "HTTP 429").
    page_ids: tokens found on that site (bluewatch.resolve.ids.find_ids).
    candidates: registry records from a name search or lookup, optionally as Candidates carrying an
        auxiliary name. For resolved and probable results, candidates[0] is the chosen record.
    """
    country = (country or "").upper()
    name = (name or "").strip()
    entries = _entries(candidates)
    label = ID_LABELS.get(country, "registry ID")
    site = domain_of(domain)
    notes: list[str] = []
    if site_note:
        notes.append(f"Site: {site_note}.")

    def finish(state: ResolutionState, reason: str, chosen: _Entry | None = None) -> Resolution:
        listed = _listing(name, country, state, chosen, entries)
        return Resolution(state=state, reason=" ".join([reason, *notes]), candidates=listed)

    def by_id(nid: str, how: str) -> Resolution:
        hit = next((e for e in entries if e.key == (country, nid)), None)
        if hit is None:
            stub = _Entry(Registry(country=country, id=nid))
            return finish("unconfirmed", f"{how}, but its registry record is not loaded: look it up.", stub)
        if hit.registry.natural_person:
            return Resolution(
                state="unresolved",
                reason="That number belongs to a sole trader (a natural person), who is never ranked or contacted.",
            )
        level = "exact" if not name or normalise_id(country, name) == nid else _level(name, hit)
        if level == "exact":
            return finish("resolved", f"{how} and matches {hit.label}.", hit)
        # An ID proves which record it is, not that the record is the company meant. With no word in
        # common, the pairing itself is the open question (Edilm's ID belongs to Atlan Studio Oy), so it
        # is treated like an ID found on someone else's site: shown, never accepted.
        if level == "none":
            return finish(
                "unconfirmed",
                f"{how}, but it belongs to {hit.label}, whose name does not match '{name}'. "
                "It may be a brand of that company: confirm before using it.",
                hit,
            )
        return finish("probable", f"{how}, but the registered name {hit.label} differs from '{name}': confirm.", hit)

    # 1. Registry ID with a valid checksum.
    if registry_id:
        nid = normalise_id(country, registry_id)
        if nid:
            return by_id(nid, f"The {label} {nid} passes the checksum")
        notes.append(f"'{registry_id}' fails the {country} {label} checksum, so it was not used.")

    # 2. VAT number (Finnish and Norwegian VAT numbers contain the registry ID).
    if vat_id:
        vat = normalise_vat(vat_id)
        mapped = vat_to_registry_id(vat) if vat else None
        if mapped and mapped[0] == country:
            return by_id(mapped[1], f"VAT number {vat} gives {label} {mapped[1]}")
        if vat:
            notes.append(f"VAT number {vat} cannot be linked to a {country} registry record here; VIES can check it.")
        else:
            notes.append(f"'{vat_id}' is not a valid VAT number, so it was not used.")

    # 3. A registry ID on the company's own site says whose site it is; the name decides whether that
    #    is the company asked for (Edilm's page is Atlan Studio Oy's site).
    site_attached = bool(site)
    on_site = {parsed for t in page_ids if (parsed := parse_token(t))}
    shown = site or "The company's site"
    if on_site:
        owner = next((e for e in entries if e.key in on_site and not e.registry.natural_person), None)
        if owner and _level(name, owner) == "exact":
            return finish("resolved", f"{shown} shows the {label} of {owner.label}.", owner)
        if owner:
            return finish(
                "unconfirmed",
                f"{shown} shows the {label} of {owner.label}, whose name does not match "
                f"'{name}'. It may be a brand of that company: confirm before using it.",
                owner,
            )
        local_ids = sorted(i for c, i in on_site if c == country)
        if local_ids and not entries:
            stub = _Entry(Registry(country=country, id=local_ids[0]))
            return finish(
                "unconfirmed",
                f"{shown} shows {label} {local_ids[0]}, whose registry record is not "
                "loaded: look it up to confirm the name.",
                stub,
            )
        if local_ids:
            notes.append(
                f"{shown} shows {label} {', '.join(local_ids)}, which is none of the registry candidates, "
                "so the site is not attached."
            )
            site_attached = False

    # 4. The registry's website field names the site we read.
    if site and site_attached:
        for owner in sorted(
            (e for e in entries if same_site(e.registry.website, site)),
            key=lambda e: e.registry.country.upper() != country,
        ):
            if owner.registry.natural_person:
                continue
            if owner.registry.country.upper() == country and _level(name, owner) == "exact":
                return finish(
                    "probable",
                    f"The registry lists {site} as the website of {owner.label}, and the name matches: confirm.",
                    owner,
                )
            notes.append(
                f"The registry lists {site} as the website of {owner.label}, not of a {country} company "
                f"named '{name}', so the site is not used."
            )
            break
        else:
            notes.append(
                f"{site} is not linked to any candidate (no registry ID on the page, and no registry record lists it)."
            )

    # 5–6. Whole-word name match, then the candidates for a person to pick.
    if not name:
        return Resolution(state="unresolved", reason=" ".join(notes) or "No company name, website or ID to match.")
    local = [e for e in entries if e.registry.country.upper() == country]
    levels = {e.key: _level(name, e) for e in local}
    exact = [e for e in local if levels[e.key] == "exact" and not e.registry.natural_person]
    partial = [e for e in local if levels[e.key] == "partial" and not e.registry.natural_person]
    people = [e for e in local if levels[e.key] in ("exact", "partial") and e.registry.natural_person]
    if people:
        notes.append(f"{len(people)} sole trader(s) with this name are natural persons and are not listed.")
    namesakes = len(exact) + len(partial) + len(people)
    if namesakes == 1 and exact:
        return finish(
            "unconfirmed",
            f"One registry company has this name, {exact[0].label}, but nothing links it "
            "to a site yet: confirm, or paste its website.",
            exact[0],
        )
    if namesakes == 1 and partial:
        return finish(
            "unconfirmed",
            f"The only registry name containing '{name}' is {partial[0].label}: confirm "
            "it is the company meant, or paste its website.",
            partial[0],
        )
    if namesakes > 1:
        return finish(
            "ambiguous",
            f"{namesakes} registry entries carry the name '{name}': pick one, or paste the company's website.",
        )
    if country not in REGISTRIES:
        return finish(
            "unresolved",
            f"There is no keyless {country or 'unknown-country'} registry, and no VAT "
            "number from the company's site links it to one.",
        )
    near = [e for e in local if levels[e.key] == "near"]
    if near:
        return finish(
            "unresolved",
            f"No {REGISTRIES[country]} company is called '{name}'; names that only "
            "contain it inside a longer word are different names.",
        )
    return finish("unresolved", f"No {REGISTRIES[country]} company matches '{name}'.")


def _listing(
    name: str, country: str, state: ResolutionState, chosen: _Entry | None, entries: list[_Entry]
) -> list[Candidate]:
    """Chosen record first, then same-name, partial-name, other-country and near-name records."""
    listed: list[tuple[float, Candidate]] = []
    if chosen is not None:
        score = {"resolved": 1.0, "probable": 0.9}.get(state, 0.6)
        listed.append(
            (
                2.0,
                Candidate(
                    name=_best(name, chosen)[1], registry=chosen.registry, score=score, reason=f"chosen: {state}"
                ),
            )
        )
    for e in entries:
        if e.registry.natural_person or (chosen is not None and e.key == chosen.key):
            continue
        level = _level(name, e)
        if e.registry.country.upper() != country:
            if level in ("exact", "partial"):
                listed.append((0.3, _candidate(e, 0.3, f"separate entity in {e.registry.country}; not merged")))
        elif level == "exact":
            listed.append((0.8, _candidate(e, 0.8, "same name")))
        elif level == "partial":
            listed.append((0.5, _candidate(e, 0.5, "the name has extra words")))
        elif level == "near":
            listed.append((0.0, _candidate(e, 0.0, f"a different word, not '{name}'")))
    listed.sort(key=lambda pair: -pair[0])
    return [c for _, c in listed[:_MAX_LISTED]]


def _candidate(entry: _Entry, score: float, reason: str) -> Candidate:
    return Candidate(name=entry.registry.name or entry.registry.id, registry=entry.registry, score=score, reason=reason)


def company_from(
    registry: Registry, resolution: Resolution, *, domain: str | None = None, vertical: Vertical | None = None
) -> Company:
    """A Company for a resolved registry record; id like 'FI:3652359-1'. Natural persons are refused."""
    if registry.natural_person:
        raise ValueError("Sole traders are natural persons and are never turned into companies.")
    nid = normalise_id(registry.country, registry.id) or registry.id
    names = [registry.name] if registry.name else []
    for c in resolution.candidates:
        if c.registry.id == registry.id and c.name not in names and c.name != registry.id:
            names.append(c.name)
    return Company(
        id=f"{registry.country.upper()}:{nid}",
        names=names or [nid],
        registry=registry,
        domain=domain_of(domain or registry.website),
        vertical=vertical,
        resolution=resolution,
    )
