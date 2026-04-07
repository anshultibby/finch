"""
Alpaca account operations — check status, buying power, positions.
"""
from skills.alpaca.scripts._client import get_trading_client


def get_account_info(paper: bool = True):
    """Get account info: status, buying power, equity, etc."""
    client = get_trading_client(paper=paper)
    account = client.get_account()
    return {
        "id": str(account.id),
        "status": str(account.status),
        "buying_power": float(account.buying_power),
        "equity": float(account.equity),
        "cash": float(account.cash),
        "portfolio_value": float(account.portfolio_value),
        "pattern_day_trader": account.pattern_day_trader,
        "trading_blocked": account.trading_blocked,
    }


def get_positions(paper: bool = True):
    """Get all open positions in the Alpaca account."""
    client = get_trading_client(paper=paper)
    positions = client.get_all_positions()
    result = []
    for pos in positions:
        result.append({
            "symbol": pos.symbol,
            "qty": float(pos.qty),
            "side": str(pos.side),
            "market_value": float(pos.market_value),
            "cost_basis": float(pos.cost_basis),
            "unrealized_pl": float(pos.unrealized_pl),
            "unrealized_plpc": float(pos.unrealized_plpc),
            "current_price": float(pos.current_price),
            "avg_entry_price": float(pos.avg_entry_price),
        })
    return result
