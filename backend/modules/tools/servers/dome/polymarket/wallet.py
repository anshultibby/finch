"""
Polymarket Wallet - Position and P&L Tracking

Monitor wallet positions and performance.
"""
from typing import Optional, Dict, Any
from .._client import call_dome_api


def get_wallet(wallet_address: str) -> Dict[str, Any]:
    """
    Get wallet information and positions on Polymarket.
    
    Args:
        wallet_address: Ethereum wallet address (0x...)
        
    Returns:
        dict with:
        - address: Wallet address
        - positions: List of active positions with:
            - market_slug: Market identifier
            - condition_id: Condition ID
            - token_id: Token ID
            - outcome: 'Yes' or 'No'
            - size: Position size (shares)
            - average_price: Average entry price
            - current_price: Current market price
            - unrealized_pnl: Unrealized profit/loss
            - value: Current position value
        - total_value: Total portfolio value
        
    Example:
        # Get wallet positions
        wallet = get_wallet("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        if 'error' not in wallet:
            print(f"Total value: ${wallet['total_value']:,.2f}")
            for pos in wallet['positions']:
                print(f"\n{pos['market_slug']}")
                print(f"  Size: {pos['size']} shares")
                print(f"  P&L: ${pos['unrealized_pnl']:,.2f}")
    """
    endpoint = f"/polymarket/wallet/{wallet_address}"
    return call_dome_api(endpoint)


def get_wallet_pnl(
    wallet_address: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get profit and loss history for a wallet on Polymarket.
    
    Args:
        wallet_address: Ethereum wallet address (0x...)
        start_time: Unix timestamp (seconds) for start of range
        end_time: Unix timestamp (seconds) for end of range
        
    Returns:
        dict with:
        - address: Wallet address
        - total_pnl: Total realized P&L
        - total_volume: Total trading volume
        - win_rate: Win rate (0-1)
        - num_trades: Number of trades
        - pnl_history: Daily P&L breakdown with:
            - date: Date
            - realized_pnl: Realized P&L for the day
            - volume: Trading volume
            - num_trades: Number of trades
        - best_trade: Best single trade
        - worst_trade: Worst single trade
        
    Example:
        # Get all-time P&L
        pnl = get_wallet_pnl("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        if 'error' not in pnl:
            print(f"Total P&L: ${pnl['total_pnl']:,.2f}")
            print(f"Win rate: {pnl['win_rate']*100:.1f}%")
            print(f"Total volume: ${pnl['total_volume']:,.0f}")
        
        # Get P&L for specific time period
        import time
        end = int(time.time())
        start = end - (30 * 24 * 60 * 60)  # Last 30 days
        pnl = get_wallet_pnl(
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            start_time=start,
            end_time=end
        )
    """
    endpoint = f"/polymarket/wallet-pnl/{wallet_address}"
    params = {}
    
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    
    return call_dome_api(endpoint, params)
