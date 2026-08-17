"""
Guards on the things that made automated runs expensive.

A tool result isn't paid once — it stays in the message list and is re-sent on
every later LLM call of that run. So an unbounded read is charged dozens of
times. These pin the bounds that keep that from coming back:

  * read_chat_file caps a whole-file read
  * list_jobs summarises instead of dumping every instruction body

The filing system that replaced the day-trading notebook is covered in
tests/test_library.py.
"""
import pytest

from core.config import Config
# AgentContext must be imported before the tool implementations — importing
# modules.tools first trips a pre-existing circular import.
from modules.agent.context import AgentContext
from modules.tools.implementations import file_management as fm


def _ctx():
    return AgentContext(agent_id="main", user_id="u", chat_id="c", data={})


# ── read_chat_file: capped whole-file reads ──────────────────────────────────

@pytest.mark.asyncio
async def test_read_chat_file_caps_whole_file_read(monkeypatch):
    big = "".join(f"line {i}\n" for i in range(20_000))
    assert len(big) > Config.TOOL_READ_FILE_MAX_CHARS

    async def fake_read(user_id, filename, context):
        return big
    monkeypatch.setattr(fm, "_read_sandbox_text", fake_read)

    result = await fm.read_chat_file_impl(context=_ctx(), filename="big.md")

    assert result["success"] and result["truncated"] is True
    assert len(result["content"]) < Config.TOOL_READ_FILE_MAX_CHARS + 500
    assert "omitted" in result["content"]
    # head and tail both survive, so the agent can still orient
    assert "line 0" in result["content"]
    assert "line 19999" in result["content"]


@pytest.mark.asyncio
async def test_read_chat_file_leaves_small_files_alone(monkeypatch):
    async def fake_read(user_id, filename, context):
        return "short file\n"
    monkeypatch.setattr(fm, "_read_sandbox_text", fake_read)

    result = await fm.read_chat_file_impl(context=_ctx(), filename="small.md")
    assert result["content"] == "short file\n"
    assert "truncated" not in result


@pytest.mark.asyncio
async def test_explicit_line_range_bypasses_the_cap(monkeypatch):
    """Paging is the escape hatch, so it must not be capped."""
    big = "".join(f"line {i}\n" for i in range(20_000))

    async def fake_read(user_id, filename, context):
        return big
    monkeypatch.setattr(fm, "_read_sandbox_text", fake_read)

    result = await fm.read_chat_file_impl(
        context=_ctx(), filename="big.md", start_line=1, end_line=20_000
    )
    assert "truncated" not in result
    assert result["total_lines"] == 20_001


# ── list_jobs: summary, not instruction bodies ───────────────────────────────

def _fake_jobs():
    return {
        "jobs": [
            {"id": "a", "name": "Day trade — open", "message": "M" * 2000,
             "run_at": "2026-08-18T13:36:00Z", "recurrence": None,
             "status": "pending", "run_count": 0, "system_key": None},
            {"id": "b", "name": "Old close-out", "message": "M" * 2000,
             "run_at": "2026-08-14T19:45:00Z", "recurrence": None,
             "status": "done", "run_count": 1, "system_key": None},
            {"id": "c", "name": "Cancelled one", "message": "M" * 2000,
             "run_at": "2026-08-14T19:45:00Z", "recurrence": None,
             "status": "cancelled", "run_count": 0, "system_key": None},
        ],
        "recurring_count": 0, "recurring_limit": 5,
    }


@pytest.fixture
def client(monkeypatch):
    from skills.finch_api.scripts import client as C
    monkeypatch.setattr(C, "_request", lambda *a, **k: _fake_jobs())
    return C


def test_list_jobs_drops_instruction_bodies(client):
    jobs = client.list_jobs()["jobs"]
    assert all("message" not in j for j in jobs)


def test_list_jobs_drops_finished_rows(client):
    jobs = client.list_jobs()["jobs"]
    assert [j["id"] for j in jobs] == ["a"]
    assert len(client.list_jobs(active_only=False)["jobs"]) == 3


def test_list_jobs_truncates_when_messages_are_asked_for(client):
    jobs = client.list_jobs(include_message=True, message_chars=50)["jobs"]
    assert len(jobs[0]["message"]) == 51  # 50 + ellipsis


def test_list_jobs_keeps_the_scheduling_fields(client):
    job = client.list_jobs()["jobs"][0]
    for field in ("id", "name", "run_at", "recurrence", "status", "run_count"):
        assert field in job


def test_list_jobs_preserves_quota_envelope(client):
    assert client.list_jobs()["recurring_limit"] == 5


def test_get_job_returns_the_full_instruction(client):
    assert len(client.get_job("a")["message"]) == 2000
    assert client.get_job("nope") is None
