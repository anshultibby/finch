"""
Guards the seam between automation-run chat ids and the sidebar that filters
on them.

These two drifted apart once. `_run_chat_id` moved from `job-{id}` to
`job-{id}-r{n}` and migration 091 dropped `scheduled_jobs.chat_id`, while
crud.chat_async still filtered on both — so every sidebar load raised
AttributeError, the route turned it into a 500, and users saw an empty chat
history for eleven days before anyone noticed.

Nothing here touches the database: the point is that the producer and the
consumer of the id format stay in agreement, which is checkable statically.
"""
import re

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from crud.chat_async import (
    job_chat_predicate, get_user_chats_with_preview, job_run_labels,
)
from models.chat_models import Chat
from models.jobs import JOB_CHAT_PREFIX
from services.job_scheduler import _run_chat_id


def _compile(stmt):
    sql = str(stmt.compile(dialect=postgresql.dialect(),
                           compile_kwargs={"literal_binds": True}))
    return sql.replace("%%", "%")   # paramstyle doubles the LIKE wildcard


# ── the id format the sidebar keys off ───────────────────────────────────────

def test_run_chat_id_carries_the_shared_prefix():
    """If _run_chat_id stops using JOB_CHAT_PREFIX, the sidebar stops splitting."""
    assert _run_chat_id("abc123", 0).startswith(JOB_CHAT_PREFIX)
    assert _run_chat_id("abc123", 7).startswith(JOB_CHAT_PREFIX)


def test_run_chat_id_is_unique_per_run():
    """Keyed by run_count so a retry resumes, but the next cycle gets a new chat."""
    assert _run_chat_id("j1", 0) != _run_chat_id("j1", 1)
    assert _run_chat_id("j1", 3) == _run_chat_id("j1", 3)


def test_run_chat_id_cannot_collide_with_a_user_chat():
    """User chats are uuid4; a uuid never starts with the job prefix."""
    assert not re.match(r"^[0-9a-f-]{36}$", _run_chat_id("j1", 0))


# ── the predicate that splits the sidebar ────────────────────────────────────

def test_predicate_matches_ids_run_chats_actually_get():
    """The LIKE pattern must cover what _run_chat_id emits, not a stale format."""
    pattern = job_chat_predicate().right.value          # e.g. "job-%"
    assert pattern.endswith("%")
    assert _run_chat_id("j1", 0).startswith(pattern[:-1])


def test_predicate_compiles_against_live_columns():
    """Referencing a dropped column (as `ScheduledJob.chat_id` was) raises here."""
    sql = _compile(select(Chat.chat_id).where(~job_chat_predicate()))
    assert "NOT" in sql and JOB_CHAT_PREFIX in sql


# ── labelling run chats for the sidebar section ──────────────────────────────

class _JobRow:
    def __init__(self, id, name, system_key=None):
        self.id, self.name, self.system_key = id, name, system_key


class _JobsDB:
    """Returns a fixed set of automations for any IN (...) lookup."""
    def __init__(self, rows): self._rows = rows

    async def execute(self, stmt):
        rows = self._rows

        class _R:
            def all(self): return rows
        return _R()


async def test_run_chats_are_labelled_with_their_automation():
    """Run chats have no title of their own — the job name stands in."""
    labels = await job_run_labels(
        _JobsDB([_JobRow("abc", "Catalyst ideas — daily scan", "catalyst_ideas")]),
        [_run_chat_id("abc", 3)],
    )
    label = labels[_run_chat_id("abc", 3)]
    assert label["job_name"] == "Catalyst ideas — daily scan"
    assert label["run_number"] == 3
    assert label["job_id"] == "abc"


async def test_user_chats_get_no_label():
    """A uuid4 chat id must not parse as a run, or it'd be mislabelled."""
    assert await job_run_labels(_JobsDB([]), ["8f45b8e3-8115-4424-ba32-dac079b6b177"]) == {}


async def test_run_of_a_deleted_automation_still_labels():
    """Deleting an automation leaves its transcripts; they must not go blank."""
    labels = await job_run_labels(_JobsDB([]), [_run_chat_id("gone", 0)])
    assert labels[_run_chat_id("gone", 0)]["job_name"] == "Deleted automation"


@pytest.mark.parametrize("source,expect_negated", [("user", True), ("automation", False)])
async def test_source_selects_the_right_half(source, expect_negated):
    """"user" excludes run chats, "automation" keeps only them."""
    captured = {}

    class _FakeResult:
        def scalars(self): return self
        def all(self): return []

    class _FakeDB:
        async def execute(self, stmt):
            captured.setdefault("sql", _compile(stmt))
            return _FakeResult()

    await get_user_chats_with_preview(_FakeDB(), "u1", source=source)

    sql = captured["sql"]
    assert f"LIKE '{JOB_CHAT_PREFIX}%'" in sql
    assert (f"NOT LIKE '{JOB_CHAT_PREFIX}%'" in sql) is expect_negated
