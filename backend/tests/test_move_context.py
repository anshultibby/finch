"""Move classification plumbing: the measured prior and the model-output parser.

The LLM writes the words; these deterministic pieces decide what it's told and
what survives from its reply, so they're what the tests pin down.
"""
import asyncio
from datetime import date, timedelta

import pytest

from services import move_explainer
from services.monitoring import move_context as mc


def _run(coro):
    return asyncio.run(coro)


BACKDROP = {
    "tape": [{"symbol": "SPY", "label": "S&P 500", "change_pct": -1.0}],
    "sectors": [{"sector": "Technology", "etf": "XLK", "change_pct": -3.0}],
    "headlines": [],
}


@pytest.fixture
def stub_lookups(monkeypatch):
    def install(typical, sector="Technology"):
        async def _typical(symbol):
            return typical

        async def _sector(symbol):
            return sector

        monkeypatch.setattr(mc, "_typical_daily_move", _typical)
        monkeypatch.setattr(mc, "_sector", _sector)
    return install


def test_routine_when_move_is_within_typical_range(stub_lookups):
    stub_lookups(typical=2.0)
    ctx = _run(mc.move_context("NVDA", {"changesPercentage": -2.5}, BACKDROP))
    assert ctx["move_multiple"] == 1.2
    assert ctx["prior"] == "routine for this stock"


def test_sector_explains_a_big_move(stub_lookups):
    stub_lookups(typical=1.0)
    ctx = _run(mc.move_context("NVDA", {"changesPercentage": -3.4}, BACKDROP))
    assert ctx["idiosyncratic_pct"] == -0.4
    assert ctx["prior"] == "mostly explained by the market/sector"


def test_stock_specific_when_it_diverges_from_sector(stub_lookups):
    stub_lookups(typical=1.0)
    ctx = _run(mc.move_context("NVDA", {"changesPercentage": 6.0}, BACKDROP))
    assert ctx["idiosyncratic_pct"] == 9.0
    assert ctx["prior"] == "stock-specific"


def test_unknown_sector_falls_back_to_market(stub_lookups):
    stub_lookups(typical=1.0, sector=None)
    ctx = _run(mc.move_context("XYZ", {"changesPercentage": -1.5}, BACKDROP))
    assert ctx["sector_etf"] is None
    assert ctx["idiosyncratic_pct"] == -0.5


def test_earnings_note_window():
    today = date.today()
    assert mc._earnings_note({"earningsAnnouncement": today.isoformat()}).startswith("Earnings today")
    assert "2 days ago" in mc._earnings_note({"earningsAnnouncement": (today - timedelta(days=2)).isoformat()})
    assert "Earnings in 1 day " in mc._earnings_note({"earningsAnnouncement": (today + timedelta(days=1)).isoformat()})
    assert "Earnings in 5 days" in mc._earnings_note({"earningsAnnouncement": (today + timedelta(days=5)).isoformat()})
    assert mc._earnings_note({"earningsAnnouncement": (today + timedelta(days=30)).isoformat()}) is None
    assert mc._earnings_note({}) is None


def test_parse_extracts_json_from_chatter():
    text = 'Sure:\n{"verdict": "narrative_shift", "driver": "company", "headline": "Guidance cut", ' \
           '"explanation": "They reset growth.", "watch": "Next call"}\nHope that helps'
    read = move_explainer._parse(text)
    assert read["verdict"] == "narrative_shift"
    assert read["driver"] == "company"
    assert read["watch"] == "Next call"


def test_parse_coerces_unknown_labels_and_rejects_empty():
    read = move_explainer._parse('{"verdict": "huge", "driver": "vibes", "explanation": "x"}')
    assert read["verdict"] == "noise"
    assert read["driver"] == "company"
    assert move_explainer._parse('{"verdict": "news"}') is None
    assert move_explainer._parse("no json here") is None


def test_session_line_names_the_last_session():
    from datetime import datetime
    sunday = datetime(2026, 10, 18, 20, 0, tzinfo=mc.ET)
    assert "last session, Friday Oct 16" in mc.session_line(sunday)
    monday_pre = datetime(2026, 10, 19, 8, 0, tzinfo=mc.ET)
    assert "last session, Friday Oct 16" in mc.session_line(monday_pre)
    open_ = datetime(2026, 10, 19, 11, 0, tzinfo=mc.ET)
    assert "Markets are open" in mc.session_line(open_)
    close = datetime(2026, 10, 19, 17, 0, tzinfo=mc.ET)
    assert "Monday's" in mc.session_line(close)
