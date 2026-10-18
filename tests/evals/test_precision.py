import json
from datetime import datetime, timezone

import pytest

from bluewatch.evals.keys import KeyRow, band, load_keys, merge, stage
from bluewatch.evals.precision import AGE_EDGES, freeze, report
from bluewatch.evals.traps import load_cases, run_traps
from bluewatch.models import Assessment, ReadinessLevel, Resolution, Score

AT = datetime(2026, 10, 17, tzinfo=timezone.utc)


def assessment(company_id: str, confidence: str = "medium", **levels: int | None) -> Assessment:
    return Assessment(
        company_id=company_id,
        levels=[ReadinessLevel(key=k, level=v, confidence=confidence) for k, v in levels.items()],
        dimensions=[],
        score=Score(potential=0.5, evidence=0.5, group="dive_deeper"),
        rules_version="rules-test",
        assessed_at=AT,
    )


def midpoint(interval):
    return None if interval is None else (interval[0] + interval[1]) // 2


IRL_LEVEL = {0: 5, 1: 8, 2: 9}  # a level that sits in each investment stage


def oracle() -> dict[str, Assessment]:
    """An engine that answers every numeric key with the key's own middle level."""
    out = {}
    for i, row in enumerate(merge(load_keys())):
        irl = row.bands["irl"]
        out[row.name] = assessment(
            f"XX:{i}",
            trl=midpoint(row.bands["trl"]),
            brl=midpoint(row.bands["brl"]),
            irl=IRL_LEVEL[irl[0]] if irl else None,
        )
    return out


def run(assessments, tmp_path, **kw):
    return report(assessments, with_traps=False, frozen_path=tmp_path / "frozen.json", **kw)


def test_parser_matches_the_recorded_bench_counts():
    rows = load_keys()
    assert len(rows) == 72
    assert sum(1 for r in rows if r.bands["trl"]) == 47 and sum(1 for r in rows if r.bands["brl"]) == 37
    merged = merge(rows)
    assert len(merged) == 70  # Kelluu and Sensemakers appear in two key files
    kelluu = next(r for r in merged if "FI:2902007-2" in r.ids)
    assert kelluu.bands["trl"] == (7, 8) and kelluu.registered.isoformat() == "2018-03-14"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("6-7 (inferred)", (6, 7)),
        ("9 (type-approved)", (9, 9)),
        ("unknown (inferred 3-5)", None),
        ("Ingredients 6-7; biorefinery 5-6", None),
        ("Not applicable (operator)", None),
        ("medium", (4, 6)),
    ],
)
def test_band(text, expected):
    assert band(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("pre-seed to seed (inferred)", (0, 1)),
        ("growth (Series A closed April 2026)", (2, 2)),
        ("Public company", (2, 2)),
        ("Seed-type rounds per aggregators", (1, 1)),
        ("Not verified", None),
        ("Round of about EUR 4.5M; date unknown, so the stage cannot be fixed", None),
    ],
)
def test_stage(text, expected):
    assert stage(text) == expected


def test_an_engine_that_agrees_with_the_keys_scores_full_marks(tmp_path):
    result = run(oracle(), tmp_path)
    for level in result.levels[:3]:
        assert level.n > 0 and level.exact == level.n and level.within_one == level.n
        assert sum(sum(row.values()) for row in level.confusion.values()) == level.n
    trl, brl = result.levels[0], result.levels[1]
    assert trl.weighted_kappa == 1.0 and brl.weighted_kappa == 1.0
    assert result.levels[3].key == "oirl" and result.levels[3].n == 0


def test_one_wrong_answer_costs_one_exact(tmp_path):
    engine = oracle()
    before = run(engine, tmp_path).levels[0]
    engine["Norsepower"] = assessment("XX:norse", trl=2)  # key 9
    after = run(engine, tmp_path).levels[0]
    assert after.exact == before.exact - 1 and after.within_one == before.within_one - 1
    assert after.confusion["7-9"]["1-3"] == 1


def test_the_age_baseline_is_scored_on_the_same_companies(tmp_path):
    """An engine that only looks at company age must score exactly what the age baseline scores."""
    today = AT.date()
    engine = {}
    for i, row in enumerate(merge(load_keys())):
        if row.registered:
            age = (today - row.registered).days / 365.25
            b = 0 if age < AGE_EDGES[0] else 1 if age < AGE_EDGES[1] else 2
            engine[row.name] = assessment(f"XX:{i}", trl=b * 3 + 2, brl=b * 3 + 2, irl=IRL_LEVEL[b])
    result = run(engine, tmp_path, today=today)
    for level in result.levels[:3]:
        assert (level.exact, level.within_one) == (level.baseline_exact, level.baseline_within_one)
    assert result.levels[1].n > 0


def test_abstaining_is_counted_not_scored(tmp_path):
    result = run({row.name: assessment(f"XX:{i}") for i, row in enumerate(merge(load_keys()))}, tmp_path)
    assert all(level.n == 0 for level in result.levels)
    assert any("we answered 0 of 46" in note for note in result.notes)


def test_keys_that_straddle_a_band_edge_are_left_out_of_n(tmp_path):
    rows = [
        KeyRow(group="partner", name=f"C{i}", ids={f"FI:{i}"}, bands={"trl": iv})
        for i, iv in enumerate([(6, 7), (4, 6), (1, 3)])
    ]
    result = run([assessment(f"FI:{i}", trl=6) for i in range(3)], tmp_path, keys=rows)
    trl = result.levels[0]
    assert (trl.n, trl.exact, trl.within_one) == (2, 1, 1)
    assert any("1 of those keys straddles a band edge and is left out of n" in note for note in result.notes)
    assert any("of 3 companies with a numeric key" in note for note in result.notes)


def test_assessments_match_by_register_id(tmp_path):
    result = run([assessment("FI:2506251-5", confidence="high", trl=3)], tmp_path)  # Norsepower, key 9
    assert result.levels[0].n == 1 and result.levels[0].exact == 0
    assert any("Matched 1 of 70" in note for note in result.notes)
    assert any("more than one level off: 1 of 1" in note for note in result.notes)


def test_freeze_records_the_rules_hash_and_time(tmp_path):
    path = tmp_path / "frozen.json"
    record = freeze(path, rules_hash="rules-test", now=AT)
    assert json.loads(path.read_text(encoding="utf-8")) == record
    assert record["rules_hash"] == "rules-test" and record["frozen_at"] == AT.isoformat()
    assert report(oracle(), with_traps=False, frozen_path=path).frozen_at == AT
    changed = report(
        {"Norsepower": assessment("XX:1", trl=9).model_copy(update={"rules_version": "rules-new"})},
        with_traps=False,
        frozen_path=path,
    )
    assert changed.frozen_at is None and any("rules changed since the freeze" in n for n in changed.notes)


def test_freeze_uses_the_rules_version_by_default(tmp_path):
    version = pytest.importorskip("bluewatch.rules.version")
    assert freeze(tmp_path / "f.json")["rules_hash"] == version.rules_version()


def naive(name, *, country, registry_id=None, domain=None, page_ids=(), candidates=()):
    """The naive resolver the traps exist to catch: take the first search hit."""
    if not candidates:
        return Resolution(state="unresolved", reason="no candidates")
    return Resolution(state="resolved", reason="top hit", candidates=list(candidates))


def scripted(name, *, country, registry_id=None, domain=None, page_ids=(), candidates=()):
    """A resolver that answers each trap the way the case expects."""
    case = next(c for c in load_cases() if c["input"]["name"] == name and c["input"].get("domain") == domain)
    expect = case["expect"]
    gold = [c for c in candidates if c.registry.id == expect["gold"]]
    state = expect["ok_states"][0]
    return Resolution(state=state, reason="scripted", candidates=gold + [c for c in candidates if c not in gold])


def test_traps_catch_a_naive_resolver():
    results = {r.case.split()[0]: r for r in run_traps(naive)}
    assert len(results) == 10
    assert not results["T1"].passed and "wrong company (3431445-4)" in results["T1"].note
    assert not results["T3"].passed and not results["T8"].passed
    assert results["T6"].passed and results["T7"].passed


def test_traps_pass_a_careful_resolver():
    assert all(r.passed for r in run_traps(scripted))


def test_traps_run_on_the_real_resolver_when_it_exists():
    pytest.importorskip("bluewatch.resolve.resolver")
    results = run_traps()
    assert len(results) == 10 and all(r.got for r in results)
