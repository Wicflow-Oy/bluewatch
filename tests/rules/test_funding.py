import re
from datetime import date

from bluewatch.models import FounderProfile
from bluewatch.rules.assess import assess
from bluewatch.rules.eligibility import Applicant, applicant_from_profile
from bluewatch.rules.funding import evaluate, funding_opportunities, instruments, tiers_for
from bluewatch.rules.seed_adapter import demo_items

TODAY = date(2026, 10, 17)


def applicant(country="FI", **kw) -> Applicant:
    base = dict(
        country=country,
        form="OY",
        org_type="company",
        age_years=0.5,
        size_band="micro",
        trl=(6, 6),
        trl_applicable=True,
        industry_code="62100",
        municipality="Turku",
        topics=frozenset({"ocean", "maritime"}),
        from_register=True,
    )
    return Applicant(**(base | kw))


def inst(**kw) -> dict:
    base = {
        "id": "test-call",
        "name": "Test call",
        "funder": "Test funder",
        "type": "grant",
        "status": "open",
        "deadline": "2026-11-20",
        "url": "https://example.org/call",
        "applicant_types": ["sme"],
        "country_rule": "EU Member State or Horizon associated country",
        "trl_min": 5,
        "trl_max": 8,
        "themes": ["blue_economy"],
        "rule_sources": {"all": "read"},
    }
    return base | kw


def sbep() -> dict:
    return next(i for i in instruments() if i["id"] == "sbep-jtc4")


def tier(country: str) -> str:
    return evaluate(sbep(), applicant(country=country), TODAY).tier


def test_sbep_call_4_flips_on_registration_country():
    finnish = evaluate(sbep(), applicant("FI"), TODAY)
    norwegian = evaluate(sbep(), applicant("NO", form="AS"), TODAY)
    assert finnish.tier == "excluded" and finnish.rule_verified
    assert "no Finnish funder" in finnish.deciding_rule
    assert "no upgrade path" in finnish.upgrade_path
    assert norwegian.tier == "possible"  # the national funder's own rules apply
    assert finnish.deadline == norwegian.deadline == date(2026, 11, 16)


def test_sbep_other_countries_follow_the_published_table():
    assert tier("LV") != "excluded" and tier("LV") != "certain"  # listed, no funder entry: confirm
    assert tier("DE") == "possible"  # participating funder, not in the per-country table
    assert tier("IS") == "excluded"  # no Icelandic funder in call 4


def test_certain_only_when_every_deciding_rule_was_read():
    assert evaluate(inst(), applicant(), TODAY).tier == "certain"
    snippet_rule = inst(rule_sources={"all": "read", "trl_min": "snippet"})
    capped = evaluate(snippet_rule, applicant(), TODAY)
    assert capped.tier == "possible" and not capped.rule_verified


def test_unknowns_make_it_likely_and_a_fail_excludes_with_the_rule():
    unknown_size = evaluate(inst(), applicant(size_band="unknown"), TODAY)
    assert unknown_size.tier == "likely" and "SME status" in unknown_size.deciding_rule
    too_early = evaluate(inst(), applicant(trl=(3, 3)), TODAY)
    assert too_early.tier == "excluded"
    assert "TRL" in too_early.deciding_rule and too_early.upgrade_path == "Reach TRL 5"
    assert too_early.deadline == date(2026, 11, 20)


def test_service_company_fails_a_trl_gate():
    assert evaluate(inst(), applicant(trl=None, trl_applicable=False), TODAY).tier == "excluded"


def test_a_one_level_trl_gate_names_that_level_once():
    gate = evaluate(inst(trl_min=9, trl_max=9), applicant(trl=None), TODAY)
    assert gate.deciding_rule == "No rule fails; still unknown: TRL: Needs TRL 9; the company's TRL is not known"


def test_no_open_call_caps_at_possible():
    assert evaluate(inst(status="closed_next_unknown", deadline=None), applicant(), TODAY).tier == "possible"
    assert evaluate(inst(deadline="2026-10-01"), applicant(), TODAY).tier == "possible"  # deadline passed


def test_primary_aquaculture_rule_needs_the_industry_code():
    sprint = next(i for i in instruments() if i["id"] == "bf-sprint")
    pending = evaluate(sprint, applicant(industry_code=None), TODAY)
    assert any("not yet registered" in c.text for c in pending.checks)
    assert evaluate(sprint, applicant(industry_code="03220"), TODAY).tier == "excluded"


def test_national_instruments_only_for_their_own_country():
    sprint = next(i for i in instruments() if i["id"] == "bf-sprint")
    assert evaluate(sprint, applicant("NO", form="AS"), TODAY).tier == "excluded"
    assert evaluate(sprint, applicant("FI"), TODAY).tier in ("likely", "possible")


def test_every_tier_names_its_rule_source_and_deadline():
    profile = FounderProfile(
        id="NO:938525420", country="NO", name="HAVNIO AS", founded=date(2026, 9, 16), themes=["harbour software"]
    )
    tiers = tiers_for(applicant_from_profile(profile, TODAY), today=TODAY)
    assert len(tiers) == len(instruments())
    for t in tiers:
        assert t.deciding_rule and t.rule_source
    by_id = {t.instrument_id: t for t in tiers}
    assert by_id["emso-physical-access-2026"].deadline == date(2026, 10, 31)
    assert by_id["bf-r2b"].tier != "certain"  # call 2/2026 is closed and open to research organisations only


def test_company_opportunities_leave_out_exclusions_and_rank_by_priority():
    c, e, _ = next(item for item in demo_items() if item[0].id == "FI:3101791-3")
    opportunities = funding_opportunities(c, assess(c, e), mode="apelago", today=TODAY)
    assert opportunities and all(o.tier != "excluded" for o in opportunities)
    assert [o.priority for o in opportunities] == sorted((o.priority for o in opportunities), reverse=True)
    for o in opportunities:
        assert o.rule and o.action and o.rule_source
        assert abs(sum(o.priority_parts.values()) - o.priority) < 1e-3


RESEARCH_NOTE = re.compile(r"snippet|search summary|third-party|presumed|\(inferred|\(source:|generic Horizon", re.I)
BARE_CODE = re.compile(r"\b(?:for|in|to|from) (?!EU\b)[A-Z]{2}\b")


def test_rule_texts_are_plain_statements_without_research_notes_or_country_codes():
    """How sure a rule is shows as its source tag; the text a visitor reads is the rule itself."""
    for a in (applicant("FI"), applicant("NO", form="AS"), applicant("SI"), applicant("BG"), applicant(None)):
        for i in instruments():
            e = evaluate(i, a, TODAY)
            texts = [e.deciding_rule, e.upgrade_path or "", e.unknown_reason or "", *(c.text for c in e.checks)]
            for text in texts:
                assert not RESEARCH_NOTE.search(text), (i["id"], text)
                assert not BARE_CODE.search(text), (i["id"], text)


def test_a_country_rule_names_the_country():
    e = evaluate(inst(country_rule="Slovenia"), applicant("FI"), TODAY)
    assert e.deciding_rule == "Country: Only for companies registered in Slovenia"
    assert e.upgrade_path == "Apply through a company registered in Slovenia"
    e = evaluate(inst(country_rule="EU-headquartered"), applicant("NO"), TODAY)
    assert e.upgrade_path == "Apply through an EU-headquartered company"
