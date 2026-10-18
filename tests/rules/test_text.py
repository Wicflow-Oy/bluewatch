from bluewatch.rules.text import humanise_keys, trunc


def test_humanise_keys_turns_data_keys_in_prose_into_words():
    assert humanise_keys("Theme fit: data_digital, ocean") == "Theme fit: data and digital, ocean"
    assert humanise_keys("Open to small_midcap_equity_only, spin_out") == "Open to small midcap equity only, spin out"
    assert humanise_keys("no open call now (no_open_call)") == "no open call now (no open call)"
    plain = "Registered 12 Oct 2026 (PRH); site havnio.no"
    assert humanise_keys(plain) == plain


def test_trunc_floors_and_never_rounds_up():
    assert trunc(0.975) == "0.97"
    assert trunc(0.29) == "0.29"  # float error must not floor it to 0.28
    assert trunc(1.0) == "1.00"
    assert trunc(8.96, 0) == "8" and trunc(2.96, 1) == "2.9"
