import pytest

from bluewatch.rules.calibration import answer_key_agreement, key_band
from bluewatch.rules.presets import load_preset, preset_names
from bluewatch.rules.version import rules_version


def test_both_presets_load_with_the_same_engine_shape():
    assert {"blue", "climate_circular"} <= set(preset_names())
    blue, climate = load_preset("blue"), load_preset("climate_circular")
    assert blue.verticals.keys() != climate.verticals.keys()
    assert blue.house_fund and blue.house_fund.investor_id == "redstone-blue"
    assert climate.house_fund is None
    with pytest.raises(KeyError):
        load_preset("no-such-preset")


def test_rules_version_is_a_stable_hash():
    assert rules_version() == rules_version()
    assert rules_version().startswith("rules-") and len(rules_version()) == len("rules-") + 12


def test_answer_key_bands_parse():
    assert key_band("7-8 (product in commercial use)") == (7, 8)
    assert key_band("9 (type-approved)") == (9, 9)
    assert key_band("4-6 [inferred]") == (4, 6)
    assert key_band("unknown (inferred 3-5)") is None
    assert key_band("Not applicable (operator)") == "n/a"


def test_calibration_measures_without_thresholds():
    report = answer_key_agreement()
    for key in ("trl", "brl"):
        stats = report[key]
        assert stats["n_keyed"] > 0
        assert stats["answered"] + stats["abstained"] == stats["n_keyed"]
        assert stats["exact"] <= stats["within_one"] <= stats["answered"]
