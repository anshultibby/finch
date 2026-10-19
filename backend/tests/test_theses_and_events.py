"""Theses (memory-store files) and the corporate-events watch: the pure logic
that decides what's written, what's due, and what counts as a dividend change."""
from datetime import date

import pytest

from services import events_watch as ew
from services import theses


# ── thesis files ─────────────────────────────────────────────────────────────

def _thesis(**over):
    t = {
        "symbol": "NVDA", "stance": "own",
        "why": "Data-center AI spend keeps compounding.\nCUDA lock-in.",
        "breaks": "Hyperscalers cut capex two quarters running.",
        "written": "2026-10-01", "updated": "2026-10-18",
        "log": [{"date": "2026-10-18", "verdict": "noise", "status": "intact", "note": "Tech selloff, routine."}],
    }
    t.update(over)
    return t


def test_render_parse_round_trip():
    t = _thesis()
    back = theses.parse_md(theses.render_md(t))
    for k in ("symbol", "stance", "why", "breaks", "written", "updated"):
        assert back[k] == t[k]
    assert back["log"] == [{"date": "2026-10-18", "verdict": "noise", "status": "intact", "note": "Tech selloff, routine."}]


def test_parse_tolerates_hand_edits():
    text = "# my notes\n\n## Why I own it\nCheap and growing.\n\n## Story log\n- not a log line\n"
    t = theses.parse_md(text, "ko")
    assert t["symbol"] == "KO"
    assert t["stance"] == "own"
    assert t["why"] == "Cheap and growing."
    assert t["breaks"] == ""
    assert t["log"] == []


def test_placeholder_sections_parse_as_empty():
    t = theses.parse_md(theses.render_md(_thesis(breaks="")))
    assert t["breaks"] == ""


def test_log_is_capped():
    t = _thesis(log=[{"date": "2026-01-01", "verdict": "news", "note": f"n{i}"} for i in range(40)])
    back = theses.parse_md(theses.render_md(t))
    assert len(back["log"]) == theses.MAX_LOG
    assert back["log"][-1]["note"] == "n39"


def test_index_has_one_line_per_thesis():
    idx = theses.render_index([_thesis(), _thesis(symbol="KO", stance="watch", why="Dividend king")])
    lines = [l for l in idx.splitlines() if l.startswith("- [")]
    assert lines == [
        "- [KO](KO.md) — watch · Dividend king",
        "- [NVDA](NVDA.md) — own · Data-center AI spend keeps compounding.",
    ]


@pytest.mark.parametrize("bad", ["", "nvda; rm -rf /", "../etc", "A" * 20])
def test_symbol_validation(bad):
    with pytest.raises(ValueError):
        theses.path_for(bad)


def test_parse_check():
    assert theses._parse_check('{"status": "weakened", "reason": "Capex guide cut."}') == {
        "status": "weakened", "reason": "Capex guide cut."}
    assert theses._parse_check('{"status": "fine", "reason": "x"}') is None


# ── events watch ─────────────────────────────────────────────────────────────

FRI = date(2026, 10, 23)
MON = date(2026, 10, 26)


def test_heads_up_is_next_trading_day():
    assert ew.is_heads_up_due({"date": "2026-10-26"}, FRI)  # Fri → Mon
    assert not ew.is_heads_up_due({"date": "2026-10-24"}, FRI)


def test_recap_timing():
    # After-close report on Friday reacts Monday.
    assert ew.is_recap_due({"date": "2026-10-23", "time": "amc", "eps": 1.0}, MON)
    assert not ew.is_recap_due({"date": "2026-10-23", "time": "amc", "eps": 1.0}, FRI)
    # Before-open reports react the same day.
    assert ew.is_recap_due({"date": "2026-10-26", "time": "bmo", "eps": 1.0}, MON)
    # Not reported yet → never recap.
    assert not ew.is_recap_due({"date": "2026-10-26", "time": "bmo", "eps": None}, MON)


def _div(amount, declared, freq="Quarterly"):
    return {"adjDividend": amount, "dividend": amount, "declarationDate": declared, "frequency": freq}


def test_dividend_raise_and_cut():
    today = date(2026, 10, 16)
    raise_ = ew.classify_dividend([_div(0.56, "2026-10-15"), _div(0.53, "2026-07-15")], today)
    assert raise_["kind"] == "raise" and raise_["change_pct"] == 5.7
    cut = ew.classify_dividend([_div(0.25, "2026-10-14"), _div(0.50, "2026-07-14")], today)
    assert cut["kind"] == "cut" and cut["change_pct"] == -50.0


def test_dividend_ignores_flat_old_and_special():
    today = date(2026, 10, 16)
    assert ew.classify_dividend([_div(0.53, "2026-10-15"), _div(0.53, "2026-07-15")], today) is None
    assert ew.classify_dividend([_div(0.60, "2026-09-01"), _div(0.53, "2026-06-01")], today) is None
    # A special dividend isn't compared against the regular one.
    special = [_div(2.00, "2026-10-15", "Special"), _div(0.53, "2026-10-01"), _div(0.53, "2026-07-01")]
    assert ew.classify_dividend(special, today) is None
