"""Default cockpit board — the "priors" the Finch agent personalizes from.

The cockpit is one `widgets` row (kind="cockpit") whose spec is a list of blocks.
This is the strong default layout every user starts with; the agent then
reorders / toggles / configures it per user via the normal widget edit flow.

Blocks bind to per-viewer symbolic sources (goal / activity) + public market
data (quote / news), so the board is live with zero agent involvement.
"""
from typing import Any, Optional

from schemas.widget import WidgetSpec


def default_cockpit_spec(goal: Optional[Any] = None) -> WidgetSpec:
    """The default cockpit board. `goal` is accepted for future per-kind tuning;
    today every kind gets the same blocks and the `goal` block adapts itself
    (trajectory for number/grow, a calmer summary for income/protect)."""
    tiles = [
        {"id": "goal", "type": "goal", "size": "full", "query": {"source": "goal"}},
        {"id": "desk", "type": "activity", "size": "lg", "title": "Finch’s desk",
         "query": {"source": "activity", "limit": 6}},
        {"id": "trades", "type": "trades", "size": "md", "title": "Review a recent trade",
         "query": {"source": "trades", "limit": 5}},
        {"id": "pulse", "type": "table", "size": "md", "title": "Market pulse",
         "query": {"source": "quote", "symbols": ["SPY", "QQQ", "DIA"]}},
        {"id": "news", "type": "news", "size": "md", "title": "Worth knowing",
         "query": {"source": "news", "limit": 3}},
    ]
    return WidgetSpec.model_validate({
        "spec_version": 1,
        "tiles": tiles,
        "refresh": {"interval_seconds": 120},
    })
