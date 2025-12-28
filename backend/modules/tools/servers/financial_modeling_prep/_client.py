"""FMP API Client"""
import requests
from .._env import get_api_key


def call_fmp_api(endpoint: str, params: dict = None):
    """Call FMP API endpoint"""
    api_key = get_api_key('FMP')
    if not api_key:
        return {"error": "FMP_API_KEY not set"}
    
    url = f"https://financialmodelingprep.com/api/v3{endpoint}"
    
    try:
        response = requests.get(
            url, 
            params={'apikey': api_key, **(params or {})},
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
