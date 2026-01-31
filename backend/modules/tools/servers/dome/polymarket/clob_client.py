"""
Polymarket CLOB Client - Direct API access using official py-clob-client

This provides direct access to Polymarket's Central Limit Order Book (CLOB)
without requiring Dome API, which has been experiencing 403 errors.

For read-only operations, no authentication is needed.
For trading operations, you'll need a private key and optional funder address.
"""
from typing import Optional, Dict, Any, List
import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams, OpenOrderParams

logger = logging.getLogger(__name__)


def get_clob_client(
    private_key: Optional[str] = None,
    funder: Optional[str] = None,
    signature_type: int = 0
) -> ClobClient:
    """
    Get a Polymarket CLOB client instance.
    
    Args:
        private_key: Wallet private key (optional, only needed for trading)
        funder: Funder address for proxy wallets (optional)
        signature_type: 0 for EOA, 1 for email/Magic wallet, 2 for browser proxy
        
    Returns:
        ClobClient instance
        
    Example:
        # Read-only client (no auth needed)
        client = get_clob_client()
        markets = client.get_simplified_markets()
        
        # Trading client (requires auth)
        client = get_clob_client(
            private_key="0x...",
            funder="0x...",
            signature_type=1
        )
    """
    HOST = "https://clob.polymarket.com"
    CHAIN_ID = 137  # Polygon
    
    if private_key:
        # Authenticated client for trading
        client = ClobClient(
            HOST,
            key=private_key,
            chain_id=CHAIN_ID,
            signature_type=signature_type,
            funder=funder
        )
        client.set_api_creds(client.create_or_derive_api_creds())
    else:
        # Read-only client
        client = ClobClient(HOST)
    
    return client


def get_markets_clob(
    limit: int = 10,
    offset: int = 0,
    active: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Get markets using CLOB client (direct API, no Dome required).
    
    Args:
        limit: Number of markets to return (default 10)
        offset: Pagination offset (default 0)
        active: Filter by active status (optional)
        
    Returns:
        dict with:
        - data: List of simplified market data
        - error: Error message if failed
        
    Example:
        markets = get_markets_clob(limit=20)
        if 'error' not in markets:
            for m in markets['data']:
                print(f"{m['question']}: {m['condition_id']}")
    """
    try:
        client = get_clob_client()
        
        # Get simplified markets
        result = client.get_simplified_markets()
        
        if not isinstance(result, dict) or 'data' not in result:
            return {"error": "Invalid response from CLOB API"}
        
        markets = result['data']
        
        # Filter by active status if specified
        if active is not None:
            markets = [m for m in markets if m.get('active') == active]
        
        # Apply pagination
        paginated = markets[offset:offset + limit]
        
        return {
            "data": paginated,
            "total": len(markets),
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        logger.error(f"Error fetching markets from CLOB: {e}")
        return {"error": f"Failed to fetch markets: {str(e)}"}


def get_orderbook(
    token_id: str
) -> Dict[str, Any]:
    """
    Get orderbook for a specific token using CLOB client.
    
    Args:
        token_id: Token ID (e.g., from market data)
        
    Returns:
        dict with:
        - market: Market identifier
        - asset_id: Token ID
        - bids: List of bid orders [price, size]
        - asks: List of ask orders [price, size]
        - error: Error message if failed
        
    Example:
        book = get_orderbook("123456")
        if 'error' not in book:
            print(f"Best bid: {book['bids'][0][0]}")
            print(f"Best ask: {book['asks'][0][0]}")
    """
    try:
        client = get_clob_client()
        orderbook = client.get_order_book(token_id)
        
        return {
            "market": orderbook.market,
            "asset_id": orderbook.asset_id,
            "bids": [[float(bid.price), float(bid.size)] for bid in orderbook.bids],
            "asks": [[float(ask.price), float(ask.size)] for ask in orderbook.asks],
            "timestamp": orderbook.timestamp if hasattr(orderbook, 'timestamp') else None
        }
    
    except Exception as e:
        logger.error(f"Error fetching orderbook for {token_id}: {e}")
        return {"error": f"Failed to fetch orderbook: {str(e)}"}


def get_market_price(
    token_id: str,
    side: str = "MID"
) -> Dict[str, Any]:
    """
    Get current price for a token.
    
    Args:
        token_id: Token ID
        side: Price side - "BUY", "SELL", or "MID" (default)
        
    Returns:
        dict with:
        - price: Current price (0-1)
        - token_id: Token ID
        - side: Price side
        - error: Error message if failed
        
    Example:
        price = get_market_price("123456", side="BUY")
        if 'error' not in price:
            print(f"Buy price: ${price['price']}")
    """
    try:
        client = get_clob_client()
        
        if side.upper() == "MID":
            price = client.get_midpoint(token_id)
        else:
            price = client.get_price(token_id, side=side.upper())
        
        return {
            "price": float(price),
            "token_id": token_id,
            "side": side.upper()
        }
    
    except Exception as e:
        logger.error(f"Error fetching price for {token_id}: {e}")
        return {"error": f"Failed to fetch price: {str(e)}"}


def get_user_orders(
    private_key: str,
    funder: Optional[str] = None,
    signature_type: int = 1
) -> Dict[str, Any]:
    """
    Get user's open orders (requires authentication).
    
    Args:
        private_key: Wallet private key
        funder: Funder address for proxy wallets
        signature_type: 0 for EOA, 1 for email/Magic wallet, 2 for browser proxy
        
    Returns:
        dict with:
        - orders: List of open orders
        - error: Error message if failed
    """
    try:
        client = get_clob_client(
            private_key=private_key,
            funder=funder,
            signature_type=signature_type
        )
        
        orders = client.get_orders(OpenOrderParams())
        
        return {"orders": orders}
    
    except Exception as e:
        logger.error(f"Error fetching user orders: {e}")
        return {"error": f"Failed to fetch orders: {str(e)}"}


def get_user_trades(
    private_key: str,
    funder: Optional[str] = None,
    signature_type: int = 1
) -> Dict[str, Any]:
    """
    Get user's trade history (requires authentication).
    
    Args:
        private_key: Wallet private key
        funder: Funder address for proxy wallets
        signature_type: 0 for EOA, 1 for email/Magic wallet, 2 for browser proxy
        
    Returns:
        dict with:
        - trades: List of trades
        - error: Error message if failed
    """
    try:
        client = get_clob_client(
            private_key=private_key,
            funder=funder,
            signature_type=signature_type
        )
        
        trades = client.get_trades()
        
        return {"trades": trades}
    
    except Exception as e:
        logger.error(f"Error fetching user trades: {e}")
        return {"error": f"Failed to fetch trades: {str(e)}"}
