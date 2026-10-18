import pytest

from bluewatch.read.fetch import page_from_html
from bluewatch.read.keywords import classify_keywords
from tests.read.fakes import html

BLUE_OCEAN_ROBOTICS = [
    "Blue Ocean Robotics - We Create and Commercialize Robots",
    "We develop, produce and sell professional service robots in various industries such as pharmaceutical, "
    "hospitality, and other global markets.",
]


def test_ocean_in_the_company_name_is_not_evidence():
    result = classify_keywords(BLUE_OCEAN_ROBOTICS, company_names=["Blue Ocean Robotics"])
    assert not result.blue
    assert "company's own name" in result.reason


@pytest.mark.parametrize(
    "text, vertical",
    [
        ("Kehitämme vesiviljelyn automaatiota kalankasvattajille.", "blue_biotech_water"),  # FI
        ("Vi automatiserar fiskodling i hela Norden.", "blue_biotech_water"),  # SV
        ("Vi leverer programvare til havbruk og fiskeoppdrett.", "blue_biotech_water"),  # NO
        ("Arendame laevandus tarkvara sadamatele.", "maritime_ports"),  # ET
        ("Floating solar and offshore wind for island grids.", "ocean_infra_clean_energy"),  # EN
        ("Sonar mapping of the seabed for ports.", "marine_intelligence"),
    ],
)
def test_terms_in_five_languages(text, vertical):
    result = classify_keywords([text])
    assert result.blue and result.vertical == vertical
    assert result.quote and result.quote in text  # cut from the page itself


@pytest.mark.parametrize(
    "parts",
    [
        ["Linen towels made in Finland. Free shipping on orders over 50 EUR."],
        ["Market research, sales reports and analyst support for retail chains."],
        ["Book a room with a sea view. Guests can join our summer boat trips."],
    ],
)
def test_traps_are_not_blue(parts):
    assert not classify_keywords(parts).blue


def test_general_ocean_terms_say_blue_without_guessing_a_vertical():
    result = classify_keywords(
        ["Nemo Seafarms is a biodiversity positive business operating in the Baltic Sea."],
        company_names=["Nemo Seafarms"],
    )
    assert result.blue and result.vertical is None
    assert result.quote.startswith("Nemo Seafarms is a biodiversity")


def test_long_sentences_give_a_short_quote_from_the_original_text():
    body = "Lorem ipsum dolor sit amet " * 20 + "with smart aquaculture technology " + "and more words " * 20
    page = page_from_html("https://x.fi/", html("X", f"<p>{body}</p>"))
    result = classify_keywords(page.quotable())
    assert result.blue and len(result.quote) <= 220
    assert result.quote in page.text and "aquaculture" in result.quote
