"""
LLM Model constants.

Usage:
    from models.llm_models import Models
    
    model = Models.CLAUDE_SONNET_4_5
"""
from enum import StrEnum


class Models(StrEnum):
    # Claude
    CLAUDE_SONNET_4_5 = "anthropic/claude-sonnet-4-5"
    CLAUDE_OPUS_4_5 = "anthropic/claude-opus-4-5-20251101"
    
    # Gemini
    GEMINI_3_PRO = "gemini/gemini-3-pro-preview"
    GEMINI_3_FLASH = "gemini/gemini-3-flash-preview"
    GEMINI_2_5_PRO = "gemini/gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini/gemini-2.5-flash"
    GEMINI_2_FLASH = "gemini/gemini-2.0-flash"
    
    # OpenAI
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    O3 = "o3"
    O3_MINI = "o3-mini"
