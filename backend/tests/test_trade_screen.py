"""Haiku 5.5 registry/pricing wiring + the entry-scan screen's fail-open guarantee.

The screen may only ever *skip* a session; if anything about it is off (no key,
disabled, network/parse error) it must return run=True so trading never stalls on
the screen's own failure.
"""
import pytest

from core.model_registry import resolve, is_selectable
from services.credits import _get_model_pricing
from services import trade_screen
from services.trade_screen import should_run_entry_scan, ScreenResult


# ── model registry / pricing ─────────────────────────────────────────────────

def test_haiku_5_5_resolves_to_its_own_spec_not_the_haiku_4_5_one():
    spec = resolve("anthropic/claude-haiku-5-5")
    assert spec.reasoning_style == "anthropic_adaptive"  # not the 4.5 budget style
    assert spec.default_effort == "high"
    assert spec.pricing["input"] == 0.10
    assert spec.pricing["output"] == 0.50


def test_haiku_4_5_still_resolves_to_the_budget_spec():
    spec = resolve("anthropic/claude-haiku-4-5")
    assert spec.reasoning_style == "anthropic_budget"
    assert spec.pricing["input"] == 1.0


def test_haiku_5_5_is_selectable():
    assert is_selectable("anthropic/claude-haiku-5-5")


def test_haiku_5_5_credits_pricing():
    p = _get_model_pricing("anthropic/claude-haiku-5-5")
    assert p["input"] == 0.10 and p["output"] == 0.50


def test_gpt_6_luna_credits_pricing_no_output_charge():
    p = _get_model_pricing("gpt-6-luna")
    assert p["input"] == 0.10 and p["output"] == 0.0


# ── screen fail-open ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_screen_fails_open_when_disabled(monkeypatch):
    monkeypatch.setattr(trade_screen.Config, "TRADE_SCREEN_ENABLED", False)
    res = await should_run_entry_scan()
    assert isinstance(res, ScreenResult) and res.run is True


@pytest.mark.asyncio
async def test_screen_fails_open_without_api_key(monkeypatch):
    monkeypatch.setattr(trade_screen.Config, "TRADE_SCREEN_ENABLED", True)
    monkeypatch.setattr(trade_screen.Config, "OPENAI_API_KEY", None)
    res = await should_run_entry_scan()
    assert res.run is True


@pytest.mark.asyncio
async def test_screen_fails_open_on_snapshot_error(monkeypatch):
    monkeypatch.setattr(trade_screen.Config, "TRADE_SCREEN_ENABLED", True)
    monkeypatch.setattr(trade_screen.Config, "OPENAI_API_KEY", "sk-test")

    async def _boom(symbols, chunk_size=50):
        raise RuntimeError("fmp down")

    import services.monitoring.inputs as inputs
    monkeypatch.setattr(inputs, "batch_quotes", _boom)
    res = await should_run_entry_scan()
    assert res.run is True  # never skip on our own failure


@pytest.mark.asyncio
async def test_screen_skips_on_low_probability(monkeypatch):
    monkeypatch.setattr(trade_screen.Config, "TRADE_SCREEN_ENABLED", True)
    monkeypatch.setattr(trade_screen.Config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(trade_screen.Config, "TRADE_SCREEN_MIN_PROBABILITY", 0.35)

    async def _quotes(symbols, chunk_size=50):
        return {"SPY": {"price": 500.0, "changesPercentage": 0.02}}

    import services.monitoring.inputs as inputs
    monkeypatch.setattr(inputs, "batch_quotes", _quotes)

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"answers": [{"name": "warrants_session", "probability": 0.1}]}

    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return _Resp()

    monkeypatch.setattr(trade_screen.httpx, "AsyncClient", _Client)
    res = await should_run_entry_scan()
    assert res.run is False and res.probability == 0.1


@pytest.mark.asyncio
async def test_screen_runs_on_high_probability(monkeypatch):
    monkeypatch.setattr(trade_screen.Config, "TRADE_SCREEN_ENABLED", True)
    monkeypatch.setattr(trade_screen.Config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(trade_screen.Config, "TRADE_SCREEN_MIN_PROBABILITY", 0.35)

    async def _quotes(symbols, chunk_size=50):
        return {"SPY": {"price": 500.0, "changesPercentage": -1.4},
                "VIXY": {"price": 20.0, "changesPercentage": 8.0}}

    import services.monitoring.inputs as inputs
    monkeypatch.setattr(inputs, "batch_quotes", _quotes)

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"answers": [{"name": "warrants_session", "probability": 0.82}]}

    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return _Resp()

    monkeypatch.setattr(trade_screen.httpx, "AsyncClient", _Client)
    res = await should_run_entry_scan()
    assert res.run is True and res.probability == 0.82
