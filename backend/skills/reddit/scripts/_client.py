"""
Reddit Sentiment API Client - Internal implementation

Uses ApeWisdom API to get Reddit mentions and sentiment.
"""
import requests

BASE_URL = "https://apewisdom.io/api/v1.0"


def call_apewisdom_api(endpoint: str, params: dict = None):
    """
    Internal helper to call ApeWisdom API
    
    Args:
        endpoint: API endpoint
        params: Query parameters
        
    Returns:
        API response data or error dict
    """
    url = f"{BASE_URL}{endpoint}"
    
    try:
        response = requests.get(url, params=params or {}, timeout=30)
        response.raise_for_status()
        return response.json()
    
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

