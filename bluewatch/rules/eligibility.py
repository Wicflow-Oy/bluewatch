"""Hard-rule checks for one funding instrument against one applicant.

grants.json stores each rule as published text plus the tag of its source (rule_sources: read,
sedia, snippet, inferred, unverified): how sure a rule is lives in the tag, never in the text. Every
check here reads one of those fields and returns pass, fail or unknown with the tag of the field it
read, so the tier can say how sure it is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from bluewatch.models import Company, FounderProfile, ReadinessLevel, Registry
from bluewatch.rules.geo import COUNTRY_CODES, EU, EUROPE, NORDIC, countries_named
from bluewatch.rules.text import humanise_keys, trunc
from bluewatch.rules.topics import is_generic, shared_topics, topics_of

VERIFIED = frozenset({"read", "sedia"})
# Country names for rule texts: "Only for companies registered in Slovenia", never "Only for SI".
COUNTRY_NAMES = {code: name.title() for name, code in COUNTRY_CODES.items() if len(name) > 3}
SIZE_ORDER = {"micro": 0, "small": 1, "medium": 2, "large": 3}
ALAND = frozenset(
    {
        "mariehamn",
        "maarianhamina",
        "jomala",
        "finström",
        "lemland",
        "saltvik",
        "hammarland",
        "sund",
        "eckerö",
        "föglö",
        "geta",
        "vårdö",
        "lumparland",
        "brändö",
        "kumlinge",
        "kökar",
        "sottunga",
    }
)
NATIONAL_TYPES = {
    "finnish_oy": ("FI", ("OY", "OYJ"), "a Finnish limited company (Oy)"),
    "swedish_aktiebolag": ("SE", ("AB",), "a Swedish limited company (AB)"),
    "norwegian_company": ("NO", (), "a Norwegian company"),
    "norwegian_registered_business_enterprise": ("NO", (), "a company in Norway's Register of Business Enterprises"),
    "danish_company_registered_with_CVR_number": ("DK", (), "a Danish company with a CVR number"),
    "estonian_starting_entrepreneur": ("EE", (), "an Estonian starting entrepreneur"),
    "micro_or_small_enterprise_registered_in_estonia": ("EE", (), "a micro or small company registered in Estonia"),
}
COMPANY_TYPES = {
    "sme",
    "startup",
    "spin_out",
    "small_midcap_equity_only",
    "private_sector_organisation",
    "innovator",
    "limited_company",
    "entrepreneurs",
    "any_legal_entity_per_national_funder",
    "large_company",
    "limited_partnership",
    "general_partnership",
    "sole_trader",
}
SME_TYPES = {"sme", "startup", "spin_out"}
RESEARCH_TYPES = {
    "research_organisation",
    "research_org",
    "university",
    "erc_pi_host_institution",
    "individual_researcher",
    "any_legal_entity_per_national_funder",
}
FOUNDING_TYPES = {"individual_founding_sme", "researchers_becoming_founders", "innovator", "individual_researcher"}
ORG_TYPES = {
    "company": COMPANY_TYPES,
    "research_org": RESEARCH_TYPES,
    "student_team": FOUNDING_TYPES,
    "individual_founding": FOUNDING_TYPES,
}


@dataclass(frozen=True)
class Applicant:
    country: str | None
    form: str | None
    org_type: str
    age_years: float | None
    size_band: str
    trl: tuple[int, int] | None
    trl_applicable: bool
    industry_code: str | None
    municipality: str | None
    topics: frozenset[str]
    from_register: bool
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Check:
    name: str
    outcome: str  # pass | fail | unknown
    text: str
    tag: str
    cap: str | None = None  # a tier ceiling the rule itself sets ("possible: the funder's own rules apply")
    upgrade: str | None = None


@dataclass
class Checks:
    items: list[Check] = field(default_factory=list)

    def add(self, name: str, outcome: str, text: str, tag: str, **kw) -> None:
        # Rule texts quote grants.json keys ("Open to spin_out, sme"); visitors read words.
        self.items.append(Check(name, outcome, humanise_keys(text), tag, **kw))


# --------------------------------------------------------------------------- applicants
def applicant_from_company(company: Company, levels: list[ReadinessLevel], today: date) -> Applicant:
    trl = next((lv for lv in levels if lv.key == "trl"), None)
    text = " ".join(
        [
            *company.names,
            company.one_liner or "",
            company.vertical_note or "",
            (company.vertical or "").replace("_", " "),
        ]
    )
    founded = company.registry.founded
    return Applicant(
        country=company.registry.country if company.registry.country != "XX" else None,
        form=company.registry.form,
        org_type="company",
        age_years=round((today - founded).days / 365.25, 2) if founded else None,
        size_band="unknown",
        trl=(trl.level, trl.level) if trl and trl.level else None,
        trl_applicable=trl.applicable if trl else True,
        industry_code=company.registry.industry_code,
        municipality=company.registry.municipality,
        topics=frozenset(topics_of(text)),
        from_register=bool(company.registry.id),
        evidence_ids=tuple(trl.evidence_ids) if trl else (),
    )


def applicant_from_profile(profile: FounderProfile, today: date, registry: Registry | None = None) -> Applicant:
    band = re.findall(r"\d", profile.trl_band or "")
    return Applicant(
        country=profile.country,
        form=registry.form if registry else None,
        org_type=profile.org_type,
        age_years=round((today - profile.founded).days / 365.25, 2) if profile.founded else None,
        size_band=profile.size_band,
        trl=(int(band[0]), int(band[-1])) if band else None,
        trl_applicable=True,
        industry_code=registry.industry_code if registry else None,
        municipality=registry.municipality if registry else None,
        topics=frozenset(topics_of(" ".join(profile.themes))),
        from_register=profile.source == "register",
    )


# --------------------------------------------------------------------------- the checks
def check_instrument(inst: dict, a: Applicant) -> list[Check]:
    out = Checks()
    national = _national_type(inst)
    if national:
        _check_national(inst, a, national, out)
    else:
        _check_country(inst, a, out)
    _check_applicant_type(inst, a, out)
    _check_size(inst, a, out)
    _check_age(inst, a, out)
    _check_trl(inst, a, out)
    _check_themes(inst, a, out)
    _check_consortium(inst, out)
    _check_other(inst, a, out)
    return out.items


def tag_of(inst: dict, rule_field: str) -> str:
    sources = inst.get("rule_sources") or {}
    return sources.get(rule_field) or sources.get("all") or sources.get("rules") or "unverified"


def _national_type(inst: dict) -> tuple[str, tuple[str, ...], str] | None:
    types = inst.get("applicant_types")
    if isinstance(types, list):
        return next((NATIONAL_TYPES[t] for t in types if t in NATIONAL_TYPES), None)
    return None


def _check_national(inst: dict, a: Applicant, national: tuple[str, tuple[str, ...], str], out: Checks) -> None:
    country, forms, label = national
    tag = tag_of(inst, "applicant_types")
    if a.country is None:
        out.add("Country", "unknown", "Registration country not known", tag)
    elif a.country != country:
        out.add(
            "Country",
            "fail",
            f"Only for {label}",
            tag,
            upgrade=f"Apply through a company registered in {COUNTRY_NAMES[country]}",
        )
    elif forms and a.form and a.form not in forms:
        out.add("Applicant type", "fail", f"Only for {label}", tag)
    else:
        out.add("Country", "pass", f"Open to {label}", tag)
    rule = str(inst.get("country_rule") or "").lower()
    if a.country == "FI" and "aland-only" in rule:
        if a.municipality is None:
            out.add(
                "Country",
                "unknown",
                "Registered office not known (companies operating only in Åland are excluded)",
                tag_of(inst, "country_rule"),
            )
        elif a.municipality.lower() in ALAND:
            out.add("Country", "fail", "Companies operating only in Åland are excluded", tag_of(inst, "country_rule"))


def _check_country(inst: dict, a: Applicant, out: Checks) -> None:
    by_country = inst.get("tier_by_registration_country")
    if by_country:
        _check_country_table(inst, a, by_country, out)
        return
    rule = inst.get("country_rule")
    tag = tag_of(inst, "country_rule")
    funder = str(inst.get("funder", ""))
    if not rule and inst.get("type") == "cascade" and _funder_country(inst["name"]):
        # A project's open call for third parties serves the region in its title ("Slovenian seas").
        rule, tag = f"{_funder_country(inst['name'])} (the region named in the call title)", "inferred"
    elif not rule and funder.startswith("Horizon Europe"):
        # EU topics carry no country field; the generic Horizon rule rides on the consortium rule's tag.
        rule = "EU Member State or Horizon associated country (generic Horizon rule)"
        tag = tag_of(inst, "consortium_rule")
    elif not rule and _funder_country(funder):
        # A national funder with no stated country rule: inferred, so it can exclude but never confirm.
        rule, tag = f"{_funder_country(funder)} (inferred from the national funder)", "inferred"
    if not rule or not isinstance(rule, str):
        return
    lower = rule.lower()
    if lower.startswith("unknown"):
        out.add("Country", "unknown", "Country rule not published", tag)
        return
    if "no restriction" in lower:
        out.add("Country", "pass", "No restriction on the applicant's country", tag)
        return
    if "priority for" in lower:
        out.add("Country", "unknown", rule, tag)
        return
    if "eu member state or horizon associated" in lower:
        allowed, who = EUROPE, "applicants from EU or Horizon Europe associated countries"
        through = "a company in an EU or Horizon Europe associated country"
    elif "eu-headquartered" in lower:
        allowed, who, through = EU, "EU-headquartered companies", "an EU-headquartered company"
    elif "nordic" in lower:
        allowed, who, through = NORDIC, "applicants from the Nordic region", "a company in the Nordic region"
    else:
        named = (
            countries_named(rule)
            | ({"NO"} if "norwegian" in lower else set())
            | ({"FI"} if "finnish" in lower else set())
        )
        if not named:
            out.add("Country", "unknown", f"Country rule not machine-readable: {rule}", tag)
            return
        allowed, who = frozenset(named), f"companies registered in {_country_names(named)}"
        through = f"a company registered in {_country_names(named)}"
    if a.country is None:
        out.add("Country", "unknown", f"Open to {who}; registration country not known", tag)
    elif a.country in allowed:
        out.add("Country", "pass", f"Open to {who}", tag)
    else:
        out.add("Country", "fail", f"Only for {who}", tag, upgrade=f"Apply through {through}")


def _country_names(codes: set[str]) -> str:
    """ "Finland", "Finland or Sweden", "Denmark, Finland or Sweden": names, never bare codes."""
    names = sorted(COUNTRY_NAMES.get(code, code) for code in codes)
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} or {names[-1]}"


NATIONALITIES = {
    "finnish": "Finland",
    "norwegian": "Norway",
    "swedish": "Sweden",
    "danish": "Denmark",
    "estonian": "Estonia",
    "latvian": "Latvia",
    "lithuanian": "Lithuania",
    "slovenian": "Slovenia",
}


def _funder_country(funder: str) -> str | None:
    lower = funder.lower()
    return next((country for word, country in NATIONALITIES.items() if word in lower), None)


def _check_country_table(inst: dict, a: Applicant, by_country: dict, out: Checks) -> None:
    """A call whose eligibility is decided per registration country (SBEP call 4)."""
    tag = tag_of(inst, "country_rule")
    funders = inst.get("participating_countries") or {}
    upgrade = inst.get("upgrade_path_note")
    if a.country is None:
        out.add("Country", "unknown", "Registration country not known; this call is decided by it", tag)
        return
    text = by_country.get(a.country)
    if text is None and a.country in funders:
        where = COUNTRY_NAMES.get(a.country, a.country)
        text = f"possible: {funders[a.country]} funds partners from {where}; its own eligibility rules apply"
    if text is None:
        where = COUNTRY_NAMES.get(a.country, a.country)
        out.add(
            "Country",
            "fail",
            f"No funder from {where} in this call; a firm registered there can only join as a self-funded partner",
            tag,
            upgrade=upgrade,
        )
    elif text.startswith("excluded"):
        out.add("Country", "fail", text.removeprefix("excluded: "), tag, upgrade=upgrade)
    elif text.startswith("possible?"):
        out.add("Country", "unknown", text.removeprefix("possible?: "), tag, upgrade=upgrade)
    else:
        out.add("Country", "pass", text.removeprefix("possible: "), tag, cap="possible", upgrade=upgrade)


def _check_applicant_type(inst: dict, a: Applicant, out: Checks) -> None:
    types = inst.get("applicant_types")
    tag = tag_of(inst, "applicant_types")
    if isinstance(types, str):
        if types.startswith("unknown"):
            out.add("Applicant type", "unknown", "Applicant types not published", tag)
        return
    general = [t for t in types or [] if t not in NATIONAL_TYPES]
    if not general:
        return
    fitting = set(general) & ORG_TYPES.get(a.org_type, set())
    if not fitting:
        out.add("Applicant type", "fail", f"Open to: {', '.join(general)}", tag)
    elif fitting <= SME_TYPES and a.org_type == "company":
        if a.size_band == "unknown":
            out.add(
                "Applicant type",
                "unknown",
                "SME status not known (headcount and turnover)",
                tag,
                upgrade="Confirm SME status: under 250 staff and turnover up to EUR 50M",
            )
        elif a.size_band == "large":
            out.add("Applicant type", "fail", "Open to SMEs only", tag)
        else:
            out.add("Applicant type", "pass", f"An SME ({a.size_band})", tag)
    else:
        out.add("Applicant type", "pass", f"Open to {', '.join(sorted(fitting))}", tag)


def _check_size(inst: dict, a: Applicant, out: Checks) -> None:
    rule = inst.get("size_rule")
    if not isinstance(rule, str) or rule.lower().startswith("unknown as"):
        return
    lower = rule.lower()
    if "sme" in lower and "sme" in (inst.get("applicant_types") or []):
        return  # already checked as the applicant type
    tag = tag_of(inst, "size_rule")
    if lower == "unknown":
        out.add("Size", "unknown", "Size rule not published", tag)
        return
    if re.search(r"(<|fewer than|maximum)\s*10\b", lower) or ("micro" in lower and "small" not in lower):
        limit = "micro"
    elif re.search(r"<\s*50\b", lower) or "micro or small" in lower:
        limit = "small"
    else:
        limit = "medium"
    if a.size_band == "unknown":
        out.add("Size", "unknown", f"{rule}; company size not known", tag)
    elif SIZE_ORDER[a.size_band] <= SIZE_ORDER[limit]:
        out.add("Size", "pass", f"{rule}: a {a.size_band} company fits", tag)
    else:
        out.add("Size", "fail", rule, tag)


def _check_age(inst: dict, a: Applicant, out: Checks) -> None:
    rule = inst.get("age_rule")
    if not isinstance(rule, str):
        return
    tag = tag_of(inst, "age_rule")
    lower = rule.lower()
    if lower == "unknown" or "case by case" in lower:
        out.add("Age", "unknown", "Age rule not published" if lower == "unknown" else rule, tag)
        return
    most = re.search(r"(?:<|not more than|up to|under)\s*(\d+)\s*years?", lower)
    least = re.search(r"(?:at least|minimum of|>=)\s*(\d+)\s*years?", lower)
    if a.age_years is None:
        out.add("Age", "unknown", f"{rule}; founding date not known", tag)
    elif most and a.age_years >= int(most.group(1)):
        if "pivot" in lower:
            out.add("Age", "unknown", f"Older than {most.group(1)} years: only with a significant pivot", tag)
        else:
            out.add("Age", "fail", rule, tag)
    elif least and a.age_years < int(least.group(1)):
        out.add("Age", "fail", rule, tag)
    elif most or least:
        out.add("Age", "pass", f"{trunc(a.age_years, 1)} years old: {rule}", tag)
    condition = re.search(r"\bwith (no prior [^,]+)", lower)
    if condition:
        out.add("Age", "unknown", f"Not checked: {condition.group(1)}", tag)


def _check_trl(inst: dict, a: Applicant, out: Checks) -> None:
    lo, hi = inst.get("trl_min"), inst.get("trl_max")
    if lo is None and hi is None:
        return
    lo, hi = lo or 1, hi or 9
    tag = tag_of(inst, "trl_min")
    need = f"TRL {lo}" if lo == hi else f"TRL {lo}-{hi}"
    if not a.trl_applicable:
        out.add(
            "TRL",
            "fail",
            f"Needs {need}; technology readiness does not apply to this company",
            tag,
            upgrade="Only if the company develops its own technology",
        )
    elif a.trl is None:
        # A stage gate that cannot be checked keeps the instrument at "possible" at best.
        out.add(
            "TRL",
            "unknown",
            f"Needs {need}; the company's TRL is not known",
            tag,
            cap="possible",
            upgrade=f"Show evidence of TRL {lo} (for example a pilot or test with a named partner)",
        )
    elif a.trl[1] < lo:
        out.add("TRL", "fail", f"Needs {need}; evidence supports TRL {a.trl[1]}", tag, upgrade=f"Reach TRL {lo}")
    elif a.trl[0] > hi:
        out.add("TRL", "fail", f"Needs {need}; the company is past it (TRL {a.trl[0]})", tag)
    elif lo <= a.trl[0] and a.trl[1] <= hi:
        out.add("TRL", "pass", f"Needs {need}; evidence supports TRL {a.trl[0]}", tag)
    else:
        out.add("TRL", "unknown", f"Needs {need}; the company's TRL band overlaps it", tag)


def _check_themes(inst: dict, a: Applicant, out: Checks) -> None:
    themes = inst.get("themes")
    if not themes:
        return
    text = "; ".join(themes)
    tag = tag_of(inst, "themes")
    if is_generic(text):
        out.add("Theme", "pass", "Open to any sector", tag)
        return
    shared = shared_topics(text, a.topics)
    if not topics_of(text):
        out.add("Theme", "unknown", f"Theme fit not mapped: {text}", tag, cap="possible")
    elif not a.topics:
        # Without the company's themes a themed call can't be more than possible, however clean the rest is.
        out.add(
            "Theme",
            "unknown",
            f"Themes: {text}; the company's themes are not known",
            tag,
            cap="possible",
            upgrade="Describe what the company does (its site or a short profile) to test the theme fit",
        )
    elif shared:
        out.add("Theme", "pass", f"Theme fit: {', '.join(sorted(shared))}", tag)
    else:
        out.add("Theme", "fail", f"Themes ({text}) do not match the company's ({', '.join(sorted(a.topics))})", tag)


def _check_consortium(inst: dict, out: Checks) -> None:
    rule = inst.get("consortium_rule")
    if not isinstance(rule, str):
        return
    tag = tag_of(inst, "consortium_rule")
    parts = [p.strip() for p in rule.split(";") if p.strip()]
    single = re.compile(r"single (applicant|entity|company)|or team")
    if rule.lower().startswith("unknown"):
        out.add("Consortium", "unknown", "Consortium rule not published", tag)
    elif any(single.search(p.lower()) for p in parts):
        out.add("Consortium", "pass", "A single applicant can apply", tag)
        for extra in (p for p in parts if not single.search(p.lower())):
            out.add("Consortium", "unknown", f"Not checked: {extra}", tag)
    else:
        out.add("Consortium", "unknown", f"Needs partners: {parts[0]}", tag, upgrade=f"Build the consortium: {rule}")


def _check_other(inst: dict, a: Applicant, out: Checks) -> None:
    tag = tag_of(inst, "other_hard_rules")
    for rule in inst.get("other_hard_rules") or []:
        lower = rule.lower()
        if "removed" in lower:
            continue  # the pack notes a rule that was dropped as unverified
        if "primary agriculture, fisheries or aquaculture" in lower:
            _check_primary_sector(a, rule, tag, out)
        elif "finnish trade register" in lower:
            outcome = "fail" if a.country and a.country != "FI" else "pass" if a.country == "FI" else "unknown"
            out.add("Other rule", outcome, rule, tag)
        elif "blue-economy product" in lower:
            blue = a.topics & {"ocean", "maritime", "aquaculture_food", "water"}
            out.add("Other rule", "pass" if blue else "unknown", rule, tag)
        else:
            out.add("Other rule", "unknown", f"Not checked: {rule}", tag)


def _check_primary_sector(a: Applicant, rule: str, tag: str, out: Checks) -> None:
    code = (a.industry_code or "").replace(".", "")
    if not code:
        reason = (
            "industry code not yet registered (new Finnish companies get one 2-6 weeks after founding)"
            if a.from_register
            else "industry code not given"
        )
        out.add(
            "Other rule",
            "unknown",
            f"{rule}: {reason}",
            tag,
            upgrade="Re-check when the register shows the industry code",
        )
    elif code[:2] in ("01", "02", "03"):
        out.add("Other rule", "fail", f"{rule}: industry code {a.industry_code} is primary production", tag)
    else:
        out.add("Other rule", "pass", f"Industry code {a.industry_code} is not primary production", tag)
