"""
Low-level MCP client for Robinhood agentic trading, for use inside the E2B
sandbox. Uses the OAuth access token + MCP URL injected by the backend as env
vars (ROBINHOOD_MCP_TOKEN / ROBINHOOD_MCP_URL).

Exposes a synchronous `call(tool, **args)` so agent-written code stays simple —
each call opens a short-lived MCP session, invokes one tool, and returns the
parsed JSON result.
"""
import asyncio
import json
import os
from typing import Any

DEFAULT_MCP_URL = "https://agent.robinhood.com/mcp/trading"


def _require_token() -> str:
    token = os.environ.get("ROBINHOOD_MCP_TOKEN")
    if not token:
        raise RuntimeError(
            "ROBINHOOD_MCP_TOKEN is not set — the user hasn't connected Robinhood. "
            "Ask them to connect it in Settings > Connections."
        )
    return token


def _mcp_url() -> str:
    return os.environ.get("ROBINHOOD_MCP_URL") or DEFAULT_MCP_URL


def _parse(result: Any) -> Any:
    """Extract JSON/text from an MCP CallToolResult into plain Python."""
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text is None:
            continue
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return text
    return getattr(result, "structuredContent", None)


async def _acall(tool: str, arguments: dict) -> Any:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"Authorization": f"Bearer {_require_token()}"}
    async with streamablehttp_client(_mcp_url(), headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
    return _parse(result)


def call(tool: str, **arguments: Any) -> Any:
    """Call a Robinhood MCP tool by name. Returns the parsed JSON response.

    Example: call("get_equity_quotes", symbols=["AAPL"]) """
    # Drop None args so we don't send nulls the MCP server rejects.
    clean = {k: v for k, v in arguments.items() if v is not None}
    return asyncio.run(_acall(tool, clean))


def list_tools() -> list[dict]:
    """List the tools the Robinhood MCP server exposes (name + description)."""
    async def _list():
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        headers = {"Authorization": f"Bearer {_require_token()}"}
        async with streamablehttp_client(_mcp_url(), headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
        return [{"name": t.name, "description": t.description} for t in tools.tools]

    return asyncio.run(_list())
