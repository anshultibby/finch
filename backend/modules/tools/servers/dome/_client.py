"""
Dome API client with rate limiting

Handles API key management and rate limiting (1 req/sec for free tier).
"""
import time
import httpx
from typing import Optional, Dict, Any
from .._env import get_api_key


class RateLimiter:
    """Simple rate limiter for Dome API (1 req/sec)"""
    
    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
    
    def wait(self):
        """Wait until we can make another request"""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()


# Global rate limiter instance
_rate_limiter = RateLimiter(requests_per_second=1.0)


def call_dome_api(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Call Dome API with rate limiting and error handling.
    
    Args:
        endpoint: API endpoint path (e.g., '/polymarket/markets')
        params: Optional query parameters
        
    Returns:
        dict with API response or {'error': 'message'} on failure
    """
    api_key = get_api_key('DOME')
    if not api_key:
        return {"error": "DOME_API_KEY not set"}
    
    # Wait for rate limit
    _rate_limiter.wait()
    
    url = f"https://api.domeapi.io/v1{endpoint}"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                url,
                headers={'x-api-key': api_key.get()},
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
