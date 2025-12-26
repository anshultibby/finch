"""
Chat title and icon generation service using LLM
"""
import json
from typing import Optional, Tuple
from pydantic import BaseModel
from anthropic import Anthropic
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class ChatTitleResponse(BaseModel):
    """Response from the chat title generation"""
    title: str
    icon: str


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

Respond ONLY with a valid JSON object, no markdown or extra text."""


async def generate_chat_title(first_message: str) -> Tuple[str, str]:
    """
    Generate a title and icon for a chat based on the first message.
    
    Args:
        first_message: The first user message in the chat
        
    Returns:
        Tuple of (title, icon)
    """
    try:
        client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Use Sonnet for better titles
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": f"Generate a title and icon for a chat that starts with this message:\n\n\"{first_message[:500]}\""
                }
            ],
            system=TITLE_GENERATION_PROMPT
        )
        
        # Parse the response
        content = response.content[0].text.strip()
        
        # Try to parse JSON
        try:
            data = json.loads(content)
            title = data.get("title", "New Chat")[:50]  # Limit title length
            icon = data.get("icon", "💬")
            
            # Validate icon is actually an emoji (basic check)
            if not icon or len(icon) > 4:
                icon = "💬"
                
            logger.info(f"Generated chat title: {icon} {title}")
            return title, icon
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse title response as JSON: {content}")
            # Fallback to extracting from text
            return "New Chat", "💬"
            
    except Exception as e:
        logger.error(f"Error generating chat title: {e}")
        return "New Chat", "💬"

