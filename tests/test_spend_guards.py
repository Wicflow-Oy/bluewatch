import pytest

from bluewatch import spend
from bluewatch.api.guards import RateLimiter
from bluewatch.config import CACHE_DIR, settings
from bluewatch.llm import FakeModelClient, ModelRequest, ModelResponse
from bluewatch.spend import BudgetedModelClient, SpendLedger, cost_usd


def _req(max_tokens=500):
    return ModelRequest(
        task="classify_blue", system="s", prompt="p" * 3000, model="claude-haiku-5-5", max_tokens=max_tokens
    )


def test_budget_refuses_when_cap_reached():
    ledger = SpendLedger()
    client = BudgetedModelClient(
        FakeModelClient(answers={"classify_blue": {"blue": True}}), cap_usd=0.01, ledger=ledger
    )
    assert not client.complete(_req()).refused
    ledger.add(0.02)
    resp = client.complete(_req())
    assert resp.refused and resp.stop_reason == "budget"


def test_one_shared_ledger_in_the_cache_dir():
    assert spend.ledger() is spend.ledger()
    assert spend.ledger().path == CACHE_DIR / "spend.json"
    capped = spend.capped(FakeModelClient())
    assert capped.ledger is spend.ledger() and capped.cap_usd == settings().daily_spend_cap_usd


def test_unknown_model_charged_at_top_rate():
    assert cost_usd("some-new-model", 1_000_000, 0) == 4.0


def test_rate_limiter_per_ip_and_total():
    rl = RateLimiter(per_ip_per_hour=2, total_per_minute=3)
    assert rl.allow("a", now=0)[0] and rl.allow("a", now=1)[0]
    assert not rl.allow("a", now=2)[0]  # third from the same IP within the hour
    assert rl.allow("b", now=3)[0]
    assert not rl.allow("c", now=4)[0]  # fourth overall within the minute
    assert rl.allow("c", now=70)[0]  # the minute window has passed


def test_rate_limiter_forgets_idle_ips():
    rl = RateLimiter(per_ip_per_hour=5, total_per_minute=100_000)
    for i in range(20_000):
        assert rl.allow(f"10.0.{i // 256}.{i % 256}", now=i * 0.001)[0]
    assert len(rl._ip_hits) == 20_000
    assert rl.allow("192.0.2.1", now=3700)[0]  # over an hour later: the sweep drops every idle IP
    assert list(rl._ip_hits) == ["192.0.2.1"]


def test_a_refused_ip_is_not_kept():
    rl = RateLimiter(per_ip_per_hour=5, total_per_minute=1)
    assert rl.allow("a", now=0)[0]
    assert not rl.allow("b", now=1)[0]
    assert list(rl._ip_hits) == ["a"]


def test_a_call_in_flight_holds_its_worst_case():
    worst = cost_usd("claude-haiku-5-5", 1000, 500)  # _req(): 3001 characters is about 1000 tokens
    seen: list[ModelResponse] = []

    class Nested:
        name = "nested"

        def complete(self, request: ModelRequest) -> ModelResponse:
            seen.append(client.complete(request))  # a second call while the first is still running
            return ModelResponse(text="ok", input_tokens=1000, output_tokens=10)

    client = BudgetedModelClient(Nested(), cap_usd=worst * 1.5, ledger=SpendLedger())
    assert not client.complete(_req()).refused
    assert seen[0].refused and seen[0].stop_reason == "budget"
    assert client.ledger.spent_today() == pytest.approx(cost_usd("claude-haiku-5-5", 1000, 10))  # settled


def test_the_ledger_survives_a_restart(tmp_path):
    path = tmp_path / "state" / "spend.json"
    SpendLedger(path=path).add(1.25)
    assert SpendLedger(path=path).spent_today() == 1.25
    assert not list(path.parent.glob("*.tmp"))
