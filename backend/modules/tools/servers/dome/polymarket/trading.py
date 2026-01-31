"""
Polymarket Trading - Market-Wide Trade History

Track historical trades across markets (not wallet-specific).
For wallet-specific activity, use get_wallet_activity from wallet.py instead.
"""
from typing import Optional, Dict, Any
from .._client import call_dome_api


def get_trade_history(
    condition_id: Optional[str] = None,
    market_slug: Optional[str] = None,
    token_id: Optional[str] = None,
    maker_address: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get market-wide trade history (all trades across the platform).
    
    NOTE: For wallet-specific trades, use get_wallet_activity() from wallet.py instead.
    This endpoint returns all trades on the platform matching your filters.
    
    Args:
        condition_id: Filter by condition ID
        market_slug: Filter by market slug
        token_id: Filter by token ID (specific outcome)
        maker_address: Filter by maker wallet address
        start_time: Unix timestamp (seconds) for start of range
        end_time: Unix timestamp (seconds) for end of range
        limit: Number of trades to return (1-1000, default 100)
        offset: Number to skip for pagination (default 0)
        
    Returns:
        dict with:
        - trades: List of trades with:
            - id: Trade ID
            - market_slug: Market identifier
            - condition_id: Condition ID
            - token_id: Token ID
            - side: 'BUY' or 'SELL'
            - price: Trade price (0-1)
            - size: Trade size (shares)
            - timestamp: Trade timestamp
            - maker_address: Maker wallet address
            - taker_address: Taker wallet address
        - pagination: Pagination info
        
    Example:
        # Get recent trades for a specific market
        trades = get_trade_history(
            condition_id="0x4567b275...",
            limit=50
        )
        if 'error' not in trades:
            for trade in trades['trades']:
                print(f"{trade['timestamp']}: {trade['side']} "
                      f"{trade['size']} @ ${trade['price']}")
        
        # For wallet-specific trades, use wallet.get_wallet_activity() instead:
        # from servers.dome.polymarket.wallet import get_wallet_activity
        # activity = get_wallet_activity("0xabc123...", limit=100)
    """
    params = {
        "limit": min(max(1, limit), 1000),
        "offset": max(0, offset)
    }
    
    if condition_id:
        params["condition_id"] = condition_id
    if market_slug:
        params["market_slug"] = market_slug
    if token_id:
        params["token_id"] = token_id
    if maker_address:
        params["maker_address"] = maker_address
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    
    return call_dome_api("/polymarket/trades", params)
