"""
Trade-idea scoring tests.

The scoring rules decide whether the bot's own scorecard is honest, so they get
the coverage: stop-before-target within a bar, horizon expiry, short direction,
and the level validation that stops nonsense ideas being recorded at all.
"""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from schemas.trade_ideas import IdeaCreate, IdeaDecision, Idea, IdeaScorecard
from services.trade_ideas import _classify, _returns, _scorecard


def _idea(direction="long", entry=100.0, stop=95.0, target=110.0, horizon=3):
    return SimpleNamespace(direction=direction, entry_ref=entry, stop=stop,
                           target=target, horizon_days=horizon)


def _bar(high, low, close=None):
    return {"date": "2026-08-07", "high": high, "low": low,
            "close": close if close is not None else (high + low) / 2}


FUTURE = datetime.now(timezone.utc) + timedelta(days=30)
PAST = datetime.now(timezone.utc) - timedelta(days=1)


# ── outcome classification ───────────────────────────────────────────────────

def test_target_hit():
    v = _classify(_idea(), [_bar(112, 99)], FUTURE)
    assert v == {"outcome": "target", "exit_price": 110.0}


def test_stop_hit():
    v = _classify(_idea(), [_bar(102, 94)], FUTURE)
    assert v == {"outcome": "stop", "exit_price": 95.0}


def test_stop_wins_when_one_bar_spans_both():
    """Daily bars can't order intraday touches — take the pessimistic read so the
    bot can't flatter its own hit rate."""
    v = _classify(_idea(), [_bar(115, 90)], FUTURE)
    assert v["outcome"] == "stop"


def test_still_open_inside_the_horizon():
    assert _classify(_idea(), [_bar(105, 98)], FUTURE) is None


def test_expires_at_the_last_close_once_the_horizon_passes():
    v = _classify(_idea(), [_bar(105, 98, close=103.0)], PAST)
    assert v == {"outcome": "expired", "exit_price": 103.0}


def test_expiry_with_no_bars_falls_back_to_entry():
    """A delisted/halted name shouldn't score as a win or a loss."""
    v = _classify(_idea(), [], PAST)
    assert v == {"outcome": "expired", "exit_price": 100.0}


def test_earlier_bar_decides():
    """Stop on day 1 then a rip to target on day 2 is still a loss."""
    v = _classify(_idea(), [_bar(101, 94), _bar(115, 100)], FUTURE)
    assert v["outcome"] == "stop"


def test_short_direction_inverts_the_levels():
    short = _idea(direction="short", entry=100.0, stop=105.0, target=90.0)
    assert _classify(short, [_bar(101, 89)], FUTURE)["outcome"] == "target"
    assert _classify(short, [_bar(106, 99)], FUTURE)["outcome"] == "stop"


# ── returns ──────────────────────────────────────────────────────────────────

def test_long_returns_and_r_multiple():
    r = _returns(_idea(), 110.0)
    assert r["return_pct"] == 10.0
    assert r["r_multiple"] == 2.0  # +10 gained on 5 risked


def test_long_loss_is_minus_one_r():
    assert _returns(_idea(), 95.0)["r_multiple"] == -1.0


def test_short_profit_is_positive():
    short = _idea(direction="short", entry=100.0, stop=105.0, target=90.0)
    r = _returns(short, 90.0)
    assert r["return_pct"] == 10.0
    assert r["r_multiple"] == 2.0


# ── validation ───────────────────────────────────────────────────────────────

def _valid(**kw):
    base = dict(symbol="NVDA", catalyst_type="earnings_beat",
                catalyst_summary="Q2 EPS $1.20 vs $0.98 est", thesis="drift",
                entry_ref=100.0, stop=95.0, target=110.0)
    base.update(kw)
    return IdeaCreate(**base)


def test_valid_idea_accepted():
    assert _valid().reward_risk == 2.0


def test_long_levels_must_be_ordered():
    with pytest.raises(ValidationError):
        _valid(stop=105.0)  # stop above entry


def test_unknown_catalyst_type_rejected():
    with pytest.raises(ValidationError):
        _valid(catalyst_type="vibes")


def test_high_conviction_requires_a_bear_case():
    """Where bad ideas hide: a confident call with no stated downside."""
    with pytest.raises(ValidationError):
        _valid(conviction=5)
    assert _valid(conviction=5, bear_case="Guidance was soft").conviction == 5


def test_approval_requires_an_execution_mode():
    with pytest.raises(ValidationError):
        IdeaDecision(approve=True)
    assert IdeaDecision(approve=True, execution_mode="auto").execution_mode == "auto"
    assert IdeaDecision(approve=False).execution_mode is None


# ── scorecard ────────────────────────────────────────────────────────────────

def _scored(outcome, ret, bench, r, status="proposed"):
    return Idea(
        id="i", user_id="u", created_at=datetime.now(timezone.utc), symbol="X",
        direction="long", catalyst_type="earnings_beat", catalyst_summary="c",
        thesis="t", entry_ref=100.0, stop=95.0, target=110.0, horizon_days=3,
        conviction=3, status=status, outcome=outcome, return_pct=ret,
        benchmark_return_pct=bench, r_multiple=r,
    )


def test_scorecard_counts_untraded_ideas():
    """The whole point: a rejected idea still scores against the hit rate."""
    ideas = [
        _scored("target", 10.0, 1.0, 2.0, status="approved"),
        _scored("stop", -5.0, 1.0, -1.0, status="rejected"),
        _scored("pending", None, None, None),
    ]
    s = _scorecard(ideas)
    assert (s.total, s.open, s.scored) == (3, 1, 2)
    assert (s.wins, s.losses) == (1, 1)
    assert s.hit_rate == 0.5
    assert s.avg_return_pct == 2.5
    assert s.avg_r_multiple == 0.5


def test_alpha_subtracts_the_benchmark():
    """+10% in a +9% market is a 1% pick, not a 10% one."""
    i = _scored("target", 10.0, 9.0, 2.0)
    assert i.alpha_pct == 1.0
    assert _scorecard([i]).avg_alpha_pct == 1.0


def test_empty_scorecard_is_none_not_zero():
    """Nothing scored yet must not read as a 0% hit rate."""
    s = _scorecard([_scored("pending", None, None, None)])
    assert s.scored == 0 and s.hit_rate is None and s.avg_alpha_pct is None
