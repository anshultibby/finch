"""
Regression test for the delegate-tool timeout bug.

`delegate` runs a full sub-agent loop that can stay quiet (no tool events) for
longer than the executor's heartbeat window during a single LLM generation. The
old code killed any tool that didn't emit an event within QUEUE_HEARTBEAT_TIMEOUT,
which is why delegation was disabled ("timeout issues"). The executor must now keep
waiting as long as the underlying task is still running, and only force-fail when a
tool is truly stuck (nothing running) or the overall batch ceiling is exceeded.
"""
import asyncio
import pytest

from core.config import Config
from modules.agent.context import AgentContext
from modules.tools.executor import ToolExecutor, ExecutionMode, ToolCallRequest
from schemas.sse import SSEEvent


@pytest.fixture(autouse=True)
def _no_real_alerts(monkeypatch):
    """These tests deliberately fail a tool, which trips the global tool-monitoring
    alert path. Keep it from sending a real email during the test run."""
    monkeypatch.setattr(Config, "TOOL_ALERTS_ENABLED", False, raising=False)


class FakeRunner:
    """Runner stub that emits one early event, goes quiet past the heartbeat
    window, then returns a final result — mimicking a long sub-agent generation."""

    def __init__(self, quiet_seconds: float, *, hang: bool = False):
        self.quiet_seconds = quiet_seconds
        self.hang = hang

    async def execute(self, tool_name, arguments, context):
        # One early event so the tool clearly started.
        yield SSEEvent(event="tool_status", data={"message": "sub-agent started"})
        # Quiet stretch longer than the heartbeat window (no events emitted).
        await asyncio.sleep(self.quiet_seconds)
        if self.hang:
            # Never returns a result within the test's patience — simulates a real hang.
            await asyncio.sleep(3600)
        yield {"success": True, "data": {"task_id": arguments.get("task_id", "t")},
               "message": "done"}


def _ctx():
    return AgentContext(agent_id="a", user_id="u", chat_id="c", data={})


async def _run(executor, n=1):
    calls = [
        ToolCallRequest(id=f"id{i}", name="delegate",
                        arguments={"task": "x", "task_id": f"t{i}"})
        for i in range(n)
    ]
    events = []
    async for ev in executor.execute_batch_streaming(calls, _ctx(), enable_tool_streaming=True):
        events.append(ev)
    return events


def _tools_end(events):
    return next(e for e in events if e.event == "tools_end")


@pytest.mark.asyncio
async def test_long_quiet_tool_is_not_killed():
    """A tool quiet past the heartbeat window but still running must complete, not time out."""
    executor = ToolExecutor(execution_mode=ExecutionMode.PARALLEL, runner=FakeRunner(quiet_seconds=0.3))
    executor.QUEUE_HEARTBEAT_TIMEOUT = 0.1   # heartbeat shorter than the quiet stretch
    executor.MAX_BATCH_WAIT = 30             # generous overall ceiling

    events = await _run(executor)
    results = _tools_end(events).data["execution_results"]

    assert len(results) == 1
    assert results[0]["status"] == "completed", results[0]
    assert "timed out" not in (results[0].get("error") or "")


@pytest.mark.asyncio
async def test_multiple_quiet_delegates_all_complete():
    """Several parallel sub-agents, all quiet past the window, should all succeed."""
    executor = ToolExecutor(execution_mode=ExecutionMode.PARALLEL, runner=FakeRunner(quiet_seconds=0.3))
    executor.QUEUE_HEARTBEAT_TIMEOUT = 0.1
    executor.MAX_BATCH_WAIT = 30

    results = _tools_end(await _run(executor, n=3)).data["execution_results"]
    assert len(results) == 3
    assert all(r["status"] == "completed" for r in results), results


@pytest.mark.asyncio
async def test_overall_ceiling_still_fails_a_true_hang():
    """A tool that never returns must still be failed once MAX_BATCH_WAIT is exceeded."""
    executor = ToolExecutor(execution_mode=ExecutionMode.PARALLEL,
                            runner=FakeRunner(quiet_seconds=0.1, hang=True))
    executor.QUEUE_HEARTBEAT_TIMEOUT = 0.1
    executor.MAX_BATCH_WAIT = 0.5            # low ceiling so the test is fast

    results = _tools_end(await _run(executor)).data["execution_results"]
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "timed out" in results[0]["error"]
