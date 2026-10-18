from bluewatch.models import DIMENSIONS
from bluewatch.rules.dimensions import assess_dimensions
from bluewatch.rules.evidence import CORE_FIELDS, FIELD_DIMENSIONS
from bluewatch.rules.gaps import ledger
from tests.rules.helpers import company, ev, registered


def test_ten_dimensions_in_contract_order():
    dims = assess_dimensions(company(), [ev("Harbour software")])
    assert tuple(d.key for d in dims) == DIMENSIONS
    assert {d.state for d in dims} <= {"fact", "assumption", "unknown", "not_applicable"}


def test_dimension_states_follow_the_evidence():
    share = ev("Share issue registered 20 Aug 2026", field="funding", tag="registry", family="prh_notices")
    guess = ev("Probably sells to ports", field="customers", tag="snippet", state="assumption")
    dims = {d.key: d for d in assess_dimensions(company(), [ev("Harbour software"), share, guess])}
    assert dims["product"].state == "fact"
    assert dims["deal_dynamics"].state == "fact"
    assert dims["business_model"].state == "assumption"
    assert dims["team"].state == "unknown" and "team page" in dims["team"].note


def test_tech_is_not_applicable_for_a_service_company():
    dims = {d.key: d for d in assess_dimensions(company(), [ev("Aquaculture consulting and training")])}
    assert dims["tech"].state == "not_applicable"


def test_ledger_always_carries_the_five_standard_checks():
    c = company()
    evidence = [registered(), ev("Harbour software")]
    gl = ledger(c, evidence)
    unknown_fields = {e.field for e in gl.unknowns}
    assert {"customers", "team", "funding", "public_contracts"} <= unknown_fields
    assert all(e.next_check for e in gl.unknowns)
    assert all(e.id.startswith(f"{c.id}#gap-") for e in gl.unknowns)  # stable ids for evidence requests
    assert ledger(c, evidence) == gl


def test_ledger_marks_trl_not_applicable_for_services():
    gl = ledger(company(), [ev("Aquaculture consulting and training")])
    assert [e.field for e in gl.not_applicable] == ["trl"]


def test_every_unknown_dimension_has_a_ledger_entry_that_says_how_to_close_it():
    c = company()
    evidence = [registered(), ev("Harbour software")]
    gl = ledger(c, evidence)
    unknown_dimensions = {d.key for d in assess_dimensions(c, evidence) if d.state == "unknown"}
    covered = {d for e in gl.unknowns for d in FIELD_DIMENSIONS.get(e.field, ())}
    assert unknown_dimensions and unknown_dimensions <= covered
    market = next(e for e in gl.unknowns if e.field == "market")
    assert market.next_check and "public tenders" in (market.next_check.how or "")
    assert {e.field for e in gl.unknowns} - set(CORE_FIELDS) == {"market", "competition", "impact"}
