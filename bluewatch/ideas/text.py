"""Text helpers for Idea Harbour: clean what a visitor typed, cut it into quotable sentences, spot text
aimed at the reviewer, and compare two ideas. No model and no network.
"""

from __future__ import annotations

import re

from bluewatch.ideas.models import ClaimField, Flag, IdeaSubmission

TEXT_FIELDS: tuple[ClaimField, ...] = ("problem", "who_has_it", "solution", "who_pays", "exists_detail")

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\w)(?:\+|0)\d[\d\s()-]{6,}\d")
# Profile pages identify a person; Idea Harbour collects no personal data, so these links are dropped.
PERSONAL_LINK = re.compile(r"linkedin\.com/in/|facebook\.com/|instagram\.com/|(?:x|twitter)\.com/|mailto:", re.I)
# Instructions addressed to whoever (or whatever) reads the submission. The rules never follow text, so
# this is not a defence of the rules; it marks an attempt to game the review so a person looks first.
INSTRUCTIONS = re.compile(
    r"\b(?:ignore|disregard|forget) (?:all |any |the |your )?(?:previous |prior |above |earlier |system )?"
    r"(?:instructions|rules|prompts?|rubric|criteria)\b"
    r"|\byou are (?:now )?(?:an? |the )?(?:ai|assistant|model|language model|chatbot|reviewer|evaluator|grader)\b"
    r"|\b(?:system|developer) (?:prompt|message)\b"
    r"|\b(?:give|rate|score|rank|mark|classify|put) (?:this|us|our (?:idea|team|project)|it) (?:as |at |in )?"
    r"(?:the )?(?:highest|top|maximum|max|first|10/10|100|bring)"
    r"|</?\s*submission\s*>",
    re.I,
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")
_STOP = frozenset(
    """that this with from have will they their them there what when which while into onto about would could
    should also more most less than then such only very much many some each over under using used uses make
    makes made team idea ideas project projects solution problem system based help helps where your ours""".split()
)


def sanitise(sub: IdeaSubmission) -> tuple[IdeaSubmission, list[Flag]]:
    """The submission with contact details and personal profile links removed, plus a flag for each."""
    flags: list[Flag] = []
    cleaned: dict[str, str] = {}
    removed = False
    for field in TEXT_FIELDS:
        text = getattr(sub, field)
        new = PHONE.sub("[phone removed]", EMAIL.sub("[e-mail removed]", text))
        removed |= new != text
        cleaned[field] = new
    if removed:
        flags.append(
            Flag(
                kind="contact_details_removed",
                text="Contact details were removed: Idea Harbour collects no e-mail addresses or phone numbers.",
            )
        )
    links = [link for link in sub.links if not PERSONAL_LINK.search(link)]
    if len(links) < len(sub.links):
        flags.append(
            Flag(
                kind="personal_link_dropped",
                text="A personal profile link was dropped: add a project page, repository or video instead.",
            )
        )
    return sub.model_copy(update={**cleaned, "links": links}), flags


def sentences(text: str) -> list[str]:
    """Sentences as exact slices of the text, so any of them is a valid quote."""
    return [s.strip() for s in _SENTENCE_END.split(text or "") if s.strip()]


def word_list(text: str) -> list[str]:
    return re.findall(r"[^\W\d_][\w'-]*", text or "")


def instruction_sentences(sub: IdeaSubmission) -> list[str]:
    found = [s for field in TEXT_FIELDS for s in sentences(getattr(sub, field)) if INSTRUCTIONS.search(s)]
    if INSTRUCTIONS.search(sub.title):
        found.append(sub.title)
    return found


def content_words(text: str) -> frozenset[str]:
    return frozenset(w.lower() for w in word_list(text) if len(w) >= 4 and w.lower() not in _STOP)


def similarity(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard overlap of content words: 1.0 for the same words, 0.0 for none shared."""
    return len(a & b) / len(a | b) if a and b else 0.0
