"""Polygon.io API Client"""
import requests
from datetime import datetime
from .._env import get_api_key


def call_polygon_api(endpoint: str, params: dict = None):
    """Call Polygon.io API endpoint"""
    api_key = get_api_key('POLYGON')
    if not api_key:
        return {"error": "POLYGON_API_KEY not set"}
    
    url = f"https://api.polygon.io{endpoint}"
    
    try:
        response = requests.get(
            url,
            params={'apiKey': api_key.get(), **(params or {})},
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        if response.status_code == 403:
            return {"error": "API access denied - check your Polygon subscription tier"}
        return {"error": f"HTTP {response.status_code}: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


def format_bars(results: list):
    """Convert Polygon bar results to clean format"""
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
        'trades': bar.get('n')
    } for bar in results]
