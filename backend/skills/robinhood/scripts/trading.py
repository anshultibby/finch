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


# ---- options ---------------------------------------------------------------
# Single-leg only (long calls/puts, covered calls, cash-secured puts) — the MCP
# does NOT support multi-leg spreads, even on option_level_3 accounts. The
# account must be agentic_allowed=True AND option_level_2/option_level_3
# (see connection_status()["options_enabled"]).

def get_option_chains(underlying_symbol: str) -> dict:
    """Chains for an underlying: expiration dates + chain ids (equity or index,
    e.g. 'AAPL', 'SPX')."""
    return call("get_option_chains", underlying_symbol=underlying_symbol)


def find_option_instruments(chain_symbol: str, expiration_date: Optional[str] = None,
                            strike_price: Optional[str] = None,
                            type: Optional[str] = None) -> dict:
    """Contracts for an underlying, narrowed by expiry (YYYY-MM-DD), strike
    (e.g. '150.0000'), and type ('call'/'put'). The returned `id` (UUID) is the
    option_id used everywhere else."""
    return call("get_option_instruments", chain_symbol=chain_symbol,
                expiration_dates=expiration_date, strike_price=strike_price,
                type=type, tradability="tradable")


def get_option_quotes(instrument_ids: list[str]) -> dict:
    """Live quotes (+ prior close) for up to ~20 option instrument UUIDs."""
    return call("get_option_quotes", instrument_ids=instrument_ids)


def get_option_positions(account_number: str, nonzero: bool = True) -> dict:
    """Open option positions (nonzero=True is the 'what do I hold' case)."""
    return call("get_option_positions", account_number=account_number, nonzero=nonzero)


def get_option_orders(account_number: str, state: Optional[str] = None) -> dict:
    """Option orders, newest first."""
    return call("get_option_orders", account_number=account_number, state=state)


def review_option_order(account_number: str, option_id: str, side: str,
                        position_effect: str, quantity: str,
                        type: str = "limit", price: Optional[str] = None,
                        stop_price: Optional[str] = None,
                        chain_symbol: Optional[str] = None,
                        underlying_type: Optional[str] = None,
                        time_in_force: Optional[str] = None) -> dict:
    """Simulate a SINGLE-LEG option order — quote, fees, collateral, alerts.
    Always call before place_option_order and surface order_checks verbatim.
    side='buy'/'sell'; position_effect='open'/'close' (close a long → sell).
    Pass chain_symbol + underlying_type ('equity'/'index') to get fees/collateral."""
    return call("review_option_order", account_number=account_number,
                legs=[{"option_id": option_id, "side": side,
                       "position_effect": position_effect}],
                quantity=quantity, type=type, price=price, stop_price=stop_price,
                chain_symbol=chain_symbol, underlying_type=underlying_type,
                time_in_force=time_in_force)


def place_option_order(account_number: str, option_id: str, side: str,
                       position_effect: str, quantity: str,
                       type: str = "limit", price: Optional[str] = None,
                       stop_price: Optional[str] = None,
                       ref_id: Optional[str] = None,
                       time_in_force: Optional[str] = None) -> dict:
    """Place a REAL single-leg option order. price per contract for
    limit/stop_limit; stop_market is sell-to-close only (stop below the ask),
    market/stop_market are GFD + regular hours only. Pass a fresh uuid4 hex as
    ref_id and reuse the SAME ref_id when retrying a transport failure."""
    return call("place_option_order", account_number=account_number,
                legs=[{"option_id": option_id, "side": side,
                       "position_effect": position_effect}],
                quantity=quantity, type=type, price=price, stop_price=stop_price,
                ref_id=ref_id, time_in_force=time_in_force)


def cancel_option_order(account_number: str, order_id: str) -> Any:
    """Cancel an open option order by id."""
    return call("cancel_option_order", account_number=account_number, order_id=order_id)


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
    agentic_acct = next((a for a in accounts if a.get("agentic_allowed")), None)
    agentic = agentic_acct["account_number"] if agentic_acct else None
    options_enabled = bool(agentic_acct and agentic_acct.get("option_level")
                           in ("option_level_2", "option_level_3"))
    return {
        "connected": True,
        "agentic_account": agentic,
        "options_enabled": options_enabled,  # single-leg options trading allowed
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
