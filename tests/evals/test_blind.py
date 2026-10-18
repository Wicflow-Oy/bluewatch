import json

from bluewatch.config import DATA_DIR
from bluewatch.evals.blind import load_blind_set, score_blind_set
from tests.evals.test_precision import assessment

EXAMPLE = DATA_DIR / "eval" / "precision" / "blind_set_example.csv"


def test_the_example_file_parses():
    rows = load_blind_set(EXAMPLE)
    assert [r.name for r in rows] == ["Valkama Watercrafts", "NanoHalen", "Kelluu", "Norsepower"]
    kelluu = rows[2]
    assert kelluu.ids == {"FI:2902007-2"} and kelluu.bands == {"trl": (7, 9), "brl": (6, 7), "irl": (2, 2)}
    assert rows[3].bands["irl"] is None  # "unknown": they would not commit


def test_a_blind_set_is_scored_side_by_side():
    ours = [
        assessment("FI:3274823-2", trl=6, brl=4, irl=5),  # Valkama
        assessment("FI:3399187-5", trl=7, brl=2),  # NanoHalen: TRL key 4-5
        assessment("FI:2902007-2", trl=8, brl=6, irl=9),  # Kelluu
    ]
    result = score_blind_set(EXAMPLE, assessments=ours)
    trl = result.levels[0]
    assert result.blind and (trl.n, trl.exact, trl.within_one) == (2, 1, 1)  # Valkama 6-7 straddles
    assert trl.weighted_kappa is None  # too few rows for kappa
    notes = "\n".join(result.notes)
    assert "Partner row NanoHalen: TRL ours 7 / yours 4-5 (differs)" in notes
    assert (
        "Partner row Kelluu: TRL ours 8 / yours 7-9 (same band); BRL ours 6 / yours 6-7 (within one); "
        "stage ours Series A or later / yours Series A or later (same band)." in notes
    )
    assert "Partner row Norsepower: not in our assessments." in notes


def test_a_json_blind_set_by_name(tmp_path):
    path = tmp_path / "blind.json"
    path.write_text(
        json.dumps({"companies": [{"company": "Meriva Oy", "trl": "unknown", "brl": "low"}]}), encoding="utf-8"
    )
    result = score_blind_set(path, assessments={"Meriva Oy": assessment("FI:3652359-1", brl=2)})
    assert (result.levels[1].n, result.levels[1].exact) == (1, 1)
    assert result.reference.endswith(": 1 company from your own assessments")
