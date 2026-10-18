import json
import re

from bluewatch.llm import ModelRequest, ModelResponse
from bluewatch.read import evals
from bluewatch.read.keywords import classify_keywords
from tests.read.fakes import BUDGET, ScriptedClient

CASES = {c["id"]: c for c in evals.load_cases()}


class Oracle:
    """Answers each eval case from its gold label, quoting the page (or always says blue)."""

    name = "oracle"

    def __init__(self, always_blue: bool = False):
        self.always_blue = always_blue

    def complete(self, request: ModelRequest) -> ModelResponse:
        case = CASES[re.search(r"URL: eval:(\S+)", request.prompt).group(1)]
        parts = [*case["meta"].values(), case["text"], case["title"]]
        quote = classify_keywords(parts).quote or next(" ".join(p.split()[:12]) for p in parts if len(p.split()) > 2)
        data = {
            "blue": self.always_blue or case["label"] == "yes",
            "vertical": "other",
            "quote": quote,
            "reason": "test",
        }
        return ModelResponse(text=json.dumps(data), data=data)


def test_the_shipped_eval_set_is_free_of_personal_data():
    built = json.loads(evals.PAGES.read_text(encoding="utf-8"))
    assert len(built["cases"]) == 43 and len(CASES) == len(evals.load_cases())  # ids are unique
    for case in built["cases"]:
        text = " ".join([case["name"], case["title"], case["text"], *case["meta"].values()])
        assert not evals._EMAIL.search(text) and not evals._PHONE.search(text)
        assert not any(evals._hash(w.casefold()) in evals._NAME_HASHES for w in re.findall(r"\w+", text))
        assert "url" not in case


def test_labels_match_the_review_file():
    labels = [c["label"] for c in json.loads(evals.PAGES.read_text(encoding="utf-8"))["cases"]]
    assert labels.count("yes") == 17 and labels.count("no") == 26


def test_keyword_baseline_has_no_false_positives():
    baseline = evals.run_keyword_baseline()
    assert baseline.precision == 1.0 and baseline.trap_false_positives == 0
    assert baseline.recall >= 0.85 and baseline.quote_verified_rate == 1.0


def test_a_model_that_matches_the_labels_passes_the_gate():
    result = evals.run_reader_eval(Oracle(), model_id="oracle")
    assert result.precision == 1.0 and result.recall == 1.0 and evals.gate(result)


def test_a_model_that_says_blue_for_everything_fails():
    result = evals.run_reader_eval(Oracle(always_blue=True), model_id="yes-man")
    assert result.trap_false_positives > 0 and not evals.gate(result)


def test_an_incomplete_run_never_passes():
    result = evals.run_reader_eval(ScriptedClient(BUDGET), model_id="spent")
    assert result.answered == 0 and result.fallbacks == {"model budget": result.n}
    assert not evals.gate(result)


def test_the_cli_says_it_did_not_run_without_a_key(capsys):
    assert evals.main(["--model", "claude-haiku-5-5"]) == 2
    out = capsys.readouterr().out
    assert "Baseline" in out and "ANTHROPIC_API_KEY is not set" in out
