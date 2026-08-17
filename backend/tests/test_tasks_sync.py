"""
The tasks/{slug}.md -> agent_tasks mirror.

The file is the source of truth; these cover the parsing that turns it into a
row the app can list. The rule that matters most: a malformed task file must
still sync — losing the user's work to a bad date string is far worse than a
row with a null column.
"""
import pytest

from modules.agent.context import AgentContext
from modules.tools.implementations import file_management as fm


TASK = """---
status: open
opened: 2026-08-10
symbols: [NVDA, MU]
review: 2026-08-20
---
# Does the NVDA AI-capex thesis survive Q3?

## What's next
Check hyperscaler capex guides.
"""


# ── frontmatter parsing ──────────────────────────────────────────────────────

def test_parses_the_convention():
    meta = fm._parse_frontmatter(TASK)
    assert meta["status"] == "open"
    assert meta["symbols"] == ["NVDA", "MU"]
    assert meta["review"] == "2026-08-20"


def test_strips_inline_comments_and_quotes():
    meta = fm._parse_frontmatter(
        "---\nstatus: open  # open | done\ntitle: 'quoted'\n---\n# T\n"
    )
    assert meta["status"] == "open"
    assert meta["title"] == "quoted"


def test_no_frontmatter_is_empty_not_an_error():
    assert fm._parse_frontmatter("# Just a heading\n") == {}
    assert fm._parse_frontmatter("") == {}


def test_body_text_after_the_fence_is_not_parsed():
    meta = fm._parse_frontmatter(TASK)
    assert "What's next" not in meta


def test_dates_parse_and_bad_dates_are_dropped_not_raised():
    from datetime import date
    assert fm._as_date("2026-08-20") == date(2026, 8, 20)
    assert fm._as_date("next tuesday") is None
    assert fm._as_date("") is None
    assert fm._as_date(None) is None


# ── which paths are tasks ────────────────────────────────────────────────────

@pytest.mark.parametrize("path,slug", [
    ("tasks/nvda-q3.md", "nvda-q3"),
    ("tasks/NVDA-Q3.md", "nvda-q3"),          # slug normalises
])
def test_task_paths_match(path, slug):
    m = fm._TASK_MD_PATTERN.match(path)
    assert m and m.group(1).lower() == slug


@pytest.mark.parametrize("path", [
    "tasks/sub/nested.md",      # one level only
    "stocks/NVDA/thesis.md",    # that's the other mirror
    "tasks/notes.txt",
    "my-tasks/a.md",
])
def test_non_task_paths_do_not_match(path):
    assert fm._TASK_MD_PATTERN.match(path) is None


# ── the sync itself ──────────────────────────────────────────────────────────

def _ctx():
    return AgentContext(agent_id="main", user_id="u", chat_id="c", data={})


@pytest.mark.asyncio
async def test_sync_writes_the_parsed_row(monkeypatch):
    captured = {}

    class FakeDB:
        async def execute(self, stmt, params=None):
            captured.update(params or {})

    class FakeSession:
        async def __aenter__(self): return FakeDB()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr("core.database.get_db_session", lambda: FakeSession())
    await fm._maybe_sync_task("tasks/nvda-q3.md", TASK, _ctx())

    assert captured["slug"] == "nvda-q3"
    assert captured["status"] == "open"
    assert captured["title"] == "Does the NVDA AI-capex thesis survive Q3?"
    assert '"NVDA"' in captured["symbols"] and '"MU"' in captured["symbols"]
    assert str(captured["review_on"]) == "2026-08-20"
    assert captured["body"] == TASK          # full markdown is preserved


@pytest.mark.asyncio
async def test_unknown_status_falls_back_to_open(monkeypatch):
    captured = {}

    class FakeDB:
        async def execute(self, stmt, params=None):
            captured.update(params or {})

    class FakeSession:
        async def __aenter__(self): return FakeDB()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr("core.database.get_db_session", lambda: FakeSession())
    await fm._maybe_sync_task(
        "tasks/x.md", "---\nstatus: wip\nreview: whenever\n---\n# X\n", _ctx()
    )
    assert captured["status"] == "open"      # not dropped, not an error
    assert captured["review_on"] is None     # bad date doesn't lose the task


@pytest.mark.asyncio
async def test_non_task_paths_are_ignored(monkeypatch):
    called = False

    class FakeSession:
        async def __aenter__(self):
            nonlocal called
            called = True
            return None
        async def __aexit__(self, *a): return False

    monkeypatch.setattr("core.database.get_db_session", lambda: FakeSession())
    await fm._maybe_sync_task("stocks/NVDA/thesis.md", TASK, _ctx())
    assert called is False


# ── schema declarations must match the real database ─────────────────────────

def test_chat_id_is_a_varchar_fk_to_chats_chat_id():
    """This exact declaration failed a production migration: `chats` has no `id`
    column — its PK is `chat_id`, a varchar, because job runs use ids like
    "job-9447c340b486-r27". Copied from StockAnalysis, which had it wrong too."""
    from sqlalchemy import String
    from models.tasks import AgentTask

    col = AgentTask.__table__.c.chat_id
    assert isinstance(col.type, String)
    fk = list(col.foreign_keys)[0]
    assert fk.target_fullname == "chats.chat_id"


def test_stock_analysis_chat_id_matches_the_database_too():
    from sqlalchemy import String
    from models.brokerage import StockAnalysis

    col = StockAnalysis.__table__.c.chat_id
    assert isinstance(col.type, String)
    assert list(col.foreign_keys)[0].target_fullname == "chats.chat_id"


@pytest.mark.asyncio
async def test_a_db_failure_never_breaks_the_write(monkeypatch):
    """The agent asked to write a file. The mirror is a side effect."""
    class Boom:
        async def __aenter__(self): raise RuntimeError("db down")
        async def __aexit__(self, *a): return False

    monkeypatch.setattr("core.database.get_db_session", lambda: Boom())
    await fm._maybe_sync_task("tasks/x.md", TASK, _ctx())   # must not raise
