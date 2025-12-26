"""Polygon.io API Client"""
import os
from datetime import datetime

# Import polygon.io SDK (external package, not local directory)
from polygon import RESTClient as PolygonRESTClient


_client = None

def get_polygon_client():
    """Get or create Polygon client singleton"""
    global _client
    if _client is None:
        api_key = os.getenv('POLYGON_API_KEY', '')
        if not api_key:
            raise ValueError("POLYGON_API_KEY not set")
        _client = PolygonRESTClient(api_key=api_key)
    return _client


def polygon_request(func):
    """Decorator to handle Polygon API errors uniformly"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {"error": str(e)}
    return wrapper


def format_bars(aggs):
    """Convert Polygon bars to clean format"""
    return [{
        'timestamp': agg.timestamp,
        'date': datetime.fromtimestamp(agg.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S'),
        'open': agg.open,
        'high': agg.high,
        'low': agg.low,
        'close': agg.close,
        'volume': agg.volume
    } for agg in aggs]
