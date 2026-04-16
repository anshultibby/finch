"""
Alpaca / TLH tool implementations.

Only present_swaps lives here as a tool — all actual trading
operations are handled by the alpaca skill via bash in the sandbox.
"""
from typing import Dict, Any, List
from modules.agent.context import AgentContext
from utils.logger import get_logger

logger = get_logger(__name__)


def _opportunity_to_swap(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a build_tlh_plan opportunity dict to a frontend SwapData object."""
    candidates = opp.get("substitute_candidates") or []
    primary = candidates[0] if candidates else {}
    quality = primary.get("correlation_quality", "")
    sector = "sector peer" if primary.get("is_sector_peer") else "universe pick"
    buy_reason = f"{quality} correlation ({sector})" if quality else sector

    # Include all candidates (up to 5) so the UI can show options and track correlations
    substitute_candidates = []
    for c in candidates[:5]:
        q = c.get("correlation_quality", "")
        s = "sector peer" if c.get("is_sector_peer") else "universe pick"
        substitute_candidates.append({
            "symbol":        c.get("symbol", ""),
            "correlation":   c.get("correlation", 0),
            "quality":       q,
            "reason":        f"{q} correlation ({s})" if q else s,
            "is_sector_peer": c.get("is_sector_peer", False),
        })

    return {
        "sell_symbol":            opp.get("symbol", ""),
        "sell_qty":               opp.get("shares", 0),
        "sell_loss":              opp.get("dollar_loss", 0),
        "sell_loss_pct":          opp.get("loss_pct", 0),
        "buy_symbol":             primary.get("symbol", ""),
        "buy_reason":             buy_reason,
        "estimated_savings":      opp.get("estimated_tax_savings", 0),
        "correlation":            primary.get("correlation", 0),
        "substitute_candidates":  substitute_candidates,
    }


async def present_swaps_impl(context: AgentContext, plan_file: str) -> Dict[str, Any]:
    """Read a build_tlh_plan JSON file from the sandbox and send opportunities to the frontend."""
    import json
    from modules.tools.implementations.code_execution import get_or_create_sandbox, _build_sandbox_env

    envs = await _build_sandbox_env(context)
    entry = await get_or_create_sandbox(context.user_id, envs)
    sbx = entry.sbx

    raw = await sbx.files.read(plan_file, format="text")
    plan = json.loads(raw)

    harvest_now = plan.get("harvest_now") or []
    borderline = plan.get("borderline") or []
    opportunities = harvest_now + borderline

    if not opportunities:
        return {
            "success": True,
            "swaps": [],
            "total_swaps": 0,
            "total_estimated_savings": 0,
            "message": "No harvest opportunities found.",
        }

    swaps = [_opportunity_to_swap(opp) for opp in opportunities]
    total_savings = sum(s["estimated_savings"] for s in swaps)

    return {
        "success": True,
        "swaps": swaps,
        "total_swaps": len(swaps),
        "total_estimated_savings": round(total_savings, 2),
        "message": f"Presenting {len(swaps)} swap opportunities (~${total_savings:,.0f} estimated savings). Check the Opportunities tab.",
    }
