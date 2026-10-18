from datetime import date, datetime, timezone

import pytest

from bluewatch.models import EntityRef, Signal
from bluewatch.rules.assess import assess
from bluewatch.rules.rank import shortlist
from bluewatch.rules.seed_adapter import demo_items
from tests.rules.helpers import company, ev, registered

TODAY = date(2026, 10, 17)


@pytest.fixture(scope="module")
def pack():
    return demo_items()


def _items(pack, preset="blue"):
    return [(c, assess(c, e, preset=preset), e, s) for c, e, s in pack]


def test_at_most_cap_and_never_padded():
    few = []
    for i in range(3):
        cid = f"FI:100000{i}-1"
        c = company(cid, name=f"Harbour {i} Oy", one_liner="Mobile payment for guest harbours")
        evidence = [registered(cid), ev("Mobile payment for guest harbours", cid=cid)]
        few.append((c, assess(c, evidence), evidence, []))
    sl = shortlist(few, mode="apelago", cap=10, today=TODAY)
    assert len(sl.entries) == 3
    assert sl.why_not_next.startswith("Only 3 rows qualified, so the other slots stay empty")
    assert shortlist(few[:1], mode="apelago", cap=10, today=TODAY).why_not_next.startswith("Only 1 row qualified")
    assert len(shortlist(few, mode="apelago", cap=2, today=TODAY).entries) == 2


def test_ranking_is_reproducible_from_rank_parts(pack):
    sl = shortlist(_items(pack), mode="redstone", today=TODAY)
    assert len(sl.entries) == sl.cap == 10
    totals = []
    for e in sl.entries:
        parts = {k: v for k, v in e.rank_parts.items() if k != "total"}
        assert abs(sum(parts.values()) - e.rank_parts["total"]) < 1e-3
        totals.append((-e.rank_parts["total"], e.company_id))
    assert totals == sorted(totals)
    assert [e.rank for e in sl.entries] == list(range(1, 11))
    assert sl.why_these and sl.why_not_next and sl.rules_version.startswith("rules-")


def test_three_reasons_each_tied_to_the_items_evidence(pack):
    items = _items(pack)
    evidence_ids = {e.id for _, _, ev_list, _ in items for e in ev_list}
    for entry in shortlist(items, mode="apelago", today=TODAY).entries:
        assert 1 <= len(entry.reasons) <= 3
        assert all(r.evidence_id in evidence_ids and r.source_label for r in entry.reasons)


def test_modes_filter_rows(pack):
    items = _items(pack)
    apelago = shortlist(items, mode="apelago", cap=200, today=TODAY)
    redstone = shortlist(items, mode="redstone", cap=200, today=TODAY)
    cohort = {c.id for c, *_ in items if "apelago_cohort" in c.tags}
    assert cohort and not cohort & {e.company_id for e in apelago.entries}  # already in A'Pelago's list
    assert cohort & {e.company_id for e in redstone.entries}
    for entry in apelago.entries:  # share issues never surface a row, or a reason, in A'Pelago mode
        assert not any("Share issue" in r.text for r in entry.reasons)
    assert all(e.group != "not_for_us" for e in redstone.entries)


def _listed(n: int, founded: date, award: date | None = None) -> tuple:
    cid = f"FI:100000{n}-1"
    c = company(cid, name=f"Harbour {n} Oy", founded=founded, one_liner="Mobile payment for guest harbours")
    evidence = [registered(cid, founded), ev("Mobile payment for guest harbours", cid=cid)]
    signals = (
        []
        if award is None
        else [
            Signal(
                id=f"s:{cid}",
                source="ted",
                type="award",
                entity_ref=EntityRef(registry="prh", id=cid[3:]),
                event_date=award,
                first_seen_at=datetime(2026, 10, 17, tzinfo=timezone.utc),
                hash="h",
                title="TED award: harbour payment system",
            )
        ]
    )
    return c, assess(c, evidence), evidence, signals


def test_change_markers_come_from_register_and_signal_dates_only():
    since = datetime(2026, 10, 12, 7, tzinfo=timezone.utc)
    items = [
        _listed(1, date(2026, 10, 14)),  # registered after the digest
        _listed(2, date(2026, 9, 1), award=date(2026, 10, 15)),
        _listed(3, date(2026, 9, 1), award=date(2026, 10, 7)),  # first seen after the digest, dated before it
        _listed(4, date(2026, 10, 12)),  # registered on the digest day itself
    ]
    change = {e.name: e.change for e in shortlist(items, mode="apelago", since=since, today=TODAY).entries}
    assert change == {
        "Harbour 1 Oy": "new since you last looked",
        "Harbour 2 Oy": "changed: TED award: harbour payment system",
        "Harbour 3 Oy": None,
        "Harbour 4 Oy": None,
    }
    assert all(e.change is None for e in shortlist(items, mode="apelago", today=TODAY).entries)


def test_why_not_next_names_a_tie_and_never_rounds_up():
    items = [_listed(n, date(2026, 9, 1)) for n in range(3)]  # three identical rows
    short = shortlist(items, mode="apelago", cap=2, today=TODAY)
    total = short.entries[1].rank_parts["total"]
    assert f"#3 would be Harbour 2 Oy, tied with #2 Harbour 1 Oy at {total:.4f}" in short.why_not_next
    assert "ordered by company ID" in short.why_not_next


def test_the_climate_preset_reranks_the_same_companies(pack):
    blue = [e.company_id for e in shortlist(_items(pack, "blue"), mode="apelago", today=TODAY).entries]
    climate = [e.company_id for e in shortlist(_items(pack, "climate_circular"), mode="apelago", today=TODAY).entries]
    assert blue != climate
    assert "FI:3652359-1" in blue and "FI:3652359-1" not in climate  # aquaculture consulting is off a climate thesis
