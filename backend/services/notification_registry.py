"""
In-memory registry for chat completion email notifications.

When a user requests email notification for a chat, their email is stored here.
When the chat stream completes, the registry is checked and an email is sent.

NOTE: This is intentionally in-memory because the notification is only relevant
for the duration of a single SSE stream, which is held open by the same worker
process. If the worker crashes, the stream breaks anyway so the notification
becomes moot. A database-backed approach would add latency for no practical gain.

Stale entries (from abandoned streams) are evicted after MAX_AGE_SECONDS.
"""

import time

# chat_id -> (user_email, registered_at)
_email_notify_registry: dict[str, tuple[str, float]] = {}

MAX_AGE_SECONDS = 3600  # 1 hour


def _evict_stale() -> None:
    """Remove entries older than MAX_AGE_SECONDS to prevent memory leaks."""
    cutoff = time.monotonic() - MAX_AGE_SECONDS
    stale = [k for k, (_, ts) in _email_notify_registry.items() if ts < cutoff]
    for k in stale:
        del _email_notify_registry[k]


def register_email_notification(chat_id: str, email: str) -> None:
    _evict_stale()
    _email_notify_registry[chat_id] = (email, time.monotonic())


def pop_email_notification(chat_id: str) -> str | None:
    entry = _email_notify_registry.pop(chat_id, None)
    if entry is None:
        return None
    return entry[0]
