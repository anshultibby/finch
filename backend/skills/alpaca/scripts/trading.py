"""
Alpaca trading operations — place orders, execute swaps.
"""
from skills.alpaca.scripts._client import get_trading_client


def execute_swap(sell_symbol: str, sell_qty: float, buy_symbol: str, buy_notional: float, paper: bool = True):
    """Execute a TLH swap: sell the loser, buy the replacement.

    Args:
        sell_symbol: Symbol to sell (e.g. "TSLA")
        sell_qty: Number of shares to sell
        buy_symbol: Replacement symbol to buy (e.g. "RIVN")
        buy_notional: Dollar amount to buy of the replacement
        paper: Use paper trading (default True)

    Returns:
        Dict with sell_order and buy_order details
    """
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    client = get_trading_client(paper=paper)
    result = {"success": True}

    # Step 1: Sell the losing position
    sell_order = client.submit_order(
        MarketOrderRequest(
            symbol=sell_symbol,
            qty=sell_qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
    )
    result["sell_order"] = {
        "id": str(sell_order.id),
        "symbol": sell_symbol,
        "qty": sell_qty,
        "side": "sell",
        "status": str(sell_order.status),
    }

    # Step 2: Buy the replacement
    buy_order = client.submit_order(
        MarketOrderRequest(
            symbol=buy_symbol,
            notional=buy_notional,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
    )
    result["buy_order"] = {
        "id": str(buy_order.id),
        "symbol": buy_symbol,
        "notional": buy_notional,
        "side": "buy",
        "status": str(buy_order.status),
    }

    return result


def place_order(symbol: str, qty: float = None, notional: float = None,
                side: str = "buy", paper: bool = True):
    """Place a single market order.

    Args:
        symbol: Stock symbol
        qty: Number of shares (use this OR notional)
        notional: Dollar amount (use this OR qty)
        side: "buy" or "sell"
        paper: Use paper trading (default True)
    """
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    client = get_trading_client(paper=paper)

    order_params = {
        "symbol": symbol,
        "side": OrderSide.BUY if side == "buy" else OrderSide.SELL,
        "time_in_force": TimeInForce.DAY,
    }
    if qty is not None:
        order_params["qty"] = qty
    elif notional is not None:
        order_params["notional"] = notional
    else:
        raise ValueError("Must provide either qty or notional")

    order = client.submit_order(MarketOrderRequest(**order_params))
    return {
        "id": str(order.id),
        "symbol": symbol,
        "side": side,
        "status": str(order.status),
        "qty": str(order.qty) if order.qty else None,
        "notional": str(order.notional) if order.notional else None,
    }


def get_orders(paper: bool = True, limit: int = 20):
    """Get recent orders."""
    from alpaca.trading.requests import GetOrdersRequest

    client = get_trading_client(paper=paper)
    orders = client.get_orders(GetOrdersRequest(limit=limit))
    result = []
    for o in orders:
        result.append({
            "id": str(o.id),
            "symbol": o.symbol,
            "side": str(o.side),
            "qty": str(o.qty) if o.qty else None,
            "notional": str(o.notional) if o.notional else None,
            "status": str(o.status),
            "filled_qty": str(o.filled_qty) if o.filled_qty else None,
            "filled_avg_price": str(o.filled_avg_price) if o.filled_avg_price else None,
            "submitted_at": str(o.submitted_at) if o.submitted_at else None,
        })
    return result


def mirror_portfolio(positions: list, paper: bool = True):
    """Mirror real portfolio positions into Alpaca paper account.

    Args:
        positions: List of dicts with {symbol, units} from get_portfolio
        paper: Must be True for mirroring

    Returns:
        Dict with mirrored positions and any errors
    """
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    client = get_trading_client(paper=paper)
    mirrored = []
    errors = []

    for pos in positions:
        symbol = pos.get("symbol", "")
        qty = pos.get("units", 0)
        if not symbol or not qty or qty <= 0:
            continue
        try:
            order = client.submit_order(
                MarketOrderRequest(
                    symbol=symbol,
                    qty=float(qty),
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                )
            )
            mirrored.append({"symbol": symbol, "qty": float(qty), "status": str(order.status)})
        except Exception as e:
            errors.append({"symbol": symbol, "error": str(e)})

    return {
        "mirrored": mirrored,
        "errors": errors,
        "total_mirrored": len(mirrored),
        "total_errors": len(errors),
    }
