"""ModelClient over the official Anthropic SDK (anthropic 1.x, Messages API).

- The key comes from ANTHROPIC_API_KEY only. Passing it explicitly stops the SDK from falling back to
  other credential sources (auth tokens, CLI profiles).
- JSON answers use structured outputs (output_config.format); data is parsed only from a complete turn.
- A refusal, a max_tokens stop or an API error becomes ModelResponse(refused/stop_reason) instead of an
  exception, so callers can say why nothing was read. Raw error bodies are not kept.
- No server-side fallback model: the reader eval must score the model it names.
"""

from __future__ import annotations

import json

import anthropic

from bluewatch.config import settings
from bluewatch.llm import ModelRequest, ModelResponse


class MissingKeyError(RuntimeError):
    """ANTHROPIC_API_KEY is not set."""


class AnthropicModelClient:
    name = "anthropic"

    def __init__(self, *, effort: str | None = "low", timeout_s: float = 60.0, client=None) -> None:
        """effort: "low" suits classification and extraction; None omits it (older models reject it).
        client: an SDK client to use instead (tests pass a stub)."""
        if client is None:
            key = settings().anthropic_api_key
            if not key:
                raise MissingKeyError("ANTHROPIC_API_KEY is not set; the reader runs offline without it.")
            client = anthropic.Anthropic(api_key=key, timeout=timeout_s, max_retries=2)
        self._client = client
        self.effort = effort

    def complete(self, request: ModelRequest) -> ModelResponse:
        output_config: dict = {}
        if request.json_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": request.json_schema}
        if self.effort:
            output_config["effort"] = self.effort
        extra = {"output_config": output_config} if output_config else {}
        try:
            message = self._client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens,
                system=request.system,
                messages=[{"role": "user", "content": request.prompt}],
                **extra,
            )
        except anthropic.APIStatusError as error:
            return _failed(request, f"api_error_{error.status_code}")
        except anthropic.APIConnectionError:  # includes timeouts
            return _failed(request, "connection_error")

        usage = message.usage
        tokens = {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}
        stop = message.stop_reason or "end_turn"
        if stop == "refusal":
            return ModelResponse(text="", model=message.model, stop_reason="refusal", refused=True, **tokens)
        text = "".join(block.text for block in message.content if block.type == "text")
        data = None
        if request.json_schema is not None and stop == "end_turn":
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = None  # reported downstream as an invalid answer
            data = parsed if isinstance(parsed, dict) else None
        return ModelResponse(text=text, data=data, model=message.model, stop_reason=stop, **tokens)


def _failed(request: ModelRequest, reason: str) -> ModelResponse:
    return ModelResponse(text="", model=request.model, stop_reason=reason, refused=True)
