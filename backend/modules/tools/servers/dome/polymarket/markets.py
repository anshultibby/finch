"""
Polymarket Markets - Search and Discovery

Find and explore Polymarket prediction markets.
"""
from .._client import call_dome_api
from ..models import GetMarketsInput, GetMarketsOutput


def get_markets(input: GetMarketsInput) -> GetMarketsOutput:
    """
    Search Polymarket prediction markets.
    
    Args:
        input: GetMarketsInput with search/filter parameters
        
    Returns:
        GetMarketsOutput with markets list and pagination
        
    Example:
        from servers.dome.models import GetMarketsInput
        result = get_markets(GetMarketsInput(tags=['crypto'], limit=5))
        for m in result.markets:
            print(f"{m.title}: ${m.volume_total:,.0f} volume")
    """
    params = input.model_dump(exclude_none=True)
    result = call_dome_api("/polymarket/markets", params)
    return GetMarketsOutput(**result)
