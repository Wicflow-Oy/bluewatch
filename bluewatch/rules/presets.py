"""Theses as config: each preset (data/presets/*.json) sets verticals, keywords, topics, the stage
window, weights and thresholds. The engine is the same for every preset; only these numbers change."""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, ConfigDict

from bluewatch.config import DATA_DIR

PRESETS_DIR = DATA_DIR / "presets"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PresetVertical(_Strict):
    label: str
    keywords: list[str]


class ImpactFramework(_Strict):
    name: str
    note: str
    areas: dict[str, list[str]]


DEFAULT_MAX_AGE_YEARS = 15.0  # a preset that sets no age limit of its own


class StageWindow(_Strict):
    irl_min: int
    irl_max: int
    max_age_years: float = DEFAULT_MAX_AGE_YEARS


class HouseFund(_Strict):
    investor_id: str
    label: str


class Weights(_Strict):
    potential: dict[str, float]
    evidence: dict[str, float]
    rank: dict[str, float]
    investor: dict[str, float]


class Thresholds(_Strict):
    promising: float
    solid_evidence: float
    off_thesis: float


class Windows(_Strict):
    newborn_weeks: int
    newly_active_days: int


class Preset(_Strict):
    name: str
    label: str
    description: str
    verticals: dict[str, PresetVertical]
    vertical_prior: dict[str, float]  # keyed by Company.vertical; "none" when unclassified
    off_thesis_keywords: list[str]
    grant_topics: list[str]
    investor_topics: list[str]
    impact: ImpactFramework
    stage_window: StageWindow
    ticket_eur: tuple[int, int]
    house_fund: HouseFund | None
    programmes: list[str]
    weights: Weights
    traction_bonus: float
    thresholds: Thresholds
    windows: Windows


def preset_names() -> list[str]:
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json"))


@lru_cache(maxsize=None)
def load_preset(name: str) -> Preset:
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        raise KeyError(f"unknown preset {name!r}; available: {', '.join(preset_names())}")
    return Preset.model_validate_json(path.read_text(encoding="utf-8"))
