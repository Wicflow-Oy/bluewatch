from collections import Counter

from bluewatch.bridges.seed import seed_bridges
from bluewatch.models import BridgeType


def test_ten_seed_bridges_cover_all_seven_types():
    bridges = seed_bridges()
    assert [b.id for b in bridges] == [f"B{i}" for i in range(1, 11)]
    assert {b.type for b in bridges} == set(BridgeType.__args__)
    assert Counter(b.confidence for b in bridges) == {"verified": 4, "probable": 2, "possible": 4}
    assert all(b.generator == "seed" for b in bridges)


def test_every_seed_bridge_has_evidence_on_both_sides():
    for bridge in seed_bridges():
        assert bridge.evidence_company and bridge.evidence_counterparty, bridge.id


def test_alpo_has_a_register_description_for_hidden_names():
    by_id = {b.id: b for b in seed_bridges()}
    for bridge_id in ("B1", "B2"):
        assert by_id[bridge_id].anonymised_name == "A Rauma boat builder"
        assert by_id[bridge_id].company.registry_id == "3101791-3"


def test_missing_seed_ids_are_linked_only_by_exact_name():
    by_id = {b.id: b for b in seed_bridges()}
    assert by_id["B3"].company.registry_id is None  # the seed's own field stays as written
    assert by_id["B3"].company.company_id == "FI:2945733-8"  # Awake.AI in startups.json
    assert by_id["B5"].company.company_id == "FI:2982879-2"  # Origin by Ocean
    assert by_id["B10"].company.company_id is None  # a research team, not a company
