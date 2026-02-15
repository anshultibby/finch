"""
Polymarket CLOB Client - Direct API access using official py-clob-client

This provides direct access to Polymarket's Central Limit Order Book (CLOB)
without requiring Dome API, which has been experiencing 403 errors.

For read-only operations, no authentication is needed.
For trading operations, you'll need a private key and optional funder address.

TODO: Add Pydantic models for all return types (GetMarketsOutput, GetOrderbookOutput, etc.)
"""
from typing import Optional, List
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
) -> dict:
    """
    Get markets using CLOB client (direct API, no Dome required).
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
) -> dict:
    """
    Get orderbook for a specific token using CLOB client.
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
) -> dict:
    """
    Get current price for a token.
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
) -> dict:
    """
    Get user's open orders (requires authentication).
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
) -> dict:
    """
    Get user's trade history (requires authentication).
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
