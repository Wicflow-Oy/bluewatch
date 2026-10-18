"""The rubric against the 48 invented sample ideas (data/ideas/sample_ideas.json), the regression set for
four weaknesses it showed: English-only rules, no scope check, no negation, and a too-wide "Promising"."""

from __future__ import annotations

import json
from functools import cache

import pytest

from bluewatch.config import DATA_DIR
from bluewatch.ideas import queue, rubric
from bluewatch.ideas.models import IdeaAssessment, IdeaSubmission
from bluewatch.ideas.signals import negated, says
from bluewatch.ideas.vet import vet
from bluewatch.ideas.vocabulary import BUILT, TALKS

SAMPLE_PATH = DATA_DIR / "ideas" / "sample_ideas.json"
# The band each sample was written to show (kept here, not in the data file, so the file stays exactly
# what a team could submit).
THIN = ("S02", "S07", "S09", "S14", "S18", "S21", "S23", "S26", "S29", "S33", "S37", "S39", "S42", "S45")
PROMISING = ("S03", "S05", "S08", "S10", "S13", "S17", "S20", "S24", "S27", "S31", "S38", "S41", "S46")


@cache
def samples() -> dict[str, IdeaSubmission]:
    raw = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))["ideas"]
    fields = IdeaSubmission.model_fields
    return {i["sample_id"]: IdeaSubmission.model_validate({k: v for k, v in i.items() if k in fields}) for i in raw}


def read(sample_id: str, today) -> IdeaAssessment:
    return vet(samples()[sample_id], today=today)


def rungs(a: IdeaAssessment) -> dict[str, int | None]:
    return {c.id: c.rung for c in a.criteria}


def test_the_sample_file_says_it_is_invented():
    data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    assert data["synthetic"] is True and data["label"].startswith("Sample data: invented")
    assert len(samples()) == 48


# --------------------------------------------------------------------------- 1. Finnish and Swedish
@pytest.mark.parametrize("sample_id", ["S15", "S36"])
def test_strong_finnish_and_swedish_ideas_are_brought_now(sample_id, today):
    """S15 (fi, reed mowing) and S36 (sv, berth charging) read "Promising, medium" when the rules knew
    only English."""
    a = read(sample_id, today)
    assert (a.tier, a.potential, a.evidence) == ("bring_now", "high", "strong")
    assert rungs(a)["solution"] == 3 and rungs(a)["who_pays"] == 3 and rungs(a)["buyers"] == 3


def test_a_promising_finnish_idea_gets_its_two_questions(today):
    """S03 (fi, lost-net reporting) read "Not yet, low": its counted talks with fishers were invisible."""
    a = read("S03", today)
    assert a.tier == "ask_two" and a.potential != "low"
    assert rungs(a)["buyers"] == 2  # "Juttelimme kahdeksan kalastajan ... kanssa"


def test_finnish_and_swedish_quotes_are_the_teams_own_words(today):
    for sample_id in ("S15", "S27", "S36", "S08"):
        sub = samples()[sample_id]
        text = " ".join(getattr(sub, f) for f in ("problem", "who_has_it", "solution", "who_pays", "exists_detail"))
        quotes = [c.quote for c in read(sample_id, today).criteria if c.quote]
        assert quotes and all(q in text for q in quotes)


# --------------------------------------------------------------------------- 2. scope
def test_an_advertisement_reads_not_yet_and_says_why(today):
    """S12, an essay-writing ad, read "Promising, high potential"."""
    a = read("S12", today)
    assert a.tier == "not_yet" and a.tier_rule == rubric.TIER_REASONS["advert"]


def test_an_off_topic_idea_reads_not_yet_and_says_why(today):
    """S30, a marketplace for student overall patches (sv), read "Promising"."""
    a = read("S30", today)
    assert a.tier == "not_yet" and a.tier_rule == rubric.TIER_REASONS["off_topic"]


def test_every_other_sample_is_in_scope(today):
    scope = {rubric.TIER_REASONS["advert"], rubric.TIER_REASONS["off_topic"]}
    out = {sample_id for sample_id in samples() if read(sample_id, today).tier_rule in scope}
    assert out == {"S12", "S30"}  # S43, the token presale, is held for its instructions first


def test_public_records_are_never_scope_checked(today):
    live = queue.build_queue("apelago", "blue", [], today=today)
    scope = {rubric.TIER_REASONS["advert"], rubric.TIER_REASONS["off_topic"]}
    assert not [i.id for i in live.items if i.assessment.tier_rule in scope]


# --------------------------------------------------------------------------- 3. negation
@pytest.mark.parametrize("sample_id", ["S31", "S38"])
def test_not_having_talked_to_buyers_earns_no_buyer_credit(sample_id, today):
    """S31 "We have not talked to any cosmetics companies yet", S38 "We haven't talked to inspection
    companies yet": both earned buyer-contact credit."""
    a = read(sample_id, today)
    assert rungs(a)["buyers"] == 0
    assert not [c for c in a.ledger.claims if c.id.startswith("claim:buyer")]


def test_nothing_tested_yet_raises_no_form_mismatch(today):
    """S41 "Nothing has been tested in the sea yet" raised a false form_text_mismatch."""
    a = read("S41", today)
    assert "form_text_mismatch" not in [f.kind for f in a.flags]
    assert rungs(a)["built"] == 1  # research and a concept, as the form says


@pytest.mark.parametrize(
    ("sentence", "pattern"),
    [
        ("We haven't talked to any buyers yet.", TALKS),
        ("Nothing has been tested in the sea yet.", BUILT),
        ("Emme ole vielä haastatelleet ostajia.", TALKS),
        ("Mitään ei ole vielä testattu merellä.", BUILT),
        ("Vi har inte intervjuat några köpare än.", TALKS),
        ("Ingenting har testats i havet ännu.", BUILT),
    ],
)
def test_negation_in_three_languages(sentence, pattern):
    assert pattern.search(sentence) and not says(pattern, sentence)


def test_negation_stays_in_its_clause():
    sentence = "We have no customers yet, but we interviewed 11 skippers in June."
    m = TALKS.search(sentence)
    assert m and not negated(sentence, m.start()) and says(TALKS, sentence)


# --------------------------------------------------------------------------- 4. a narrower "Promising"
def test_thin_ideas_no_longer_land_in_promising_by_default(today):
    """10 of 14 thin samples read "Promising: ask two questions". Medium potential now needs at least some
    evidence; the thin ideas left in Promising are the ones whose every answer reads high."""
    promising = {sample_id: read(sample_id, today) for sample_id in THIN if read(sample_id, today).tier == "ask_two"}
    assert len(promising) <= 3
    assert all(a.potential == "high" for a in promising.values())
    for sample_id in ("S02", "S07", "S09", "S23", "S26", "S29", "S33", "S39", "S42", "S45"):
        a = read(sample_id, today)
        assert a.tier == "not_yet" and a.tier_rule == rubric.TIER_REASONS["medium_thin"], sample_id


def test_promising_ideas_stay_worth_a_look(today):
    tiers = {sample_id: read(sample_id, today).tier for sample_id in PROMISING}
    assert sum(t != "not_yet" for t in tiers.values()) >= 12
    assert tiers["S31"] == "not_yet"  # medium potential once its unmade buyer talks stop counting
