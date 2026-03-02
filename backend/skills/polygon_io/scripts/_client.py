"""Polygon.io API Client — routes through the Finch sandbox proxy."""
from datetime import datetime
from .._env import call_proxy


def call_polygon_api(endpoint: str, params: dict = None):
    """Call Polygon.io API endpoint via proxy."""
    url = f"https://api.polygon.io{endpoint}"
    try:
        return call_proxy("polygon", url=url, params=params or {})
    except RuntimeError as e:
        if "403" in str(e):
            return {"error": "API access denied - check your Polygon subscription tier"}
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def format_bars(results: list):
    """Convert Polygon bar results to clean format."""
    if not results:
        return []
    return [{
        'timestamp': bar.get('t'),
        'date': datetime.fromtimestamp(bar.get('t', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S'),
        'open': bar.get('o'),
        'high': bar.get('h'),
        'low': bar.get('l'),
        'close': bar.get('c'),
        'volume': bar.get('v'),
        'vwap': bar.get('vw'),
        'trades': bar.get('n'),
    } for bar in results]
