"""The reader eval: the gate a classifier model must pass before it replaces the current one.

Eval set: 43 hand-labelled company pages (excerpts and labels only; e-mails, phone numbers and person
names redacted, URLs dropped) in data/eval/reader/pages.json, plus the trap pages in
data/eval/reader/traps.json. One labeller who knew each page's group made the labels, and the keyword
reader's vocabulary was tuned on the same pages, so the keyword baseline is optimistic.

    python -m bluewatch.read.evals --model claude-haiku-5-5            # live; needs ANTHROPIC_API_KEY
    python -m bluewatch.read.evals --model claude-haiku-5-5 --record   # live, and save the answers
    python -m bluewatch.read.evals --model claude-haiku-5-5 --replay   # offline, from saved answers
    python -m bluewatch.read.evals --build <raw review pages JSON>     # rebuild the eval set
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from bluewatch.config import DATA_DIR, settings
from bluewatch.llm import ModelClient, ModelRequest, ModelResponse, RecordedModelClient
from bluewatch.read.classify import Classification, classify_blue, classify_offline
from bluewatch.read.fetch import Page
from bluewatch.resolve.names import fold

EVAL_DIR = DATA_DIR / "eval" / "reader"
PAGES = EVAL_DIR / "pages.json"
TRAPS = EVAL_DIR / "traps.json"
RECORDED = EVAL_DIR / "recorded"

# Explicit thresholds: precision >= 0.9 with traps included, recall >= 0.8 and no trap false positives,
# because a wrong company in front of an investor costs more than a missed one. Quote validity is targeted
# at 100%; the gate allows 1 in 20 because an unverified quote can never become a claim, it only costs
# recall. Every case must get a model answer.
THRESHOLDS = {"precision": 0.90, "recall": 0.80, "quote_verified_rate": 0.95, "trap_false_positives": 0}

_GROUPS = {"A_cohort_snapshot": "snapshot", "B_cohort_current": "current", "C_control_current": "control"}
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"(?<!\w)(?:\+|0)\d[\d\s()-]{6,}\d")
# Person names that occur in the source pages, stored as hashes so this file does not repeat them.
_NAME_HASHES = {
    "b5679ea7383b47df",
    "17e8c8b0b3b3eb7b",
    "c9594fc759fab5ab",
    "94d2d2ad18fee656",
    "1383a433e765087e",
    "3275ebe6cdf102d4",
}


def redact(text: str) -> str:
    text = _PHONE.sub("[phone]", _EMAIL.sub("[email]", text or ""))
    return re.sub(r"\w+", lambda m: "[name]" if _hash(m.group(0).casefold()) in _NAME_HASHES else m.group(0), text)


def _hash(word: str) -> str:
    return hashlib.sha256(word.encode("utf-8")).hexdigest()[:16]


def build_eval_set(source: Path) -> dict:
    """Build the redacted eval set from the raw review pages (research data kept outside this repo)."""
    cases = []
    for row in json.loads(source.read_text(encoding="utf-8")):
        group = _GROUPS[row["group"]]
        name = redact(row["name"])
        slug = re.sub(r"[^a-z0-9]+", "-", fold(name)).strip("-")
        meta = {
            key: redact(row[src])
            for key, src in (("description", "meta"), ("og:description", "og"), ("jsonld:description", "jsonld"))
            if row.get(src)
        }
        cases.append(
            {
                "id": f"cl-{group}-{slug}",
                "group": group,
                "basis": "fetched",
                "label": "yes" if row["reader_label"].startswith("yes") else "no",
                "note": row["reader_label"],
                "name": name,
                "title": redact(row["title"]),
                "meta": meta,
                "text": redact(row["text"]),
            }
        )
    about = (
        "Built by bluewatch.read.evals.build_eval_set from the hand-labelled classifier review pages; "
        "excerpts and labels only, personal data redacted."
    )
    return {"about": about, "cases": cases}


def load_cases() -> list[dict]:
    return [
        *json.loads(PAGES.read_text(encoding="utf-8"))["cases"],
        *json.loads(TRAPS.read_text(encoding="utf-8"))["cases"],
    ]


def _page(case: dict) -> Page:
    url = f"eval:{case['id']}"
    return Page(
        url=url,
        final_url=url,
        status=200,
        title=case["title"],
        text=case["text"],
        meta=case["meta"],
        ids_found=[],
        fetched_at=None,
    )


@dataclass
class ReaderEvalResult:
    model_id: str
    n: int
    answered: int
    tp: int
    fp: int
    fn: int
    tn: int
    quoted: int
    quote_verified: int
    trap_false_positives: int
    fallbacks: dict[str, int] = field(default_factory=dict)
    wrong: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    @property
    def quote_verified_rate(self) -> float | None:
        """Of the quotes given, the share found word for word on the page."""
        return self.quote_verified / self.quoted if self.quoted else None

    def summary(self) -> str:
        def pct(x: float | None) -> str:
            return "n/a" if x is None else f"{x:.0%}"

        return (
            f"{self.model_id}: precision {pct(self.precision)} ({self.tp}/{self.tp + self.fp}), recall "
            f"{pct(self.recall)} ({self.tp}/{self.tp + self.fn}), quotes verified {pct(self.quote_verified_rate)}"
            f", trap false positives {self.trap_false_positives}, answered {self.answered}/{self.n}"
            + (f", fallbacks {self.fallbacks}" if self.fallbacks else "")
        )


def _score(model_id: str, cases: list[dict], results: list[Classification]) -> ReaderEvalResult:
    out = ReaderEvalResult(
        model_id, n=len(cases), answered=0, tp=0, fp=0, fn=0, tn=0, quoted=0, quote_verified=0, trap_false_positives=0
    )
    fallbacks: Counter[str] = Counter()
    for case, result in zip(cases, results, strict=True):
        if result.fallback:
            fallbacks[result.fallback] += 1
        else:
            out.answered += 1
            out.quoted += result.quote is not None
            out.quote_verified += result.verified_quote
        gold = case["label"] == "yes"
        if result.blue and gold:
            out.tp += 1
        elif result.blue:
            out.fp += 1
            out.trap_false_positives += case["group"] == "trap"
        elif gold:
            out.fn += 1
        else:
            out.tn += 1
        if result.blue != gold:
            out.wrong.append(case["id"])
    out.fallbacks = dict(fallbacks)
    return out


def run_reader_eval(model: ModelClient, *, model_id: str) -> ReaderEvalResult:
    cases = load_cases()
    results = [classify_blue(_page(c), model, model_id=model_id, company_names=[c["name"]]) for c in cases]
    return _score(model_id, cases, results)


def run_keyword_baseline() -> ReaderEvalResult:
    cases = load_cases()
    results = [classify_offline(_page(c), company_names=[c["name"]]) for c in cases]
    return _score("offline keyword reader", cases, results)


def gate(result: ReaderEvalResult) -> bool:
    """True only for a complete run (every case answered by the model) that meets every threshold."""
    if result.n == 0 or result.answered < result.n:
        return False
    return (
        (result.precision or 0.0) >= THRESHOLDS["precision"]
        and (result.recall or 0.0) >= THRESHOLDS["recall"]
        and (result.quote_verified_rate or 0.0) >= THRESHOLDS["quote_verified_rate"]
        and result.trap_false_positives <= THRESHOLDS["trap_false_positives"]
    )


@dataclass
class _Recorder:
    """Saves each answer in RecordedModelClient's format, so a live run can be replayed offline."""

    inner: ModelClient
    path: Path
    name: str = "recorder"
    store: dict = field(default_factory=dict)

    def complete(self, request: ModelRequest) -> ModelResponse:
        response = self.inner.complete(request)
        if not response.refused:
            self.store[request.key()] = {"text": response.text, "data": response.data, "model": response.model}
        return response

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.store, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=settings().classifier_model)
    parser.add_argument("--record", action="store_true", help="save the live answers for offline replay")
    parser.add_argument("--replay", action="store_true", help="run offline from saved answers")
    parser.add_argument("--build", type=Path, metavar="RAW_PAGES", help="rebuild pages.json from the raw review pages")
    args = parser.parse_args(argv)
    if args.build:
        PAGES.write_text(json.dumps(build_eval_set(args.build), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {PAGES}")
        return 0
    print("Baseline", run_keyword_baseline().summary())
    recording = RECORDED / f"{args.model}.json"
    if args.replay:
        if not recording.exists():
            print(f"No saved answers for {args.model} ({recording}); run once with --record.")
            return 2
        model: ModelClient = RecordedModelClient(recording)
    elif not settings().anthropic_api_key:
        print("ANTHROPIC_API_KEY is not set, so the live eval did not run (only the baseline above).")
        return 2
    else:
        from bluewatch.read.anthropic_client import AnthropicModelClient

        model = AnthropicModelClient()
        if args.record:
            model = _Recorder(model, recording)
    result = run_reader_eval(model, model_id=args.model)
    if isinstance(model, _Recorder):
        model.save()
    passed = gate(result)
    print("Model   ", result.summary())
    print("Wrong:", ", ".join(result.wrong) or "none")
    print(f"Gate {'PASSED' if passed else 'FAILED'} (thresholds {THRESHOLDS}, every case answered)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
