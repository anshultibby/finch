"""
Import-graph health guards.

modules.tools and modules.agent are mutually dependent at the package level:
modules.tools.decorator/registry/runner reference modules.agent.context, while
modules.agent.base_agent imports the tool registry. That is fine as long as
importing either package first works. It regressed once because
modules/agent/__init__.py eagerly imported base_agent, so pulling in the
dependency-free leaf modules.agent.context dragged the whole agent package in
and cycled. The app only survived because it happened to import modules.agent
first; `import modules.tools` in a fresh interpreter raised ImportError.

These tests import in a subprocess so each one gets a clean sys.modules.
"""
import subprocess
import sys

import pytest

# Each entry is imported first, in a fresh interpreter.
ENTRYPOINTS = [
    "modules.tools",
    "modules.agent",
    "modules.tools.clients",
    "modules.agent.context",
    "modules.tools.registry",
    "modules.tools.runner",
    "modules.tools.decorator",
    "schemas.sse",
    "schemas.chat_history",
]


def _import_in_subprocess(statement: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", statement],
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.mark.parametrize("module", ENTRYPOINTS)
def test_module_imports_standalone(module):
    """Importing any of these first must not raise (no import cycle)."""
    result = _import_in_subprocess(f"import {module}")
    assert result.returncode == 0, (
        f"`import {module}` failed in a fresh interpreter -- likely a circular "
        f"import.\n{result.stderr[-2000:]}"
    )


def test_tools_before_agent_and_reverse():
    """Both orderings of the mutually-dependent packages must work."""
    for statement in (
        "import modules.tools; import modules.agent",
        "import modules.agent; import modules.tools",
    ):
        result = _import_in_subprocess(statement)
        assert result.returncode == 0, (
            f"`{statement}` failed:\n{result.stderr[-2000:]}"
        )


def test_agent_package_does_not_eagerly_import_base_agent():
    """
    modules.agent must expose its attributes lazily. Eagerly importing
    base_agent here is what created the cycle, so guard the property directly.
    """
    result = _import_in_subprocess(
        "import sys, modules.agent; "
        "assert 'modules.agent.base_agent' not in sys.modules, "
        "'modules.agent eagerly imported base_agent'; "
        # the lazy attribute must still resolve
        "assert modules.agent.BaseAgent is not None"
    )
    assert result.returncode == 0, result.stderr[-2000:]
