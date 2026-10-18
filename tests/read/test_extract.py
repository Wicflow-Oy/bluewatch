from datetime import datetime, timezone

from bluewatch.llm import FakeModelClient, ModelResponse
from bluewatch.models import Company, Registry, Resolution
from bluewatch.read.extract import read_claims
from bluewatch.read.fetch import page_from_html
from tests.read.fakes import BUDGET, ScriptedClient, html

NOW = datetime(2026, 10, 17, 9, 0, tzinfo=timezone.utc)
SORBENT = "We revolutionize oil spill response with biodegradable sorbent"
COMPANY = Company(
    id="FI:3568392-1",
    names=["Sireness Oy"],
    resolution=Resolution(state="resolved", reason="test"),
    registry=Registry(country="FI", id="3568392-1", name="Sireness Oy"),
)
PAGE = page_from_html(
    "https://sireness.example/",
    html(
        "Sireness",
        (
            "<p>Awarded technology, founded by two women scientists, is setting a new benchmark.</p>"
            "<p>Get in touch with our founder and COB Maija Esimerkki maija@sireness.example</p>"
            "<p>We revolutionize oil spill response with biodegradable sorbent.</p>"
            "<p>Our team of 6 experts works in Vantaa.</p>"
        ),
    ),
)


def claim(field, value, quote, text="A claim."):
    return {"field": field, "claim": text, "value": value, "quote": quote}


def run(claims):
    model = FakeModelClient({"extract_claims": {"claims": claims}})
    evidence, problem = read_claims(COMPANY, PAGE, model, model_id="m", retrieved_at=NOW)
    assert problem is None
    return evidence


def test_verified_claims_are_kept_with_their_source():
    [e] = run([claim("product", "biodegradable sorbent", SORBENT)])
    assert e.field == "product" and e.verified_quote and e.tag == "llm"
    assert e.url == "https://sireness.example/" and e.source_family == "site:sireness.example" and e.retrieved_at == NOW


def test_a_number_its_quote_does_not_hold_drops_the_claim():
    """The quote is on the page, but "6" is not in it: the claim took the number from elsewhere."""
    text = "The company has 6 experts."
    assert run([claim("team", "6 experts", "founded by two women scientists", text)]) == []
    assert run([claim("team", "6 experts", "Our team of 6 experts works in Vantaa", text)])


def test_claims_whose_quote_is_not_on_the_page_are_dropped():
    assert run([claim("customers", "Port of Turku", "Our customers include the Port of Turku")]) == []


def test_team_claims_are_counts_or_roles_never_names():
    kept = run(
        [
            claim("team", "two founders", "founded by two women scientists"),
            claim("team", "6 experts", "Our team of 6 experts works in Vantaa"),
            claim("team", "Maija Esimerkki (founder)", "Get in touch with our founder and COB Maija Esimerkki"),
            claim("team", "founder and COB", "Get in touch with our founder and COB Maija Esimerkki"),
            claim("team", "a strong team", "Awarded technology, founded by two women scientists"),
        ]
    )
    assert [e.value for e in kept] == ["two founders", "6 experts"]


def test_contact_details_never_become_evidence():
    assert run([claim("product", "contact", "COB Maija Esimerkki maija@sireness.example")]) == []


def test_unknown_fields_and_duplicates_are_dropped():
    kept = run(
        [claim("product", "sorbent", SORBENT), claim("product", "sorbent", SORBENT), claim("valuation", "1", SORBENT)]
    )
    assert len(kept) == 1


def test_a_budget_refusal_gives_no_claims_and_says_why():
    evidence, problem = read_claims(COMPANY, PAGE, ScriptedClient(BUDGET), model_id="m", retrieved_at=NOW)
    assert (evidence, problem) == ([], "model budget")


def test_nothing_is_taken_from_a_truncated_response():
    data = {"claims": [claim("product", "sorbent", SORBENT)]}
    truncated = ScriptedClient(ModelResponse(text="{...", data=data, stop_reason="max_tokens"))
    assert read_claims(COMPANY, PAGE, truncated, model_id="m", retrieved_at=NOW) == ([], "model truncated")
