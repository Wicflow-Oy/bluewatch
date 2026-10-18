"""Claude's recorded reads of public leads: replayed offline, quote-checked again, never trusted blindly."""

from __future__ import annotations

from bluewatch.ideas import public_reads
from bluewatch.ideas.queue import build_queue
from bluewatch.read.quotecheck import quote_in_page

FIELDS = ("problem", "who_has_it", "solution", "who_pays", "exists_detail")


def leads(today):
    """The leads the reads were recorded for: every lead public from `today` through the recorded week."""
    return public_reads.week_of_leads(today)


def test_the_recorded_file_is_public_data_with_source_and_date():
    data = public_reads.recorded()
    assert data["label"] == public_reads.READ_LABEL and data["read_at"] == public_reads.READ_AT
    assert data["reads"] and all(r["source_url"].startswith("https://") for r in data["reads"].values())
    assert all(reason == "title only" for lead, reason in data["skipped"].items() if lead.startswith("research:"))


def test_every_replayed_field_and_claim_quotes_the_public_description(today):
    judged = 0
    for lead_id in public_reads.recorded()["reads"]:
        p = leads(today)[lead_id]
        sub, claims, reader, note = public_reads.prepared(p)
        if reader == "rules":
            assert note.startswith("Not judged yet:")  # Claude found the description too thin
            continue
        judged += 1
        assert note == public_reads.READ_LABEL
        for f in FIELDS:
            if getattr(sub, f) != getattr(p.submission, f):
                assert quote_in_page(getattr(sub, f), p.description)
        for c in claims:
            assert quote_in_page(c.quote, getattr(sub, c.field)) or c.quote in getattr(sub, c.field)
    assert judged >= 7


def test_a_tampered_or_stale_read_is_not_trusted(today):
    p = leads(today)["hackathon:portathon-2026/ku-exe"]
    good = public_reads.recorded()["reads"][p.id]
    forged = {
        **good,
        "data": {
            **good["data"],
            "fields": {**good["data"]["fields"], "who_pays": "The port pays EUR 2M a year."},
            "claims": [{"field": "who_pays", "signal": "payer", "quote": "The port pays"}],
        },
    }
    sub, claims, _, _ = public_reads.prepared(p, {"reads": {p.id: forged}})
    assert sub.who_pays == "" and all(c.field != "who_pays" for c in claims)  # not in the description: dropped
    stale = {**good, "text_sha": "000000000000"}
    assert public_reads.prepared(p, {"reads": {p.id: stale}})[3] == public_reads.CHANGED


def test_too_thin_keeps_not_judged_yet_and_research_titles_are_never_read(today):
    thin = {"text_sha": None, "data": {"too_thin": True, "why_thin": "It only names the challenge."}}
    p = leads(today)["hackathon:portathon-2026/ku-exe"]
    thin["text_sha"] = public_reads.text_sha(p.description)
    sub, _, reader, note = public_reads.prepared(p, {"reads": {p.id: thin}})
    assert (reader, note) == ("rules", "Not judged yet: it only names the challenge.") and sub.solution == ""
    research = next(r for r in leads(today).values() if r.title_only)
    assert public_reads.prepared(research)[3] == public_reads.TITLE_ONLY


def test_the_queue_ranks_on_the_reads_without_calling_a_model(today):
    queue = build_queue("apelago", "blue", [], today=today)  # the test guard blocks the network
    read = [i for i in queue.items if i.assessment.reader == "rules_and_model"]
    assert len(read) >= 7 and all(i.assessment.reader_note == public_reads.READ_LABEL for i in read)
    top = [i for i in queue.items if i.in_top]
    judged = [i.assessment.potential in ("high", "medium") for i in top]
    assert top and judged[0] and judged == sorted(judged, reverse=True)  # read leads first, unread after
    assert {i.assessment.potential for i in queue.items} >= {"high", "unknown"}
