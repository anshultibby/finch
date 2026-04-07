"""
Alpaca / TLH tool implementations.

Only present_swaps lives here as a tool — all actual trading
operations are handled by the alpaca skill via bash in the sandbox.
"""
from typing import Dict, Any, List
from modules.agent.context import AgentContext
from utils.logger import get_logger

logger = get_logger(__name__)


async def present_swaps_impl(context: AgentContext, swaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate and return structured swap data for frontend rendering."""
    validated = []
    for swap in swaps:
        validated.append({
            "sell_symbol": swap.get("sell_symbol", ""),
            "sell_qty": swap.get("sell_qty", 0),
            "sell_loss": swap.get("sell_loss", 0),
            "sell_loss_pct": swap.get("sell_loss_pct", 0),
            "buy_symbol": swap.get("buy_symbol", ""),
            "buy_reason": swap.get("buy_reason", ""),
            "estimated_savings": swap.get("estimated_savings", 0),
            "correlation": swap.get("correlation", 0),
        })

    total_savings = sum(s["estimated_savings"] for s in validated)

    return {
        "success": True,
        "swaps": validated,
        "total_swaps": len(validated),
        "total_estimated_savings": round(total_savings, 2),
        "message": f"Found {len(validated)} tax loss harvesting opportunities with ~${total_savings:,.0f} in estimated savings.",
    }
