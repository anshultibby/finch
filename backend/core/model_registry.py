"""
Central registry of LLM models and their provider characteristics.

Single source of truth for everything that varies by model:
  - which LiteLLM provider it routes to
  - which API key (Settings field) it needs
  - how prompt caching works for it
  - default call parameters (max_tokens, reasoning_effort, seed, ...)
  - pricing (for cost/cache logging)

Adding a new model is a one-place change: append a `ModelSpec` to `MODEL_SPECS`
(and put its API key in `Settings` / `.env`). Nothing else in the LLM stack
needs to change — `llm_config`, `llm_stream`, and `llm_handler` all resolve
their behaviour through this module.

Caching styles
--------------
- "anthropic"  Needs an explicit cache_control breakpoint (LiteLLM places it
               automatically when we pass top-level `cache_control`). Usage is
               reported via `cache_read_input_tokens` / `cache_creation_input_tokens`.
- "automatic"  Provider caches the prompt prefix automatically (e.g. Z.ai/GLM).
               No cache_control needed. Cache hits are reported OpenAI-style via
               `usage.prompt_tokens_details.cached_tokens`.
- "none"       No prompt caching (or handled entirely provider-side, e.g. Gemini).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Default pricing used when a model has no explicit entry (per million tokens).
_DEFAULT_PRICING: Dict[str, float] = {
    "input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75
}

# Reasoning effort tiers → Claude extended-thinking budget (tokens).
# Scaled so each tier is a meaningful step up; budget_tokens MUST stay < max_tokens.
_THINKING_BUDGET: Dict[str, int] = {
    "low": 4_096,
    "medium": 10_000,
    "high": 24_000,
}

# Output headroom reserved on top of the thinking budget. With extended thinking,
# max_tokens caps thinking + visible output combined, so we scale max_tokens with
# the budget to keep a constant amount of room for the actual response (file writes
# need ~16k). max_tokens = budget + headroom.
_THINKING_OUTPUT_HEADROOM: int = 16_000


@dataclass(frozen=True)
class ModelSpec:
    """Provider characteristics for a family of models, matched by id prefix."""

    # Lowercase prefixes that map to this spec (e.g. "zai/", "anthropic/claude").
    prefixes: Tuple[str, ...]
    # LiteLLM provider name (informational; LiteLLM infers it from the model id).
    provider: str
    # Name of the `Settings` attribute holding this provider's API key.
    api_key_setting: Optional[str]
    # Prompt-caching style: "anthropic" | "automatic" | "none".
    caching: str = "none"
    # Request usage stats while streaming (include_usage in stream_options).
    stream_usage: bool = True
    # Extra default kwargs merged into LLMConfig for this family.
    defaults: Dict[str, Any] = field(default_factory=dict)
    # How this provider expresses reasoning/thinking, used by `reasoning_params`:
    #   "anthropic_budget"   -> {"thinking": {...budget_tokens...}, scaled "max_tokens"}
    #   "anthropic_adaptive" -> {"thinking": {"type":"adaptive"}, "output_config":{"effort":...}}
    #                           (Opus 4.7/4.8: manual budget_tokens is rejected)
    #   "openai_effort"      -> {"reasoning_effort": <effort>}
    #   "auto"               -> {} (provider reasons by default, e.g. GLM/Z.ai)
    #   None                 -> no reasoning support
    reasoning_style: Optional[str] = None
    # Default effort tier ("low"|"medium"|"high") when a caller doesn't specify one.
    # None means thinking is off by default for this family.
    default_effort: Optional[str] = None
    # Pricing per million tokens.
    pricing: Dict[str, float] = field(default_factory=lambda: dict(_DEFAULT_PRICING))


# Ordered most-specific → least-specific. `resolve()` returns the first match.
MODEL_SPECS: List[ModelSpec] = [
    # ----------------------------------------------------- Anthropic Claude Opus
    # More specific than the general Claude spec below (different pricing), so it
    # must come first. Opus 4.5+ is priced at the lower $5/$25 tier.
    # Opus 4.7/4.8 reject manual extended thinking (`thinking.type:"enabled"` +
    # budget_tokens) — they use adaptive thinking with `output_config.effort`.
    ModelSpec(
        prefixes=("anthropic/claude-opus", "claude-opus"),
        provider="anthropic",
        api_key_setting="ANTHROPIC_API_KEY",
        caching="anthropic",
        stream_usage=True,
        defaults={"caching": True, "max_tokens": 32000},
        reasoning_style="anthropic_adaptive",
        default_effort="medium",
        pricing={"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write": 6.25},
    ),
    # ---------------------------------------------------------------- Anthropic
    ModelSpec(
        prefixes=("anthropic/", "claude"),
        provider="anthropic",
        api_key_setting="ANTHROPIC_API_KEY",
        caching="anthropic",
        stream_usage=True,
        # Claude's default max_tokens is only 4096 — too small for file writes.
        # When thinking is enabled, max_tokens is recomputed as budget + headroom
        # (see reasoning_params), so this base value applies only when thinking is off.
        defaults={"caching": True, "max_tokens": 16000},
        reasoning_style="anthropic_budget",
        default_effort="medium",
        pricing={"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    ),
    # ----------------------------------------------------------- Z.ai / Zhipu GLM
    # GLM caches the prompt prefix automatically; cache hits come back as
    # usage.prompt_tokens_details.cached_tokens. No cache_control breakpoint needed.
    ModelSpec(
        prefixes=("zai/", "glm-", "glm/"),
        provider="zai",
        api_key_setting="ZAI_API_KEY",
        caching="automatic",
        stream_usage=True,
        defaults={"caching": True, "max_tokens": 16000},
        # GLM-5.1 is a reasoning model; Z.ai enables thinking server-side by default,
        # so we send no explicit param ("auto"). It streams reasoning_content natively.
        reasoning_style="auto",
        default_effort="medium",
        # Z.ai pricing (per Mtok); cached input is ~5x cheaper. Estimated — used
        # only for cost logging, not billing.
        pricing={"input": 0.60, "output": 2.20, "cache_read": 0.11, "cache_write": 0.0},
    ),
    # ------------------------------------------------------------------- Gemini
    ModelSpec(
        prefixes=("gemini",),
        provider="gemini",
        api_key_setting="GEMINI_API_KEY",
        caching="none",  # Gemini handles caching provider-side.
        stream_usage=False,
        defaults={"caching": False},
        pricing={"input": 1.25, "output": 10.0, "cache_read": 0.31, "cache_write": 1.625},
    ),
    # --------------------------------------------------- OpenAI reasoning models
    ModelSpec(
        prefixes=("gpt-5", "o1", "o3"),
        provider="openai",
        api_key_setting="OPENAI_API_KEY",
        caching="automatic",
        stream_usage=True,
        defaults={"caching": True, "seed": 42},
        reasoning_style="openai_effort",
        default_effort="medium",
        pricing={"input": 15.0, "output": 60.0, "cache_read": 7.50, "cache_write": 15.0},
    ),
    # -------------------------------------------------------------- OpenAI GPT-4
    ModelSpec(
        prefixes=("gpt-4o-mini",),
        provider="openai",
        api_key_setting="OPENAI_API_KEY",
        caching="automatic",
        stream_usage=True,
        defaults={"caching": True, "seed": 42},
        pricing={"input": 0.15, "output": 0.60, "cache_read": 0.075, "cache_write": 0.15},
    ),
    ModelSpec(
        prefixes=("gpt-4o", "gpt-4"),
        provider="openai",
        api_key_setting="OPENAI_API_KEY",
        caching="automatic",
        stream_usage=True,
        defaults={"caching": True, "seed": 42},
        pricing={"input": 2.50, "output": 10.0, "cache_read": 1.25, "cache_write": 2.50},
    ),
]

# Fallback when nothing matches — assume an OpenAI-compatible provider.
_FALLBACK_SPEC = ModelSpec(
    prefixes=(),
    provider="openai",
    api_key_setting="OPENAI_API_KEY",
    caching="automatic",
    stream_usage=True,
    defaults={"caching": True, "seed": 42},
    pricing=dict(_DEFAULT_PRICING),
)


# Models the user may pick from in the chat UI (the per-chat model picker).
# Each entry is verified to work with the configured provider keys. `id` is the
# LiteLLM model string stored on the chat row; `label` is shown in the picker.
SELECTABLE_MODELS: List[Dict[str, str]] = [
    {"id": "anthropic/claude-opus-4-8", "label": "Claude Opus 4.8", "provider": "Anthropic"},
    {"id": "anthropic/claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "provider": "Anthropic"},
    {"id": "zai/glm-5.1", "label": "GLM-5.1", "provider": "Z.ai"},
    {"id": "gemini/gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro", "provider": "Google"},
]

_SELECTABLE_IDS = {m["id"] for m in SELECTABLE_MODELS}


def selectable_models() -> List[Dict[str, str]]:
    """Return the list of user-selectable models for the chat picker."""
    return [dict(m) for m in SELECTABLE_MODELS]


def is_selectable(model: Optional[str]) -> bool:
    """Whether `model` is on the user-selectable allowlist."""
    return bool(model) and model in _SELECTABLE_IDS


def resolve(model: str) -> ModelSpec:
    """Return the ModelSpec whose prefix matches `model` (case-insensitive)."""
    model_lower = (model or "").lower()
    for spec in MODEL_SPECS:
        if any(model_lower.startswith(p) for p in spec.prefixes):
            return spec
    return _FALLBACK_SPEC


def get_api_key(model: str) -> Optional[str]:
    """Return the configured API key for `model`'s provider, or None."""
    from core.config import Config

    spec = resolve(model)
    if not spec.api_key_setting:
        return None
    return getattr(Config, spec.api_key_setting, None)


def get_defaults(model: str) -> Dict[str, Any]:
    """Return a copy of the default call kwargs for `model`."""
    return dict(resolve(model).defaults)


def caching_style(model: str) -> str:
    """Return the caching style: 'anthropic' | 'automatic' | 'none'."""
    return resolve(model).caching


def wants_stream_usage(model: str) -> bool:
    """Whether to request usage stats while streaming for `model`."""
    return resolve(model).stream_usage


def get_pricing(model: str) -> Dict[str, float]:
    """Return pricing (per Mtok) for `model`."""
    return dict(resolve(model).pricing)


def reasoning_params(model: str, effort: Optional[str] = None) -> Dict[str, Any]:
    """
    Build the provider-specific reasoning/thinking kwargs for `model`.

    `effort` is "low" | "medium" | "high" (defaults to the model's `default_effort`).
    Returns a dict to merge into the LLM call kwargs:
      - Anthropic: {"thinking": {...}, "max_tokens": budget + headroom}
                   (max_tokens scales with the budget so output room stays constant)
      - OpenAI:    {"reasoning_effort": effort}
      - GLM/auto:  {} (provider reasons by default)
      - others:    {} (no reasoning)

    Returns {} when the family has no reasoning support or thinking is off.
    """
    spec = resolve(model)
    style = spec.reasoning_style
    if not style:
        return {}

    effort = effort or spec.default_effort
    if not effort:
        return {}
    if effort not in _THINKING_BUDGET:
        effort = "medium"

    if style == "openai_effort":
        return {"reasoning_effort": effort}

    if style == "anthropic_budget":
        budget = _THINKING_BUDGET[effort]
        return {
            "thinking": {"type": "enabled", "budget_tokens": budget},
            "max_tokens": budget + _THINKING_OUTPUT_HEADROOM,
        }

    if style == "anthropic_adaptive":
        # Opus 4.7/4.8: manual budget_tokens is rejected with a 400. Enable thinking
        # via adaptive mode and control depth with output_config.effort. LiteLLM
        # forwards both to Anthropic and validates effort ∈ {low, medium, high}.
        return {
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": effort},
        }

    # "auto" and anything else: provider handles reasoning itself.
    return {}


def extract_cache_tokens(usage_info: Any) -> Tuple[int, int]:
    """
    Normalize cache token accounting across providers.

    Returns (cache_read_tokens, cache_creation_tokens).

    Anthropic reports `cache_read_input_tokens` / `cache_creation_input_tokens`.
    OpenAI-compatible providers (GLM/Z.ai, OpenAI) report cache hits as
    `usage.prompt_tokens_details.cached_tokens` with no separate write count.
    """
    if usage_info is None:
        return 0, 0

    read = getattr(usage_info, "cache_read_input_tokens", 0) or 0
    creation = getattr(usage_info, "cache_creation_input_tokens", 0) or 0

    if read == 0:
        details = getattr(usage_info, "prompt_tokens_details", None)
        if details is not None:
            read = getattr(details, "cached_tokens", 0) or 0

    return read, creation
