"""Get last trade and current quote"""
from .._client import get_polygon_client, polygon_request


@polygon_request
def get_last_trade(symbol: str):
    """
    Get last trade
    
    Args:
        symbol: Stock ticker
        
    Returns:
        dict: price, size, exchange, timestamp
    """
    client = get_polygon_client()
    trade = client.get_last_trade(symbol)
    return {
        'price': trade.price,
        'size': trade.size,
        'exchange': trade.exchange,
        'timestamp': trade.sip_timestamp
    }


@polygon_request
def get_last_quote(symbol: str):
    """
    Get last quote (bid/ask)
    
    Args:
        symbol: Stock ticker
        
    Returns:
        dict: bid_price, bid_size, ask_price, ask_size, timestamp
    """
    client = get_polygon_client()
    quote = client.get_last_quote(symbol)
    return {
        'bid_price': quote.bid_price,
        'bid_size': quote.bid_size,
        'ask_price': quote.ask_price,
        'ask_size': quote.ask_size,
        'timestamp': quote.sip_timestamp
    }
