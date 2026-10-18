from bluewatch.models import Channel
from bluewatch.outreach.addresses import channels_from_page, check_address, sanitise

PERSONAL = [
    "anna.virtanen@meriva.example",
    "matti@meriva.example",
    "a.virtanen@meriva.example",
    "virtanen.anna@meriva.example",
    "anna_v@meriva.example",
    "firstname.lastname@gmail.com",
    "info@outlook.com",
    "j.korhonen@meriva.example",
    "lena.lindqvist@meriva.example",
    "pekka+work@meriva.example",
]


def test_ten_personal_addresses_on_a_page_are_never_kept():
    page = (
        "Contact us: info@meriva.example, press@meriva.example. Team: "
        + ", ".join(PERSONAL)
        + ". Site by hello@agency.fi"
    )
    channels = channels_from_page(page, company_domain="meriva.example", source_url="https://www.meriva.example/")
    kept = {c.address for c in channels if c.address}
    assert kept == {"info@meriva.example", "press@meriva.example"}  # the agency's address is not Meriva's
    assert [c.kind for c in channels] == ["org_generic", "org_press", "personal_blocked"]
    assert all(p not in str([c.model_dump() for c in channels]) for p in PERSONAL)


def test_role_addresses_need_the_role_route():
    assert check_address("ceo@meriva.example", company_domain="meriva.example").kind == "named_role"
    declared_generic = sanitise(
        Channel(kind="org_generic", address="CEO@meriva.example"), company_domain="meriva.example"
    )
    assert declared_generic.kind == "named_role" and declared_generic.address == "ceo@meriva.example"


def test_a_personal_address_is_dropped_whatever_kind_is_declared():
    for kind in ("org_generic", "named_role", "opt_in"):
        channel = sanitise(
            Channel(kind=kind, address="anna.virtanen@meriva.example", role_check_evidence_id="e1"),
            company_domain="meriva.example",
        )
        assert channel.kind == "personal_blocked" and channel.address is None
