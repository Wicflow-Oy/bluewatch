from datetime import date, datetime, timedelta, timezone

from bluewatch.models import Bridge, BridgeEvidence, BridgeParty, EntityRef, Opportunity, Resolution, Signal
from bluewatch.rules.alerts import alerts
from bluewatch.rules.assess import assess
from bluewatch.rules.nextsteps import order
from tests.rules.helpers import company, ev, registered

TODAY = date(2026, 10, 17)


def opp(oid: str, tier: str, deadline: date | None, kind: str = "grant") -> Opportunity:
    return Opportunity(
        id=oid,
        company_id="FI:1234567-8",
        kind=kind,
        title=oid,
        tier=tier,
        rule="rule",
        deadline=deadline,
        action=f"Act on {oid}",
    )


def thin_assessment():
    c = company()
    return c, assess(c, [registered(), ev("Harbour software")])


def test_good_fit_deadlines_first_then_ask_the_company():
    c, a = thin_assessment()
    steps = order(
        c,
        a,
        [
            opp("late", "possible", None, "programme"),
            opp("soon", "likely", date(2026, 10, 30)),
            opp("sooner", "certain", date(2026, 10, 25)),
        ],
        [],
        [],
        today=TODAY,
    )
    assert [s.opportunity_id for s in steps[:3]] == ["sooner", "soon", "ask_company:FI:1234567-8"]
    assert [s.rank for s in steps] == list(range(1, len(steps) + 1))
    ask = steps[2]
    assert ask.kind == "ask_company" and ask.audience == "ecosystem_actor"
    assert steps[0].audience == "startup"


def test_bridges_become_steps_with_their_own_action():
    c, a = thin_assessment()
    bridge = Bridge(
        id="B1",
        type="won_before_open_again",
        company=BridgeParty(name="Testi Oy"),
        counterparty=BridgeParty(name="Sansia Oy"),
        reason="Won the same class",
        evidence_company=[],
        evidence_counterparty=[],
        deadline=date(2026, 10, 30),
        action="Send the Sansia tender",
        confidence="verified",
    )
    steps = order(c, a, [], [], [bridge], today=TODAY)
    assert steps[0].opportunity_id == "B1" and steps[0].kind == "buyer" and steps[0].deadline == date(2026, 10, 30)


def test_a_bridge_to_a_listed_call_takes_the_opportunity_id_so_the_step_shows_its_tier():
    c, a = thin_assessment()
    page = "https://example.org/northern-blue"
    listed = Opportunity(
        id="FI:1234567-8:northern-blue",
        company_id="FI:1234567-8",
        kind="programme",
        title="Northern Blue (accelerator)",
        tier="possible",
        rule_source=page,
        action="Apply to Northern Blue",
    )
    bridge = Bridge(
        id="programme_fit/FI:1234567-8/northern-blue",
        type="programme_fit",
        company=BridgeParty(name="Testi Oy"),
        counterparty=BridgeParty(name="Programme call 4"),
        reason="Fits by stage and place",
        evidence_company=[],
        evidence_counterparty=[BridgeEvidence(claim="Applications open", url=page, tag="read")],
        action="Point to Northern Blue",
        confidence="probable",
    )
    steps = order(c, a, [listed], [], [bridge], today=TODAY)
    linked = [s for s in steps if s.opportunity_id == listed.id]
    assert len(linked) == 1  # one step for the call, though the titles differ
    assert (linked[0].kind, linked[0].action) == ("programme", "Point to Northern Blue")


def test_a_company_not_matched_for_certain_starts_with_confirming_the_match():
    c, a = thin_assessment()
    resolved = order(c, a, [opp("soon", "likely", date(2026, 10, 30))], [], [], today=TODAY)
    assert resolved[0].opportunity_id == "soon"
    probable = c.model_copy(
        update={"resolution": Resolution(state="probable", reason="Site matched by name"), "domain": "testi.fi"}
    )
    steps = order(probable, a, [opp("soon", "likely", date(2026, 10, 30))], [], [], today=TODAY)
    first = steps[0]
    assert (first.title, first.kind, first.audience) == ("Confirm the match", "confirm_match", "ecosystem_actor")
    assert "testi.fi shows business ID 1234567-8" in first.action and first.why == "Site matched by name"
    assert [s.opportunity_id for s in steps[1:3]] == ["soon", "ask_company:FI:1234567-8"]
    no_id = probable.model_copy(update={"registry": probable.registry.model_copy(update={"id": ""})})
    assert "national register" in order(no_id, a, [], [], [], today=TODAY)[0].action


def test_deadline_alerts_at_14_and_30_days():
    c = company()
    out = alerts(
        [],
        [c],
        [
            opp("a", "likely", date(2026, 10, 25)),
            opp("b", "possible", date(2026, 11, 10)),
            opp("c", "certain", date(2027, 1, 10)),
            opp("d", "excluded", date(2026, 10, 20)),
        ],
        today=TODAY,
    )
    assert [(x.id, x.priority, x.trigger) for x in out] == [
        ("deadline:a", "high", "deadline_14d"),
        ("deadline:b", "medium", "deadline_30d"),
    ]
    assert (out[0].opportunity_id, out[0].title) == ("a", "a")  # the instrument's name groups one deadline


def test_deadline_countdown_reads_today_tomorrow_or_in_n_days():
    due = [opp(oid, "likely", TODAY + timedelta(days=days)) for oid, days in (("a", 0), ("b", 1), ("c", 9))]
    out = alerts([], [company()], due, today=TODAY)
    assert [x.reasons[1] for x in out] == [
        "Deadline 17 Oct 2026, today",
        "Deadline 18 Oct 2026, tomorrow",
        "Deadline 26 Oct 2026, in 9 days",
    ]


def _signal(kind: str, when: date, seen: datetime, sensitive: bool = False) -> Signal:
    return Signal(
        id=f"s:{kind}:{when}",
        source="ted" if kind == "award" else "krek",
        type=kind,
        entity_ref=EntityRef(registry="prh", id="1234567-8"),
        event_date=when,
        first_seen_at=seen,
        hash="h",
        sensitivity="founder_sensitive" if sensitive else "public",
    )


def test_new_signals_on_listed_companies_only():
    c = company()
    fresh = datetime(2026, 10, 15, tzinfo=timezone.utc)
    out = alerts(
        [
            _signal("award", date(2026, 10, 14), fresh),
            _signal("share_issue", date(2026, 10, 1), fresh, sensitive=True),
            _signal("award", date(2025, 6, 1), fresh),
        ],  # an old award found today is history
        [c],
        [],
        today=TODAY,
    )
    assert [x.trigger for x in out] == ["new_award", "new_share_issue"]
    assert out[0].priority == "high"
    assert any("Founder-sensitive" in r for r in out[1].reasons)
    stranger = _signal("award", date(2026, 10, 14), fresh).model_copy(
        update={"entity_ref": EntityRef(registry="prh", id="7654321-0")}
    )
    assert alerts([stranger], [c], [], today=TODAY) == []
