"""
LLM Model constants.

Usage:
    from core.constants import Models

    model = Models.CLAUDE_SONNET_4_6
"""
from enum import StrEnum


class Models(StrEnum):
    # Claude
    CLAUDE_OPUS_4_8 = "anthropic/claude-opus-4-8"
    CLAUDE_SONNET_4_6 = "anthropic/claude-sonnet-4-6"
    CLAUDE_OPUS_4_6 = "anthropic/claude-opus-4-6"
    CLAUDE_SONNET_4_5 = "anthropic/claude-sonnet-4-5"
    CLAUDE_OPUS_4_5 = "anthropic/claude-opus-4-5-20251101"
    CLAUDE_HAIKU_4_5 = "anthropic/claude-haiku-4-5"
    # Haiku 5.5 (Oct 2026): $0.10/$0.50 per Mtok, 1M context, adaptive thinking +
    # effort. ~30x cheaper than Sonnet 4.6 — the day-trading coordinator model.
    CLAUDE_HAIKU_5_5 = "anthropic/claude-haiku-5-5"
    # OpenAI Decisions API model (POST /v1/decisions). $0.10/Mtok in, no output
    # charge. Used as a cheap pre-flight screen, never as a chat coordinator.
    GPT_6_LUNA = "gpt-6-luna"

    # Gemini (gemini-3-pro-preview was retired; 3.1 is the current pro preview)
    GEMINI_3_1_PRO = "gemini/gemini-3.1-pro-preview"
    # 3.6 — not 3.7 — is the insight-job workhorse: it's the newest Flash that
    # still accepts thinkingLevel MINIMAL. See `thinking_off_kwargs`.
    GEMINI_3_6_FLASH = "gemini/gemini-3.6-flash"
    GEMINI_3_FLASH = "gemini/gemini-3-flash-preview"
    GEMINI_2_5_PRO = "gemini/gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini/gemini-2.5-flash"
    GEMINI_2_FLASH = "gemini/gemini-2.0-flash"

    # Z.ai / Zhipu GLM (OpenAI-compatible via the `zai` provider)
    GLM_5_1 = "zai/glm-5.1"
    GLM_5 = "zai/glm-5"
    GLM_4_6 = "zai/glm-4.6"

    # OpenAI
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    O3 = "o3"
    O3_MINI = "o3-mini"
