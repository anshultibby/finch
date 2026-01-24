"""
Polymarket Markets - Search and Discovery

Find and explore Polymarket prediction markets.
"""
from typing import Optional, List, Dict, Any
from .._client import call_dome_api


def get_markets(
    market_slug: Optional[List[str]] = None,
    condition_id: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    limit: int = 10,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Search Polymarket prediction markets.
    
    Args:
        market_slug: Filter by market slug(s), e.g., ['bitcoin-up-or-down-july-25-8pm-et']
        condition_id: Filter by condition ID(s)
        tags: Filter by tags, e.g., ['politics', 'crypto', 'sports']
        limit: Number of markets to return (1-100, default 10)
        offset: Number of markets to skip for pagination (default 0)
        
    Returns:
        dict with:
        - markets: List of markets with:
            - market_slug: Market identifier
            - condition_id: Market condition ID
            - title: Market question
            - description: Full description
            - outcomes: List of outcomes (Yes/No) with token_ids
            - volume: Trading volume ($)
            - liquidity: Available liquidity ($)
            - tags: Market tags
            - status: ACTIVE, CLOSED, etc.
        - pagination: Pagination info (limit, offset, total, has_more)
        
    Example:
        # Find crypto markets
        markets = get_markets(tags=['crypto'], limit=5)
        if 'error' not in markets:
            for m in markets['markets']:
                print(f"{m['title']}: ${m['volume']:,.0f} volume")
    """
    params = {
        "limit": min(max(1, limit), 100),
        "offset": max(0, offset)
    }
    
    if market_slug:
        params["market_slug"] = market_slug
    if condition_id:
        params["condition_id"] = condition_id
    if tags:
        params["tags"] = tags
    
    return call_dome_api("/polymarket/markets", params)
