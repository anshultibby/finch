"""In-memory registry for chat email notifications.

Avoids DB writes on the chat row while the stream is active, which can
cause row-lock contention and interrupt the LLM stream.
"""
import time
from typing import Optional, Dict, Tuple

_registry: Dict[str, Tuple[str, float]] = {}  # chat_id -> (email, registered_at)

TTL_SECONDS = 3600  # auto-expire after 1 hour


def register(chat_id: str, email: str) -> None:
    _registry[chat_id] = (email, time.monotonic())


def pop(chat_id: str) -> Optional[str]:
    entry = _registry.pop(chat_id, None)
    if entry is None:
        return None
    email, registered_at = entry
    if time.monotonic() - registered_at > TTL_SECONDS:
        return None
    return email
