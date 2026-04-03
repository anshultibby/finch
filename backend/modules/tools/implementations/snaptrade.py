"""SnapTrade tool implementations"""
from typing import Dict, Any, Optional
from modules.agent.context import AgentContext
from core.config import Config


async def connect_brokerage_impl(
    context: AgentContext,
    broker: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate OAuth URL for user to connect their brokerage."""
    from modules.tools.clients.snaptrade import snaptrade_tools

    redirect_uri = f"{Config.APP_BASE_URL}/portfolio?snaptrade_callback=true"

    result = snaptrade_tools.get_login_redirect_uri_for_broker(
        user_id=context.user_id,
        redirect_uri=redirect_uri,
        broker_id=broker,
    )

    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("message", "Failed to generate connection URL"),
        }

    return {
        "success": True,
        "connection_url": result["redirect_uri"],
        "broker": result.get("broker_id"),
        "message": f"Connection URL generated. The user should open this link to connect: {result['redirect_uri']}",
    }


async def get_brokerage_status_impl(context: AgentContext) -> Dict[str, Any]:
    """Check whether the user has connected a brokerage."""
    from modules.tools.clients.snaptrade import snaptrade_tools

    session = snaptrade_tools._get_session(context.user_id)

    if not session or not session.is_connected:
        return {
            "success": True,
            "connected": False,
            "accounts": [],
            "message": "User has no brokerage connected. Use connect_brokerage to start the connection flow.",
        }

    try:
        accounts_result = await snaptrade_tools.get_connected_accounts(context.user_id)
        accounts = accounts_result.get("accounts", [])
    except Exception:
        accounts = []

    return {
        "success": True,
        "connected": True,
        "account_count": len(accounts),
        "accounts": accounts,
    }


async def get_portfolio_impl(context: AgentContext) -> Dict[str, Any]:
    """Fetch portfolio holdings across all connected accounts."""
    from modules.tools.clients.snaptrade import snaptrade_tools

    session = snaptrade_tools._get_session(context.user_id)
    if not session or not session.is_connected:
        return {
            "success": False,
            "error": "No brokerage connected. Use connect_brokerage first.",
        }

    try:
        result = await snaptrade_tools.get_portfolio(context.user_id)
    except Exception as e:
        return {"success": False, "error": str(e)}

    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("message", "Failed to fetch portfolio"),
        }

    return result
