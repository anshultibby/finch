"""
Friendly wrappers over the Robinhood agentic-trading MCP tools.

Thin convenience layer on top of `_client.call`. Every function returns the
parsed MCP response (a dict). For anything not covered here, use
`_client.call(<tool>, **args)` directly.
"""
from typing import Any, Optional

from ._client import call


# ---- reads ----------------------------------------------------------------

def get_accounts() -> dict:
    """List the user's Robinhood accounts. The agentic account has
    agentic_allowed=True — only it can trade."""
    return call("get_accounts")


def get_portfolio(account_number: str) -> dict:
    """Portfolio value breakdown + buying power for an account."""
    return call("get_portfolio", account_number=account_number)


def get_positions(account_number: str) -> dict:
    """Open equity positions for an account."""
    return call("get_equity_positions", account_number=account_number)


def get_quotes(symbols: list[str]) -> dict:
    """Live quotes + prior-session close for one or more symbols."""
    return call("get_equity_quotes", symbols=symbols)


def get_orders(account_number: str, state: Optional[str] = None,
               symbol: Optional[str] = None) -> dict:
    """Equity orders (newest first). Optionally filter by state/symbol."""
    return call("get_equity_orders", account_number=account_number,
                state=state, symbol=symbol)


def get_tradability(account_number: str, symbols: list[str]) -> dict:
    """Per-session eligibility + fractional support for up to 10 symbols."""
    return call("get_equity_tradability", account_number=account_number, symbols=symbols)


def search(query: str) -> dict:
    """Resolve a company name / partial name to ticker(s) + instrument_id."""
    return call("search", query=query)


# ---- writes ---------------------------------------------------------------

def review_order(account_number: str, symbol: str, side: str, type: str,
                 quantity: Optional[str] = None, dollar_amount: Optional[str] = None,
                 limit_price: Optional[str] = None, stop_price: Optional[str] = None,
                 time_in_force: Optional[str] = None,
                 market_hours: Optional[str] = None) -> dict:
    """Simulate an order (no execution). Returns the quote + pre-trade alerts.
    Call this and show the user before place_order."""
    return call("review_equity_order", account_number=account_number, symbol=symbol,
                side=side, type=type, quantity=quantity, dollar_amount=dollar_amount,
                limit_price=limit_price, stop_price=stop_price,
                time_in_force=time_in_force, market_hours=market_hours)


def place_order(account_number: str, symbol: str, side: str, type: str,
                quantity: Optional[str] = None, dollar_amount: Optional[str] = None,
                limit_price: Optional[str] = None, stop_price: Optional[str] = None,
                time_in_force: Optional[str] = None,
                market_hours: Optional[str] = None) -> dict:
    """Place a REAL equity order with real money. Provide exactly one of
    quantity or dollar_amount (dollar_amount requires type='market')."""
    return call("place_equity_order", account_number=account_number, symbol=symbol,
                side=side, type=type, quantity=quantity, dollar_amount=dollar_amount,
                limit_price=limit_price, stop_price=stop_price,
                time_in_force=time_in_force, market_hours=market_hours)


def cancel_order(account_number: str, order_id: str) -> Any:
    """Cancel an open equity order by id."""
    return call("cancel_equity_order", account_number=account_number, order_id=order_id)


# ---- connection & portfolio helpers ---------------------------------------

def connection_status() -> dict:
    """Whether Robinhood is connected, plus the tradable agentic account.

    Never raises for a missing connection — returns connected=False with a
    `reason` you can relay to the user. Call this FIRST in any trading flow.

    Returns {connected, agentic_account, accounts, reason}.
    """
    import os
    if not os.environ.get("ROBINHOOD_MCP_TOKEN"):
        return {
            "connected": False, "agentic_account": None, "accounts": [],
            "reason": "Robinhood isn't connected. Ask the user to connect it from "
                      "the Portfolio screen — don't guess or use another broker.",
        }
    try:
        data = get_accounts()
    except Exception as e:
        return {
            "connected": False, "agentic_account": None, "accounts": [],
            "reason": f"Token present but the Robinhood call failed: {e}",
        }
    accounts = (data or {}).get("data", {}).get("accounts", []) if isinstance(data, dict) else []
    agentic = next((a["account_number"] for a in accounts if a.get("agentic_allowed")), None)
    return {
        "connected": True,
        "agentic_account": agentic,
        "accounts": accounts,
        "reason": "Connected." if agentic else
                  "Connected, but no agentic-enabled account was found — only an "
                  "agentic account can trade. Ask the user to enable one in Robinhood.",
    }


def portfolio_snapshot(account_number: Optional[str] = None) -> dict:
    """One-call snapshot: agentic account value + buying power + open positions.

    Resolves the agentic account automatically when account_number is omitted.
    Returns {connected, agentic_account, portfolio, positions} or, if not
    connected/eligible, {connected, reason}.
    """
    status = connection_status()
    if not status["connected"]:
        return {"connected": False, "reason": status["reason"]}
    acct = account_number or status["agentic_account"]
    if not acct:
        return {"connected": True, "agentic_account": None, "reason": status["reason"]}
    return {
        "connected": True,
        "agentic_account": acct,
        "portfolio": get_portfolio(acct),
        "positions": get_positions(acct),
    }
