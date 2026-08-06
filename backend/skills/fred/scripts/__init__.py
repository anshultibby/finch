"""FRED skill — US macro data and the macro event calendar.

Re-exported here so `from skills.fred.scripts import upcoming_events` works,
matching the other skills. The submodule paths still work too.
"""
from .series import (
    KEY_SERIES,
    get_series,
    latest,
    macro_snapshot,
    search_series,
)
from .releases import (
    events_today,
    upcoming_events,
)

__all__ = [
    "KEY_SERIES",
    "get_series",
    "latest",
    "macro_snapshot",
    "search_series",
    "events_today",
    "upcoming_events",
]
