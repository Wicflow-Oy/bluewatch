"""What a bridge shows a reader: no research notes, no register IDs where names can be hidden."""

import re

from bluewatch.bridges.rank import all_bridges
from bluewatch.bridges.seed import seed_bridges

# Pointers into our own research files and worksheets, and notes on how a line was found.
RESEARCH_NOTE = re.compile(
    r"\.json|dossier|\brow \d|\bP\d\b|search-summary|search snippet|search-result|§|weak blue fit|\(site\)",
    re.I,
)


def _texts(bridge):
    yield bridge.reason
    yield bridge.action
    yield bridge.caveat or ""
    yield bridge.counterparty.name
    for item in bridge.evidence_company + bridge.evidence_counterparty:
        yield item.claim


def test_no_bridge_shows_research_notes(today):
    for bridge in all_bridges(today):
        for text in _texts(bridge):
            assert not RESEARCH_NOTE.search(text), f"{bridge.id}: {text}"


def test_company_claims_leave_the_register_id_to_the_source_link(today):
    # Hiding names swaps the name in the text; an ID written into a claim would still name the company.
    for bridge in all_bridges(today):
        registry_id = bridge.company.registry_id
        if registry_id:
            assert all(registry_id not in e.claim for e in bridge.evidence_company), bridge.id


def test_generated_ids_are_short_unique_and_name_no_one(today):
    bridges = all_bridges(today)
    assert len({b.id for b in bridges}) == len(bridges)
    for bridge in bridges:
        if bridge.generator != "seed":
            assert re.fullmatch(rf"{bridge.type}-[0-9a-f]{{8}}", bridge.id), bridge.id


def test_ids_stay_the_same_between_runs(today):
    first = [b.id for b in all_bridges(today)]
    all_bridges.cache_clear()
    assert [b.id for b in all_bridges(today)] == first


def test_research_teams_are_not_called_companies():
    by_id = {b.id: b for b in seed_bridges()}
    assert by_id["B4"].company.kind == by_id["B10"].company.kind == "research_group"
    assert by_id["B1"].company.kind == "company"


def _as_hidden(text: str, bridge) -> str:
    """The text as Hide names shows it: the name and each identifying term out (screens/bridges/hideNames.ts)."""
    text = text.replace(bridge.company.name, "")
    for term in sorted(bridge.identifying_terms, key=len, reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(term)}", "", text, flags=re.I)
    return text


def _hidden_texts(bridge) -> str:
    return " | ".join(_as_hidden(text, bridge) for text in _texts(bridge))


def test_hidden_names_hide_a_research_teams_project_and_organisation(today):
    # "MARPOWER team, LAPPEENRANNAN-LAHDEN TEKNILLINEN YLIOPISTO LUT (research output)"
    teams = [b for b in all_bridges(today) if b.company.kind == "research_group"]
    assert len(teams) > 10
    name = re.compile(r"(.+?) team(?:,| at) (.+) \(research output\)")
    for bridge in teams:
        project, organisation = name.fullmatch(bridge.company.name).groups()
        shown = _hidden_texts(bridge)
        assert project.casefold() not in shown.casefold(), bridge.id
        assert organisation.casefold() not in shown.casefold(), bridge.id


def test_hidden_names_hide_the_shared_project_and_the_products(today):
    by_id = {b.id: b for b in all_bridges(today)}
    assert "MISSION" not in _hidden_texts(by_id["B3"])
    for bridge in by_id.values():
        if bridge.type == "already_works_with" and bridge.generator != "seed":
            project = re.search(r"project (\S+), which runs", bridge.reason).group(1)
            assert project not in _hidden_texts(bridge), bridge.id
    for name, product in [
        ("Tethys Robotics", "Tethys ONE"),
        ("Groke Technologies", "Groke PRO"),
        ("Datadeck Oy", "DataDeck"),
    ]:
        bridges = [b for b in by_id.values() if b.company.name == name]
        assert bridges and all(product not in _hidden_texts(b) for b in bridges), name


def test_caveats_speak_to_the_reader_not_of_our_own_rules(today):
    for bridge in all_bridges(today):
        assert "never rank" not in (bridge.caveat or ""), bridge.id
