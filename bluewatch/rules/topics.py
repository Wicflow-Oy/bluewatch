"""One topic vocabulary for companies, grant themes and investor theses, so all three are compared
in the same words. A topic matches when one of its phrases occurs as a whole word."""

from __future__ import annotations

import re

from bluewatch.rules.text import find_phrases

TOPICS: dict[str, tuple[str, ...]] = {
    "ocean": (
        "ocean",
        "oceans",
        "marine",
        "sea",
        "seas",
        "blue",
        "coastal",
        "offshore",
        "subsea",
        "underwater",
        "sargassum",
        "fjord",
        "archipelago",
        "sdg 14",
    ),
    "maritime": (
        "maritime",
        "ship",
        "ships",
        "shipping",
        "shipbuilding",
        "vessel",
        "vessels",
        "port",
        "ports",
        "harbour",
        "harbours",
        "boat",
        "boats",
        "ferry",
        "ferries",
        "marina",
        "berths",
        "waterborne",
        "naval",
        "workboats",
        "watercraft",
    ),
    "aquaculture_food": (
        "aquaculture",
        "fish",
        "fishing",
        "fisheries",
        "seafood",
        "seaweed",
        "algae",
        "algal",
        "mussels",
        "shrimp",
        "salmon",
        "finfish",
        "shellfish",
        "fishmeal",
        "feed",
        "protein",
        "food",
    ),
    "water": (
        "water",
        "wastewater",
        "drinking water",
        "water quality",
        "water treatment",
        "nutrients",
        "phosphorus",
        "nitrogen",
        "watershed",
    ),
    "energy": (
        "energy",
        "power",
        "renewable",
        "renewables",
        "wind",
        "wave energy",
        "tidal",
        "electric",
        "electrification",
        "charging",
        "battery",
        "hydrogen",
        "fuels",
    ),
    "climate": (
        "climate",
        "emissions",
        "decarbonisation",
        "net zero",
        "net-zero",
        "co2",
        "carbon",
        "ghg",
        "greenhouse",
        "low-carbon",
        "1.5",
    ),
    "circular": (
        "circular",
        "circularity",
        "recycled",
        "recycling",
        "waste",
        "by-products",
        "biodegradable",
        "upcycling",
        "reuse",
        "plastic",
        "plastics",
        "biomaterials",
        "bio-based",
    ),
    "nature": (
        "biodiversity",
        "ecosystem",
        "ecosystems",
        "restoration",
        "habitat",
        "habitats",
        "reef",
        "reefs",
        "nature",
        "marine health",
    ),
    "data_digital": ("data", "digital", "ai", "software", "platform", "analytics", "saas", "app"),
    "sensing": (
        "sensor",
        "sensors",
        "monitoring",
        "observation",
        "satellite",
        "iot",
        "buoy",
        "sonar",
        "rov",
        "rovs",
        "auv",
        "usv",
        "drone",
        "drones",
        "underwater imaging",
        "measurement",
        "analyser",
    ),
    "transport": ("transport", "transportation", "logistics", "mobility"),
    "pollution": ("pollution", "oil spill", "oil spills", "microplastics", "contamination", "marine pollution"),
}

# Theme texts that open a call to any sector.
_GENERIC = ("any", "general", "sector-agnostic", "generalist")


def topics_of(text: str) -> set[str]:
    # Machine theme ids ("blue_economy", "ocean_water_maritime") read as words; parentheticals are
    # caveats ("maritime relevance not confirmed"), not themes.
    cleaned = re.sub(r"\([^)]*\)", " ", text.replace("_", " "))
    return {topic for topic, phrases in TOPICS.items() if find_phrases(cleaned, phrases)}


BLUE_FAMILY = frozenset({"ocean", "maritime", "aquaculture_food", "water"})


def shared_topics(theme_text: str, company_topics: set[str] | frozenset[str]) -> set[str]:
    """Topics a theme and a company share. A broad ocean theme ("blue economy", "marine") accepts
    any blue-economy company: an aquaculture or port company is an ocean company."""
    wanted = topics_of(theme_text)
    shared = wanted & set(company_topics)
    if "ocean" in wanted and set(company_topics) & BLUE_FAMILY:
        shared.add("ocean")
    return shared


def is_generic(text: str) -> bool:
    return bool(find_phrases(re.sub(r"\([^)]*\)", " ", text.replace("_", " ")), _GENERIC)) or "ANY" in text
