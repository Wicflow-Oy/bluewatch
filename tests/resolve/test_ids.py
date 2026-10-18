import pytest

from bluewatch.resolve.ids import (
    find_ids,
    normalise_id,
    normalise_vat,
    parse_token,
    valid_ee_registry_code,
    valid_fi_business_id,
    valid_no_orgnr,
    vat_to_registry_id,
)


@pytest.mark.parametrize("bid", ["2855258-7", "3558526-4", "2018415-0", "2506251-5", "2896110-2", "3480010-2"])
def test_real_finnish_business_ids_pass(bid):
    assert valid_fi_business_id(bid)


@pytest.mark.parametrize("bid", ["1234567-8", "2855258-6", "2855258", "28552587-1", "", "abcdefg-h"])
def test_bad_finnish_business_ids_fail(bid):
    assert not valid_fi_business_id(bid)


def test_finnish_forms_normalise():
    assert normalise_id("FI", "FI28552587") == "2855258-7"
    assert normalise_id("FI", "28552587") == "2855258-7"
    assert normalise_id("FI", "2855258–7") == "2855258-7"  # en dash, as pages write it
    assert normalise_id("FI", "1234567-8") is None  # judge test 14: a bad checksum is rejected


def test_norwegian_org_numbers():
    assert valid_no_orgnr("912288161")  # HYKE AS
    assert valid_no_orgnr("936 106 404")  # NORSEPOWER AS
    assert not valid_no_orgnr("912288162")
    assert normalise_id("NO", "NO 912 288 161 MVA") == "912288161"


def test_estonian_registry_codes():
    assert valid_ee_registry_code("12417834")
    assert valid_ee_registry_code("17608303")  # from the RIK fixture
    assert not valid_ee_registry_code("12417835")
    assert not valid_ee_registry_code("1241783")


def test_vat_numbers_map_to_registry_ids():
    assert normalise_vat("fi 2855 2587") == "FI28552587"
    assert vat_to_registry_id("FI28552587") == ("FI", "2855258-7")
    assert vat_to_registry_id("NO912288161MVA") == ("NO", "912288161")
    assert vat_to_registry_id("EE101234567") is None  # Estonian VAT numbers are not registry codes
    assert normalise_vat("FI12345678") is None


def test_parse_token():
    assert parse_token("FI:2855258-7") == ("FI", "2855258-7")
    assert parse_token("VAT:FI28552587") == ("FI", "2855258-7")
    assert parse_token("FI:1234567-8") is None


def test_find_ids_on_a_footer():
    text = "Seaber Oy | Y-tunnus 2855258-7 | ALV FI28552587 | Org.nr. 912 288 161 | Registrikood 12417834"
    found = find_ids(text)
    assert {"FI:2855258-7", "VAT:FI28552587", "NO:912288161", "EE:12417834"} <= set(found)


def test_unlabelled_nine_digit_numbers_are_not_org_numbers():
    assert find_ids("Call 912288161 or order 936106404") == []


def test_many_bare_id_shaped_numbers_are_ignored():
    # Kongsberg's homepage produced dozens of ID-shaped codes, some checksum-valid by chance; a page
    # full of them is not a footer. These six are synthetic but valid.
    codes = " ".join(["0100000-2", "0877777-0", "1655554-5", "3988885-2", "4766662-7", "5544439-7"])
    assert find_ids(codes) == []
    assert find_ids(codes + " Y-tunnus FI28552587") == ["VAT:FI28552587", "FI:2855258-7"]
