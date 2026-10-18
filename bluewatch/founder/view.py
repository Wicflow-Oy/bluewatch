"""The founder view: the same rules, flipped. A founder enters a business ID (or a short profile) and
sees every grant and programme tiered with its deciding rule, the investors to shortlist and the next
30 days.

Everything here is a pure function of its arguments: nothing is stored, sent or logged, so the public
app can run it for any business ID a visitor types. A sole trader is a private person: the view for
one shows no details at all.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from bluewatch.config import settings
from bluewatch.models import (
    Assessment,
    Company,
    Evidence,
    FounderProfile,
    FounderTier,
    FounderView,
    InvestorMatch,
    NextStep,
    Opportunity,
    Registry,
    Resolution,
    ShareConsent,
)
from bluewatch.rules.assess import assess
from bluewatch.rules.eligibility import Applicant, applicant_from_company, applicant_from_profile
from bluewatch.rules.funding import evaluate as evaluate_instrument
from bluewatch.rules.funding import instruments, kind_of, opportunity, tiers_for
from bluewatch.rules.investors import match
from bluewatch.rules.presets import load_preset
from bluewatch.rules.version import rules_version
from bluewatch.sources.common import is_closed

NATURAL_PERSON_ID = "natural-person"
CONSENT_TEXT_VERSION = "share-v1-2026-10-17"
CONSENT_TEXT = (
    "Share my business ID or profile, and these tier results, with A'Pelago so they can contact my "
    "company about programmes. I can withdraw this at any time."
)
SHARE_SCOPES = ("business_id", "profile", "tier_results")
LIVE_TIERS = ("certain", "likely", "possible")

# Industry codes (TOL 2008 / NACE, dots removed) as readable themes, longest prefix first.
INDUSTRY_THEMES = (
    ("1020", "fish processing"),
    ("3011", "shipbuilding"),
    ("3315", "ship repair"),
    ("5222", "port and water transport services"),
    ("03", "fishing and aquaculture"),
    ("50", "water transport"),
    ("36", "water supply"),
    ("37", "wastewater"),
    ("62", "software"),
    ("71", "engineering and technical consultancy"),
    ("72", "research and development"),
)


def profile_from_registry(registry: Registry) -> FounderProfile:
    """A profile from register facts only. Missing founding date or industry code stay unknown."""
    if registry.natural_person:
        return FounderProfile(
            id=NATURAL_PERSON_ID, country=registry.country, org_type="individual_founding", source="register"
        )
    return FounderProfile(
        id=f"{registry.country}:{registry.id}",
        business_id=registry.id,
        country=registry.country,
        name=registry.name,
        founded=registry.founded,
        themes=_industry_themes(registry.industry_code),
        source="register",
    )


def evaluate(
    profile: FounderProfile,
    today: date | None = None,
    *,
    registry: Registry | None = None,
    researched: tuple[Company, Assessment] | None = None,
    preset: str = "blue",
) -> FounderView:
    """Tiers, programmes, investors and the next 30 days for one profile. Pass the register record as
    `registry` when there is one: its industry code, legal form and office decide some rules. Pass the
    company and its assessment as `researched` when the company already has a card: the rules then read
    the same researched facts as the card and the funding page, so a call gets one verdict everywhere. A
    company the register lists as closed gets its profile only (the lookup says it no longer trades)."""
    today = today or settings().today
    known = researched[0].registry if researched else registry
    if profile.id == NATURAL_PERSON_ID or (known and is_closed(known.status)):
        return FounderView(profile=profile, rules_version=rules_version())
    if researched:
        company, assessment = researched
        applicant = applicant_from_company(company, assessment.levels, today)
    else:
        company = as_company(profile, registry)
        assessment = assess(
            company,
            profile_evidence(profile, company),
            preset=preset,
            now=datetime(today.year, today.month, today.day, 12, tzinfo=timezone.utc),
        )
        applicant = applicant_from_profile(profile, today, registry)
    tiers = tiers_for(applicant, today=today)
    investors = match(company, assessment, mode="apelago", preset=preset, limit=8, today=today)
    return FounderView(
        profile=profile,
        tiers=tiers,
        programmes=_programmes(profile.id, applicant, today, preset),
        investors=investors,
        next_30_days=_next_30_days(profile, tiers, investors, today),
        rules_version=rules_version(),
    )


def record_consent(profile_id: str, scope: list[str], *, now: datetime | None = None) -> ShareConsent:
    """Builds the consent record only; storing it and notifying A'Pelago is the caller's job (and is off
    in the public demo). profile_id is accepted for the caller's audit line and is not kept here."""
    unknown = [s for s in scope if s not in SHARE_SCOPES]
    if not scope or unknown:
        raise ValueError(f"scope must name what is shared, from {', '.join(SHARE_SCOPES)}")
    return ShareConsent(
        given=True,
        scope=list(scope),
        consent_text_version=CONSENT_TEXT_VERSION,
        given_at=now or datetime.now(timezone.utc),
    )


def _industry_themes(code: str | None) -> list[str]:
    digits = (code or "").replace(".", "")
    return [theme for prefix, theme in INDUSTRY_THEMES if digits.startswith(prefix)][:1]


def as_company(profile: FounderProfile, registry: Registry | None) -> Company:
    reg = registry or Registry(
        country=profile.country, id=profile.business_id or "", name=profile.name, founded=profile.founded
    )
    state = "resolved" if profile.source == "register" else "unconfirmed"
    return Company(
        id=profile.id,
        names=[profile.name or "Your company"],
        registry=reg,
        resolution=Resolution(state=state, reason=f"Founder view ({profile.source})"),
        one_liner="; ".join(profile.themes) or None,
        tags=["founder_view"],
    )


def profile_evidence(profile: FounderProfile, company: Company) -> list[Evidence]:
    """The profile's own facts as evidence: register facts are registry-tagged, self-reported ones are
    the company's own statement."""
    tag = "registry" if profile.source == "register" else "company_reply"
    out = []
    if profile.founded:
        out.append(
            Evidence(
                id=f"{profile.id}#founded",
                company_id=profile.id,
                field="founded",
                claim=f"Founded {profile.founded:%d %b %Y}",
                value=profile.founded.isoformat(),
                event_date=profile.founded,
                source_family="founder_profile",
                tag=tag,
            )
        )
    if profile.themes:
        out.append(
            Evidence(
                id=f"{profile.id}#themes",
                company_id=company.id,
                field="product",
                claim="; ".join(profile.themes),
                source_family="founder_profile",
                tag=tag,
            )
        )
    return out


def _programmes(profile_id: str, applicant: Applicant, today: date, preset: str) -> list[Opportunity]:
    p = load_preset(preset)
    out = []
    for inst in instruments():
        if inst["type"] not in ("accelerator", "access_programme", "coaching") and inst["id"] not in p.programmes:
            continue
        e = evaluate_instrument(inst, applicant, today)
        if e.tier in LIVE_TIERS:
            out.append(
                opportunity(
                    profile_id, e, applicant, "apelago", today, inst["id"] in p.programmes, frozenset(p.grant_topics)
                )
            )
    return sorted(out, key=lambda o: (-o.priority, o.id))


def _next_30_days(
    profile: FounderProfile, tiers: list[FounderTier], investors: list[InvestorMatch], today: date
) -> list[NextStep]:
    due = sorted(
        (t for t in tiers if t.tier in LIVE_TIERS and t.deadline and 0 <= (t.deadline - today).days <= 30),
        key=lambda t: (t.deadline, t.instrument_id),
    )
    by_id = {inst["id"]: inst for inst in instruments()}
    steps = [
        NextStep(
            rank=0,
            opportunity_id=f"{profile.id}:{t.instrument_id}",
            kind=kind_of(by_id[t.instrument_id]),
            title=t.instrument_name,
            action="Check the rule and apply before the deadline",
            why=f"{t.tier}: {t.deciding_rule}",
            deadline=t.deadline,
            audience="startup",
        )
        for t in due
    ]
    steps += [
        NextStep(
            rank=0,
            opportunity_id=f"investor:{m.investor_id}",
            kind="investor",
            title=m.name,
            action=f"Shortlist {m.name} and prepare the ask",
            why=m.fit_label,
            audience="startup",
        )
        for m in investors
        if m.when == "now"
    ][:2]
    return [s.model_copy(update={"rank": i + 1}) for i, s in enumerate(steps)]
