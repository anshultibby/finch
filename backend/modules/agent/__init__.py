"""
AI Agent module for portfolio chatbot

Submodules are exposed lazily (PEP 562). Eagerly importing base_agent here made
every `import modules.agent.context` -- a dependency-free leaf that 14 modules
under modules.tools depend on -- drag in the entire agent package, which in turn
imports modules.tools. That cycle only resolved when the app happened to import
modules.agent before modules.tools; importing modules.tools first raised
ImportError. Keeping this module free of eager submodule imports breaks it.
"""
from typing import TYPE_CHECKING

_LAZY_ATTRS = {
    "BaseAgent": ".base_agent",
    "LLMConfig": ".llm_config",
    "LLMHandler": ".llm_handler",
    "AgentContext": ".context",
}

if TYPE_CHECKING:  # pragma: no cover - for type checkers and IDEs only
    from .base_agent import BaseAgent
    from .llm_config import LLMConfig
    from .llm_handler import LLMHandler
    from .context import AgentContext


def __getattr__(name: str):
    module_path = _LAZY_ATTRS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module
    return getattr(import_module(module_path, __name__), name)


def __dir__():
    return sorted(set(globals()) | set(_LAZY_ATTRS))


__all__ = ['BaseAgent', 'LLMConfig', 'LLMHandler', 'AgentContext']
