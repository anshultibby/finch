"""
Test Claude prompt caching implementation.

Verifies that cache_control breakpoints are placed correctly for multi-turn
conversations, ensuring prefix caching works across turns.

Run: .venv/bin/python -m pytest tests/test_prompt_caching.py -v
  or: .venv/bin/python tests/test_prompt_caching.py
"""
import sys
import os
import copy
import types
import importlib.util


def _load_llm_stream():
    """Load llm_stream module with stubbed heavy dependencies."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, backend_dir)

    for pkg in ["modules", "modules.agent"]:
        if pkg not in sys.modules:
            p = types.ModuleType(pkg)
            p.__path__ = [os.path.join(backend_dir, pkg.replace(".", "/"))]
            p.__package__ = pkg
            sys.modules[pkg] = p

    stub_names = [
        "modules.tools", "modules.tools.decorator", "modules.tools.executor",
        "modules.tools.registry", "schemas", "schemas.sse", "schemas.snaptrade",
        "utils.logger",
    ]
    stubs = {}
    for name in stub_names:
        if name not in sys.modules:
            stubs[name] = types.ModuleType(name)
            sys.modules[name] = stubs[name]

    sys.modules["utils.logger"].get_logger = lambda n: types.SimpleNamespace(
        debug=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None, error=lambda *a, **k: None,
    )
    sse = sys.modules["schemas.sse"]
    for cls in ["SSEEvent", "LLMStartEvent", "LLMEndEvent",
                "AssistantMessageDeltaEvent", "ToolCallStreamingEvent", "ToolCallDetectedEvent"]:
        if not hasattr(sse, cls):
            setattr(sse, cls, type(cls, (), {}))

    mp = types.ModuleType("modules.agent.message_processor")
    mp.validate_and_fix_tool_calls = lambda x: x
    mp.enforce_tool_call_sequence = lambda x: x
    sys.modules["modules.agent.message_processor"] = mp

    lh = types.ModuleType("modules.agent.llm_handler")
    lh.LLMHandler = type("LLMHandler", (), {})
    sys.modules["modules.agent.llm_handler"] = lh

    lc = types.ModuleType("modules.agent.llm_config")
    lc.LLMConfig = type("LLMConfig", (), {})
    sys.modules["modules.agent.llm_config"] = lc

    spec = importlib.util.spec_from_file_location(
        "modules.agent.llm_stream",
        os.path.join(backend_dir, "modules/agent/llm_stream.py"),
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "modules.agent"
    spec.loader.exec_module(mod)
    return mod


_mod = _load_llm_stream()
_add_cache_control_to_system = _mod._add_cache_control_to_system
_add_cache_control_to_tools = _mod._add_cache_control_to_tools
_add_cache_control_to_messages = _mod._add_cache_control_to_messages
_is_claude_model = _mod._is_claude_model

SAMPLE_TOOLS = [
    {"type": "function", "function": {"name": "search_web", "description": "Search the web",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "get_portfolio", "description": "Get portfolio",
     "parameters": {"type": "object", "properties": {}}}},
]


def _count_bp(obj) -> int:
    if isinstance(obj, dict):
        c = 1 if "cache_control" in obj else 0
        return c + sum(_count_bp(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_count_bp(i) for i in obj)
    return 0


def _strip_cc(msg):
    msg = copy.deepcopy(msg)
    content = msg.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                block.pop("cache_control", None)
        if len(content) == 1 and content[0].get("type") == "text":
            msg["content"] = content[0]["text"]
    return msg


# ── Model detection ──────────────────────────────────────────────────

def test_claude_model_detection():
    assert _is_claude_model("claude-sonnet-4-6")
    assert _is_claude_model("claude-opus-4-7")
    assert not _is_claude_model("gpt-4o")
    assert not _is_claude_model("gemini-2.5-pro")


# ── System prompt ────────────────────────────────────────────────────

def test_system_prompt_cache_control():
    result = _add_cache_control_to_system("You are a helpful assistant.")
    assert len(result) == 1
    assert result[0]["type"] == "text"
    assert result[0]["text"] == "You are a helpful assistant."
    assert result[0]["cache_control"] == {"type": "ephemeral"}
    assert _count_bp(result) == 1


# ── Tools ────────────────────────────────────────────────────────────

def test_tools_cache_on_last_only():
    result = _add_cache_control_to_tools(SAMPLE_TOOLS)
    assert "cache_control" not in result[0]
    assert result[-1]["cache_control"] == {"type": "ephemeral"}
    assert _count_bp(result) == 1


def test_tools_single():
    result = _add_cache_control_to_tools([SAMPLE_TOOLS[0]])
    assert result[0]["cache_control"] == {"type": "ephemeral"}
    assert _count_bp(result) == 1


def test_tools_empty():
    assert _add_cache_control_to_tools([]) == []


def test_tools_no_mutation():
    original = copy.deepcopy(SAMPLE_TOOLS)
    _add_cache_control_to_tools(SAMPLE_TOOLS)
    assert SAMPLE_TOOLS == original


# ── Messages ─────────────────────────────────────────────────────────

def test_messages_short_conversation():
    msgs = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
        {"role": "user", "content": "How are you?"},
    ]
    result = _add_cache_control_to_messages(msgs)
    assert _count_bp(result) == 1
    assert isinstance(result[-1]["content"], list)
    assert result[-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}


def test_messages_long_conversation():
    msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"M{i}"} for i in range(30)]
    result = _add_cache_control_to_messages(msgs)
    assert _count_bp(result) == 2


def test_messages_midpoint_placement():
    msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"M{i}"} for i in range(24)]
    result = _add_cache_control_to_messages(msgs)
    mid = 24 // 2
    assert isinstance(result[mid]["content"], list)
    assert result[mid]["content"][-1].get("cache_control") == {"type": "ephemeral"}


def test_messages_single():
    result = _add_cache_control_to_messages([{"role": "user", "content": "Hi"}])
    assert _count_bp(result) == 1


def test_messages_empty():
    assert _add_cache_control_to_messages([]) == []


def test_messages_no_mutation():
    msgs = [{"role": "user", "content": "Hello"}]
    original = copy.deepcopy(msgs)
    _add_cache_control_to_messages(msgs)
    assert msgs == original


def test_messages_multimodal():
    msgs = [{"role": "user", "content": [
        {"type": "text", "text": "Look"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
    ]}]
    result = _add_cache_control_to_messages(msgs)
    assert result[0]["content"][-1].get("cache_control") == {"type": "ephemeral"}
    assert "cache_control" not in result[0]["content"][0]


def test_messages_with_tool_results():
    msgs = [
        {"role": "user", "content": "Search for AAPL"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "search", "arguments": "{}"}}
        ]},
        {"role": "tool", "tool_call_id": "c1", "content": "Apple Inc stock info..."},
        {"role": "assistant", "content": "Here's what I found about AAPL."},
    ]
    result = _add_cache_control_to_messages(msgs)
    assert _count_bp(result) == 1
    assert isinstance(result[-1]["content"], list)


# ── Total breakpoint budget (max 4) ─────────────────────────────────

def test_budget_short_conversation():
    total = (
        _count_bp(_add_cache_control_to_system("SP"))
        + _count_bp(_add_cache_control_to_tools(SAMPLE_TOOLS))
        + _count_bp(_add_cache_control_to_messages([
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hey"},
        ]))
    )
    assert total == 3
    assert total <= 4


def test_budget_long_conversation():
    total = (
        _count_bp(_add_cache_control_to_system("SP"))
        + _count_bp(_add_cache_control_to_tools(SAMPLE_TOOLS))
        + _count_bp(_add_cache_control_to_messages(
            [{"role": "user" if i % 2 == 0 else "assistant", "content": f"M{i}"} for i in range(30)]
        ))
    )
    assert total == 4
    assert total <= 4


def test_budget_no_tools():
    total = (
        _count_bp(_add_cache_control_to_system("SP"))
        + _count_bp(_add_cache_control_to_tools([]))
        + _count_bp(_add_cache_control_to_messages([{"role": "user", "content": "Hi"}]))
    )
    assert total == 2
    assert total <= 4


# ── Multi-turn prefix stability ─────────────────────────────────────

def test_prefix_stable_across_turns():
    s1 = _add_cache_control_to_system("You are helpful.")
    s2 = _add_cache_control_to_system("You are helpful.")
    assert s1 == s2

    t1 = _add_cache_control_to_tools(SAMPLE_TOOLS)
    t2 = _add_cache_control_to_tools(SAMPLE_TOOLS)
    assert t1 == t2


def test_growing_conversation_preserves_prefix():
    base = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}]
    extended = base + [{"role": "user", "content": "How?"}]

    r_base = _add_cache_control_to_messages(base)
    r_ext = _add_cache_control_to_messages(extended)

    for i in range(len(base)):
        assert _strip_cc(r_ext[i]) == _strip_cc(r_base[i]), \
            f"Message {i} content changed when conversation grew"


# ── Run standalone ───────────────────────────────────────────────────

if __name__ == "__main__":
    test_funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in test_funcs:
        try:
            fn()
            print(f"  ✓ {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {fn.__name__}: {e}")
    print(f"\n{passed}/{len(test_funcs)} tests passed")
    sys.exit(0 if passed == len(test_funcs) else 1)
