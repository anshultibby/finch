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

    # Gemini (gemini-3-pro-preview was retired; 3.1 is the current pro preview)
    GEMINI_3_1_PRO = "gemini/gemini-3.1-pro-preview"
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
