"""
Chat title and icon generation service using LLM
"""
import json
import re
from typing import Tuple
from litellm import acompletion
from core.constants import Models
from utils.logger import get_logger

logger = get_logger(__name__)


class TitleGenerationError(Exception):
    """Raised when a title/icon could not be generated — callers should fall
    back to a locally-derived title rather than persisting a sentinel."""


def _parse_title_response(content: str) -> Tuple[str, str]:
    """Pull the title/icon JSON object out of the model's reply, tolerating fences/prose."""
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in title response: {content!r}")
    data = json.loads(text[start:end + 1])

    title = (data.get("title") or "").strip()[:50]
    if not title:
        raise ValueError(f"Title response had no usable title: {content!r}")
    icon = data.get("icon") or "💬"
    if not icon or len(icon) > 4:
        icon = "💬"
    return title, icon


# System prompt for title generation
TITLE_GENERATION_PROMPT = """You generate short, descriptive titles and icons for chat conversations about investing and finance.

Given the first message of a conversation, respond with a JSON object containing:
- "title": A concise title (3-6 words max) that captures the topic
- "icon": A single emoji that represents the topic

Guidelines:
- Titles should be specific but brief (e.g., "Portfolio Review", "Tesla Stock Analysis", "Dividend Strategy")
- Choose icons that match the financial/investing context when possible
- Use varied icons - don't always use the same ones

Example icons by category:
- Portfolio/holdings: 📊 💼 📈 🏦
- Specific stocks: 🎯 📌 🔍
- Market analysis: 📉 📈 🌡️ 📋
- Dividends/income: 💰 💵 🤑
- Strategy/planning: 🎯 🗺️ 📝 💡
- Research: 🔬 🧪 📚 🔎
- Trading: ⚡ 🎲 🎢
- Crypto: 🪙 ₿ 
- Real estate: 🏠 🏢
- Retirement: 🏖️ 🌴 👴
- Risk: ⚠️ 🛡️
- Growth: 🌱 🚀 📈
- Value: 💎 🏷️
- News/events: 📰 🗞️ 📢

Respond with ONLY the raw JSON object on a single line — no markdown code fences (no ```), no preamble, no explanation."""


async def generate_chat_title(first_message: str) -> Tuple[str, str]:
    """
    Generate a title and icon for a chat based on the first message.

    Args:
        first_message: The first user message in the chat

    Returns:
        Tuple of (title, icon)

    Raises:
        TitleGenerationError: if the LLM call fails or its response can't be
            parsed. Callers should NOT persist a "New Chat" sentinel on
            failure — that makes a failed generation indistinguishable from a
            real title and prevents any future retry.
    """
    try:
        response = await acompletion(
            model=Models.CLAUDE_HAIKU_4_5,
            max_tokens=100,
            messages=[
                {
                    "role": "system",
                    "content": TITLE_GENERATION_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Generate a title and icon for a chat that starts with this message:\n\n\"{first_message[:500]}\""
                }
            ]
        )
        content = response.choices[0].message.content
        title, icon = _parse_title_response(content)
        logger.info(f"Generated chat title: {icon} {title}")
        return title, icon

    except TitleGenerationError:
        raise
    except Exception as e:
        logger.error(f"Error generating chat title: {e}")
        raise TitleGenerationError(str(e)) from e

