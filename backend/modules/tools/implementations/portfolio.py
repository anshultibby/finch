"""
Portfolio tool implementations - Brokerage and portfolio management
"""
from typing import Dict, Any, AsyncGenerator
from modules.agent.context import AgentContext
from modules.tools.clients.snaptrade import snaptrade_tools


async def get_portfolio_impl(context: AgentContext) -> AsyncGenerator:
    """Get user's portfolio holdings"""
    if not context.user_id:
        yield {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
        return
    
    # Call client which will yield SSE events and then result
    async for item in snaptrade_tools.get_portfolio_streaming(
        user_id=context.user_id
    ):
        yield item


def request_brokerage_connection_impl(context: AgentContext) -> Dict[str, Any]:
    """Request user to connect their brokerage account"""
    return {
        "success": True,
        "needs_auth": True,
        "message": "Please connect your brokerage account through SnapTrade to continue.",
        "action_required": "show_connection_modal"
    }

