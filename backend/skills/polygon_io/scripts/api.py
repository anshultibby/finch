"""Universal Polygon API caller"""
from ._client import call_polygon_api


def polygon(endpoint: str, params: dict = None):
    """
    Call any Polygon.io API endpoint directly
    
    Args:
        endpoint: API endpoint path (e.g., '/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31')
        params: Optional query parameters
        
    Returns:
        dict: API response
    """
    return call_polygon_api(endpoint, params)
