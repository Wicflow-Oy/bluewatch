"""The one model interface. Every module that needs a language model takes a ModelClient.

- FakeModelClient: scripted answers for tests.
- RecordedModelClient: replays answers recorded earlier (offline demo, eval runs in CI).
- The Anthropic client lives in bluewatch/read/anthropic_client.py and reads its key from the
  ANTHROPIC_API_KEY environment variable only.

Model swaps are gated by the reader eval (bluewatch/read/evals.py): a new model id is accepted only
if it meets the thresholds on the recorded eval set.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class ModelRequest:
    task: str  # "classify_blue", "extract_claims", "draft_outreach", ...
    system: str
    prompt: str
    model: str
    max_tokens: int = 1024
    json_schema: dict | None = None

    def key(self) -> str:
        raw = json.dumps([self.task, self.system, self.prompt, self.model], ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@dataclass
class ModelResponse:
    text: str
    data: dict | None = None  # parsed JSON when a schema was requested
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "end_turn"
    refused: bool = False


class ModelClient(Protocol):
    name: str

    def complete(self, request: ModelRequest) -> ModelResponse: ...


@dataclass
class FakeModelClient:
    """Answers by task name (or by request key) from a dict; records every request."""

    answers: dict[str, dict | str] = field(default_factory=dict)
    name: str = "fake"
    calls: list[ModelRequest] = field(default_factory=list)

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        answer = self.answers.get(request.key(), self.answers.get(request.task))
        if answer is None:
            return ModelResponse(text="", data=None, model=self.name, stop_reason="refusal", refused=True)
        if isinstance(answer, dict):
            return ModelResponse(text=json.dumps(answer, ensure_ascii=False), data=answer, model=self.name)
        return ModelResponse(text=answer, model=self.name)


@dataclass
class RecordedModelClient:
    """Replays responses saved as {request_key: {"text":..., "data":...}} in a JSON file."""

    path: Path
    name: str = "recorded"

    def __post_init__(self) -> None:
        self._store: dict = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def complete(self, request: ModelRequest) -> ModelResponse:
        hit = self._store.get(request.key())
        if hit is None:
            return ModelResponse(text="", model=self.name, stop_reason="not_recorded", refused=True)
        return ModelResponse(text=hit.get("text", ""), data=hit.get("data"), model=hit.get("model", self.name))
