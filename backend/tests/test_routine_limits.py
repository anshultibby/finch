"""Routine plan-gating helpers (see docs/routines/spec.md).

Pure, DB-free coverage of the interval parsing and per-plan caps that gate
user-created routines in services.job_scheduler.
"""
from services.job_scheduler import _interval_minutes, _routine_limits


def test_interval_minutes_named():
    assert _interval_minutes("hourly") == 60
    assert _interval_minutes("daily") == 1440
    assert _interval_minutes("weekdays") == 1440
    assert _interval_minutes("weekly") == 10080


def test_interval_minutes_every_n():
    assert _interval_minutes("every_5m") == 5
    assert _interval_minutes("every_15m") == 15
    assert _interval_minutes("every_90m") == 90


def test_interval_minutes_oneoff_and_unknown():
    # one-off (no recurrence) and unrecognized strings are ignored by the floor
    assert _interval_minutes(None) is None
    assert _interval_minutes("") is None
    assert _interval_minutes("every_5") is None      # missing the 'm'
    assert _interval_minutes("fortnightly") is None


def test_free_plan_caps():
    lim = _routine_limits("free")
    assert lim["max_active"] == 2
    assert lim["min_interval_min"] == 60
    assert lim["runs_per_day"] == 5


def test_paid_plans_are_generous():
    for plan in ("pro", "max", "admin"):
        lim = _routine_limits(plan)
        assert lim["max_active"] >= 50
        assert lim["min_interval_min"] == 5
        assert lim["runs_per_day"] is None, f"{plan} should have no daily run cap"


def test_unknown_or_missing_plan_defaults_to_free():
    # Safe direction: an unrecognized / missing plan gets the restricted caps,
    # never the generous ones.
    assert _routine_limits(None)["max_active"] == 2
    assert _routine_limits("")["max_active"] == 2


def test_free_interval_floor_blocks_subhourly():
    # The values the schedule() floor compares: sub-hourly recurrences are below
    # the free floor and must be rejected; hourly and up are allowed.
    floor = _routine_limits("free")["min_interval_min"]
    assert _interval_minutes("every_5m") < floor
    assert _interval_minutes("every_30m") < floor
    assert _interval_minutes("hourly") >= floor
    assert _interval_minutes("daily") >= floor


def test_pro_interval_floor_allows_5min():
    floor = _routine_limits("pro")["min_interval_min"]
    assert _interval_minutes("every_5m") >= floor
    assert _interval_minutes("every_1m") < floor
