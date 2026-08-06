"""
Scheduled-job logic tests — the pure parts of services/job_scheduler.

An automation is a time + an instruction. These cover how the time advances
(recurrence, backlog collapsing) and which chat a run lands in, since those are
what the waker depends on.
"""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest

from services.job_scheduler import (
    next_occurrence, _advance_past_now, _run_chat_id, _to_dto,
)


def _dt(y, m, d, hh=0, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


# ── recurrence ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("recurrence,expected", [
    ("hourly", _dt(2026, 8, 6, 13, 0)),
    ("daily",  _dt(2026, 8, 7, 12, 0)),
    ("weekly", _dt(2026, 8, 13, 12, 0)),
])
def test_named_cadences(recurrence, expected):
    assert next_occurrence(_dt(2026, 8, 6, 12, 0), recurrence) == expected


def test_weekdays_skips_the_weekend():
    # 2026-08-07 is a Friday -> next weekday run is Monday the 10th.
    assert next_occurrence(_dt(2026, 8, 7, 22, 0), "weekdays") == _dt(2026, 8, 10, 22, 0)


def test_minute_interval():
    assert next_occurrence(_dt(2026, 8, 6, 12, 0), "every_30m") == _dt(2026, 8, 6, 12, 30)


def test_minute_interval_floors_at_five_minutes():
    """Guards the waker: a 1-minute job would re-fire every loop tick."""
    assert next_occurrence(_dt(2026, 8, 6, 12, 0), "every_1m") == _dt(2026, 8, 6, 12, 5)


def test_unknown_recurrence_falls_back_to_daily():
    assert next_occurrence(_dt(2026, 8, 6, 12, 0), "fortnightly") == _dt(2026, 8, 7, 12, 0)


def test_backlog_collapses_to_one_future_run():
    """A job that missed a week of runs schedules ONE next run, not a burst."""
    stale = datetime.now(timezone.utc) - timedelta(days=7)
    nxt = _advance_past_now(stale, "daily")
    assert nxt > datetime.now(timezone.utc)
    assert nxt <= datetime.now(timezone.utc) + timedelta(days=1)


# ── run chat ─────────────────────────────────────────────────────────────────

def test_each_run_gets_a_fresh_chat():
    assert _run_chat_id("abc", 0) != _run_chat_id("abc", 1)
    assert _run_chat_id("abc", 3) == "job-abc-r3"


def _row(**kw):
    base = dict(
        id="j1", user_id="u1", name="Nightly", message="do the thing",
        run_at=_dt(2026, 8, 7, 22, 0), recurrence="weekdays", status="pending",
        created_at=_dt(2026, 8, 1), last_run_at=None, run_count=0,
        last_error=None, last_run_credits=0, credits_spent=0,
        system_key=None, comped=False, activity_gated=False,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_no_run_chat_before_the_first_run():
    """The UI must not link to a chat that doesn't exist yet."""
    assert _to_dto(_row()).run_chat_id is None


def test_run_chat_points_at_the_last_successful_run():
    dto = _to_dto(_row(run_count=3, last_run_at=_dt(2026, 8, 6, 22, 0)))
    assert dto.run_chat_id == "job-j1-r2"


def test_run_chat_points_at_the_live_run_while_running():
    dto = _to_dto(_row(run_count=3, status="running"))
    assert dto.run_chat_id == "job-j1-r3"


def test_run_chat_points_at_the_failed_run():
    """A retry resumes the failed run's chat, so surface that one."""
    dto = _to_dto(_row(run_count=2, last_error="boom"))
    assert dto.run_chat_id == "job-j1-r2"


# ── behaviour flags are per-row, not global sets ─────────────────────────────

def test_flags_round_trip():
    dto = _to_dto(_row(system_key="heartbeat", activity_gated=True, comped=False))
    assert dto.is_system and dto.activity_gated and not dto.comped


def test_projected_weekly_credits():
    dto = _to_dto(_row(recurrence="weekdays", last_run_credits=10, run_count=1,
                       last_run_at=_dt(2026, 8, 6)))
    assert dto.projected_weekly_credits == 50


def test_one_off_projects_nothing():
    dto = _to_dto(_row(recurrence=None, last_run_credits=10, run_count=1,
                       last_run_at=_dt(2026, 8, 6)))
    assert dto.projected_weekly_credits == 0
