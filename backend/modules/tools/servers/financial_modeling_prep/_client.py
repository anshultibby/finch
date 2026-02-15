"""FMP API Client"""
import requests
from .._env import get_api_key

# Endpoint prefixes that require v4 API (matched with startswith)
V4_ENDPOINT_PREFIXES = (
    '/insider-roster',
    '/insider-trading',
    '/senate-trading',
    '/house-trading',
    '/institutional-ownership',
    '/institutional-holders',
)


def call_fmp_api(endpoint: str, params: dict = None):
    """Call FMP API endpoint (auto-detects v3 vs v4)"""
    api_key = get_api_key('FMP')
    if not api_key:
        return {"error": "FMP_API_KEY not set"}
    
    # Determine API version based on endpoint
    base_endpoint = endpoint.split('?')[0]  # Remove query params for matching
    version = 'v4' if base_endpoint.startswith(V4_ENDPOINT_PREFIXES) else 'v3'
    
    url = f"https://financialmodelingprep.com/api/{version}{endpoint}"
    
    try:
        response = requests.get(
            url, 
            params={'apikey': api_key.get(), **(params or {})},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Return first item if single-item list
        if isinstance(data, list) and len(data) == 1:
            return data[0]
        
        return data
    
    except Exception as e:
        return {"error": str(e)}


def call_fmp_stable_api(endpoint: str, params: dict = None):
    """Call FMP Stable API endpoint (uses /stable/ prefix)"""
    api_key = get_api_key('FMP')
    if not api_key:
        return {"error": "FMP_API_KEY not set"}
    
    url = f"https://financialmodelingprep.com/stable{endpoint}"
    
    try:
        response = requests.get(
            url, 
            params={'apikey': api_key.get(), **(params or {})},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Return first item if single-item list
        if isinstance(data, list) and len(data) == 1:
            return data[0]
        
        return data
    
    except Exception as e:
        return {"error": str(e)}
