"""
Polymarket Wallet - Position and P&L Tracking

Monitor wallet positions and performance.
"""
from typing import Optional, Dict, Any, Literal
from .._client import call_dome_api


def get_wallet_info(
    eoa: Optional[str] = None,
    proxy: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get wallet address mapping (EOA <-> Proxy).
    
    Args:
        eoa: EOA (Externally Owned Account) wallet address
        proxy: Proxy wallet address
        (Provide one of eoa or proxy, not both)
        
    Returns:
        dict with:
        - eoa: EOA wallet address
        - proxy: Proxy wallet address
        - wallet_type: Type of wallet (e.g., 'safe')
        
    Example:
        # Get proxy from EOA
        info = get_wallet_info(eoa="0xe9a69b28ffd86f6ea0c5d8171c95537479b84a29")
        if 'error' not in info:
            print(f"Proxy: {info['proxy']}")
    """
    params = {}
    if eoa:
        params["eoa"] = eoa
    if proxy:
        params["proxy"] = proxy
    
    return call_dome_api("/polymarket/wallet", params)


def get_positions(
    wallet_address: str,
    limit: int = 100,
    pagination_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all positions for a wallet on Polymarket.
    
    Args:
        wallet_address: Proxy wallet address (0x...)
        limit: Max positions to return (1-100, default 100)
        pagination_key: Key for fetching next page
        
    Returns:
        dict with:
        - wallet_address: Wallet address
        - positions: List of active positions with:
            - wallet: Wallet address
            - token_id: Token ID
            - condition_id: Condition ID
            - title: Market title
            - shares: Raw shares (divide by 1e6 for normalized)
            - shares_normalized: Position size in shares
            - redeemable: If position can be redeemed
            - market_slug: Market identifier
            - event_slug: Event identifier
            - label: Outcome label ('Yes' or 'No')
            - winning_outcome: Winning outcome if resolved
            - market_status: Market status
        - pagination: Pagination info
        
    Example:
        # Get wallet positions
        result = get_positions("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        if 'error' not in result:
            print(f"Found {len(result['positions'])} positions")
            for pos in result['positions']:
                print(f"{pos['title']}: {pos['shares_normalized']} {pos['label']} shares")
    """
    endpoint = f"/polymarket/positions/wallet/{wallet_address}"
    params = {"limit": min(max(1, limit), 100)}
    
    if pagination_key:
        params["pagination_key"] = pagination_key
    
    return call_dome_api(endpoint, params)


def get_wallet_pnl(
    wallet_address: str,
    granularity: Literal["day", "week", "month", "year", "all"] = "day",
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get profit and loss history for a wallet on Polymarket.
    
    NOTE: This returns REALIZED P&L only (from sells/redeems), not unrealized.
    This differs from Polymarket's dashboard which shows historical unrealized PnL.
    
    Args:
        wallet_address: Proxy wallet address (0x...)
        granularity: Time granularity ('day', 'week', 'month', 'year', 'all')
        start_time: Unix timestamp (seconds) for start (defaults to first trade)
        end_time: Unix timestamp (seconds) for end (defaults to now)
        
    Returns:
        dict with:
        - granularity: Granularity used
        - start_time: Start timestamp
        - end_time: End timestamp
        - wallet_address: Wallet address
        - pnl_over_time: Array of P&L data points with:
            - timestamp: Unix timestamp
            - pnl_to_date: Cumulative realized P&L up to this point
        
    Example:
        # Get daily P&L over time
        pnl = get_wallet_pnl(
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            granularity="day"
        )
        if 'error' not in pnl:
            latest = pnl['pnl_over_time'][-1]
            print(f"Total realized P&L: ${latest['pnl_to_date']:,.2f}")
        
        # Get P&L for specific time period
        import time
        end = int(time.time())
        start = end - (30 * 24 * 60 * 60)  # Last 30 days
        pnl = get_wallet_pnl(
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            granularity="day",
            start_time=start,
            end_time=end
        )
    """
    endpoint = f"/polymarket/wallet/pnl/{wallet_address}"
    params = {"granularity": granularity}
    
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    
    return call_dome_api(endpoint, params)


def get_wallet_activity(
    wallet_address: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    market_slug: Optional[str] = None,
    condition_id: Optional[str] = None,
    limit: int = 100,
    pagination_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get on-chain activity (SPLITS, MERGES, REDEEMS) for a wallet.
    
    NOTE: This endpoint returns SPLITS, MERGES, and REDEEMS only - NOT actual
    BUY/SELL trade executions. This is by design from Dome API.
    
    For actual BUY/SELL trade execution data, use:
        from servers.dome.polymarket.trading import get_orders
        orders = get_orders(user="0x...", limit=100)
    
    Args:
        wallet_address: Proxy wallet address (0x...)
        start_time: Unix timestamp (seconds) filter from (inclusive)
        end_time: Unix timestamp (seconds) filter until (inclusive)
        market_slug: Filter by specific market
        condition_id: Filter by specific condition ID
        limit: Number of activities to return (1-1000, default 100)
        pagination_key: Cursor for pagination (from previous response)
        
    Returns:
        dict with:
        - activities: List of activity records with:
            - token_id: Token ID
            - side: 'SPLIT', 'MERGE', or 'REDEEM' (NOT BUY/SELL)
            - market_slug: Market identifier
            - condition_id: Condition ID
            - shares: Raw shares
            - shares_normalized: Normalized shares
            - price: Price at time of activity (1 for redeems)
            - tx_hash: Transaction hash
            - title: Market title
            - timestamp: Unix timestamp
            - user: User wallet address
        - pagination: Pagination info with limit, count, has_more, pagination_key
        
    Example:
        # Get redemption and merge activity for a wallet
        activity = get_wallet_activity(
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            limit=50
        )
        if 'error' not in activity:
            for act in activity['activities']:
                if act['side'] == 'REDEEM':
                    print(f"Redeemed {act['shares_normalized']} shares - {act['title']}")
        
        # For actual BUY/SELL trades, use get_orders instead:
        from servers.dome.polymarket.trading import get_orders
        orders = get_orders(user="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", limit=100)
    """
    params = {
        "user": wallet_address,
        "limit": min(max(1, limit), 1000)
    }
    
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if market_slug:
        params["market_slug"] = market_slug
    if condition_id:
        params["condition_id"] = condition_id
    if pagination_key:
        params["pagination_key"] = pagination_key
    
    return call_dome_api("/polymarket/activity", params)


def get_wallet_trades(
    wallet_address: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    market_slug: Optional[str] = None,
    condition_id: Optional[str] = None,
    token_id: Optional[str] = None,
    limit: int = 100,
    pagination_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get actual BUY/SELL trade executions for a wallet.
    
    This returns real trade execution data with prices, shares, and timestamps.
    Use this for copy trading, trade analysis, and performance tracking.
    
    Args:
        wallet_address: Wallet address (0x...)
        start_time: Unix timestamp (seconds) filter from (inclusive)
        end_time: Unix timestamp (seconds) filter until (inclusive)
        market_slug: Filter by specific market
        condition_id: Filter by specific condition ID
        token_id: Filter by specific token ID (Yes/No outcome)
        limit: Number of trades to return (1-1000, default 100)
        pagination_key: Cursor for pagination (from previous response)
        
    Returns:
        dict with:
        - orders: List of executed orders with:
            - token_id: Token ID
            - token_label: 'Yes' or 'No'
            - side: 'BUY' or 'SELL'
            - market_slug: Market identifier
            - condition_id: Condition ID
            - shares_normalized: Normalized share amount
            - price: Execution price (0-1)
            - tx_hash: Transaction hash
            - title: Market title
            - timestamp: Unix timestamp of execution
            - user: Maker wallet address
            - taker: Taker wallet address
        - pagination: Pagination info
        
    Example:
        # Get a trader's recent executions
        trades = get_wallet_trades("0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee", limit=100)
        if 'error' not in trades:
            for order in trades['orders']:
                print(f"{order['side']} {order['shares_normalized']:.2f} @ ${order['price']:.2f}")
                print(f"  Market: {order['title']}")
                print(f"  Time: {order['timestamp']}")
    """
    params = {
        "user": wallet_address,
        "limit": min(max(1, limit), 1000)
    }
    
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if market_slug:
        params["market_slug"] = market_slug
    if condition_id:
        params["condition_id"] = condition_id
    if token_id:
        params["token_id"] = token_id
    if pagination_key:
        params["pagination_key"] = pagination_key
    
    return call_dome_api("/polymarket/orders", params)
