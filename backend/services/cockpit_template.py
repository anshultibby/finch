"""Default cockpit board — the "priors" the Finch agent personalizes from.

The cockpit is one `widgets` row (kind="cockpit") whose spec is a list of blocks.
The default adapts to the user's goal kind and whether a brokerage is connected;
the agent then reorders / toggles / configures it per user via the widget edit flow.

Blocks bind to per-viewer symbolic sources (goal / activity / trades / portfolio /
watchlist) + public market data (quote / news), so the board is live with zero
agent involvement.
"""
from typing import Any, Optional

from schemas.widget import WidgetSpec

# Reusable block definitions (dicts → validated into the WidgetSpec).
_GOAL = {"id": "goal", "type": "goal", "size": "full", "query": {"source": "goal"}}
_DESK = {"id": "desk", "type": "activity", "size": "lg", "title": "Finch’s desk",
         "query": {"source": "activity", "limit": 6}}
_TRADES = {"id": "trades", "type": "trades", "size": "md", "title": "Review a recent trade",
           "query": {"source": "trades", "limit": 5}}
_PULSE = {"id": "pulse", "type": "table", "size": "md", "title": "Market pulse",
          "query": {"source": "quote", "symbols": ["SPY", "QQQ", "DIA"]}}
_NEWS = {"id": "news", "type": "news", "size": "md", "title": "Worth knowing",
         "query": {"source": "news", "limit": 3}}
_POSITIONS = {"id": "positions", "type": "table", "size": "md", "title": "Your positions",
              "query": {"source": "user_portfolio"}}
_WATCHLIST = {"id": "watch", "type": "table", "size": "md", "title": "Watchlist",
              "query": {"source": "user_watchlist"}}


def default_cockpit_spec(goal: Optional[Any] = None, *, has_brokerage: bool = False) -> WidgetSpec:
    """The default cockpit board, tuned to the goal kind + connection state.

    The `goal` block is always first (pinned). A connected user gets a live
    Positions block; the rest of the composition leans into what each goal kind
    is actually for (active → trades/pulse; income/protect → holdings + calm).
    """
    kind = getattr(goal, "kind", None) if goal else None

    if kind == "protect":
        tiles = [_GOAL, _DESK, _POSITIONS if has_brokerage else _WATCHLIST, _NEWS]
    elif kind == "income":
        tiles = [_GOAL, _POSITIONS if has_brokerage else _WATCHLIST, _DESK, _NEWS]
    elif kind == "number":
        tiles = [_GOAL, _DESK, _TRADES] + ([_POSITIONS] if has_brokerage else []) + [_PULSE, _NEWS]
    else:  # grow / no goal — the calm default
        tiles = [_GOAL, _DESK, _TRADES] + ([_POSITIONS] if has_brokerage else []) + [_PULSE, _NEWS]

    return WidgetSpec.model_validate({
        "spec_version": 1,
        "tiles": tiles,
        "refresh": {"interval_seconds": 120},
    })
