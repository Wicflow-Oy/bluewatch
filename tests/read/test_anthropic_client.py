"""AnthropicModelClient against a stubbed SDK client: no network, no key, no paid calls."""

from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from bluewatch.llm import ModelRequest
from bluewatch.read.anthropic_client import AnthropicModelClient, MissingKeyError

REQUEST = ModelRequest(
    task="classify_blue",
    system="fixed system",
    prompt="<page>x</page>",
    model="claude-haiku-5-5",
    max_tokens=2048,
    json_schema={"type": "object", "properties": {}, "additionalProperties": False},
)


def message(text="", stop="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop,
        model="claude-haiku-5-5",
        usage=SimpleNamespace(input_tokens=120, output_tokens=30),
    )


class StubSDK:
    def __init__(self, result):
        self.result = result
        self.kwargs = None
        self.messages = self

    def create(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_json_answers_use_structured_outputs_and_keep_the_page_in_the_user_turn():
    sdk = StubSDK(message('{"blue": true}'))
    response = AnthropicModelClient(client=sdk).complete(REQUEST)
    assert response.data == {"blue": True} and not response.refused
    assert (response.input_tokens, response.output_tokens) == (120, 30)
    assert sdk.kwargs["system"] == "fixed system"
    assert sdk.kwargs["messages"] == [{"role": "user", "content": "<page>x</page>"}]
    assert sdk.kwargs["output_config"] == {
        "format": {"type": "json_schema", "schema": REQUEST.json_schema},
        "effort": "low",
    }
    assert "tools" not in sdk.kwargs


def test_refusals_are_refused_responses():
    response = AnthropicModelClient(client=StubSDK(message("", stop="refusal"))).complete(REQUEST)
    assert response.refused and response.stop_reason == "refusal" and response.data is None


def test_a_max_tokens_stop_yields_no_data():
    response = AnthropicModelClient(client=StubSDK(message('{"blue": tr', stop="max_tokens"))).complete(REQUEST)
    assert response.stop_reason == "max_tokens" and response.data is None


def test_api_and_connection_errors_become_refused_responses():
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    limited = anthropic.RateLimitError("rate limited", response=httpx2.Response(429, request=request), body=None)
    response = AnthropicModelClient(client=StubSDK(limited)).complete(REQUEST)
    assert response.refused and response.stop_reason == "api_error_429"
    offline = AnthropicModelClient(client=StubSDK(anthropic.APIConnectionError(request=request))).complete(REQUEST)
    assert offline.refused and offline.stop_reason == "connection_error"


def test_the_key_comes_from_anthropic_api_key_only(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "not-a-key")
    with pytest.raises(MissingKeyError):
        AnthropicModelClient()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    assert AnthropicModelClient()._client.api_key == "test-key-not-real"
