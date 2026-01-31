"""
Polymarket Markets - Search and Discovery

Find and explore Polymarket prediction markets.
"""
from typing import Optional, List, Dict, Any
from .._client import call_dome_api


def get_markets(
    market_slug: Optional[List[str]] = None,
    event_slug: Optional[List[str]] = None,
    condition_id: Optional[List[str]] = None,
    token_id: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    min_volume: Optional[float] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 10,
    pagination_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search Polymarket prediction markets.
    
    Args:
        market_slug: Filter by market slug(s)
        event_slug: Filter by event slug(s) (events group related markets)
        condition_id: Filter by condition ID(s)
        token_id: Filter by token ID(s) (max 100)
        tags: Filter by tags, e.g., ['politics', 'crypto', 'sports']
        search: Search keywords in title/description (URL encoded)
        status: Filter by 'open' or 'closed'
        min_volume: Minimum total trading volume in USD
        start_time: Filter markets from Unix timestamp (seconds, inclusive)
        end_time: Filter markets until Unix timestamp (seconds, inclusive)
        limit: Number of markets to return (1-100, default 10)
        pagination_key: Pagination cursor from previous response
        
    Returns:
        dict with:
        - markets: List of markets with:
            - market_slug: Market identifier
            - event_slug: Event identifier
            - condition_id: Market condition ID
            - title: Market question
            - description: Full description
            - tags: List of tags
            - volume_1_week/month/year/total: Trading volumes
            - status: 'open' or 'closed'
            - start_time/end_time/completed_time/close_time: Timestamps
            - side_a: Dict with 'id' (token_id) and 'label' (e.g., 'Yes')
            - side_b: Dict with 'id' (token_id) and 'label' (e.g., 'No')
            - winning_side: 'side_a' or 'side_b' if resolved
            - image: Market image URL
            - resolution_source: Resolution source URL
        - pagination: Dict with limit, total, has_more, pagination_key
        
    Example:
        # Find crypto markets
        markets = get_markets(tags=['crypto'], limit=5)
        if 'error' not in markets:
            for m in markets['markets']:
                print(f"{m['title']}: ${m['volume_total']:,.0f} volume")
                print(f"  {m['side_a']['label']}: token {m['side_a']['id']}")
        
        # Search for specific keywords
        markets = get_markets(search='bitcoin price', status='open', limit=20)
        
        # Get high-volume markets
        markets = get_markets(min_volume=100000, status='open')
    """
    params = {"limit": min(max(1, limit), 100)}
    
    if market_slug:
        params["market_slug"] = market_slug
    if event_slug:
        params["event_slug"] = event_slug
    if condition_id:
        params["condition_id"] = condition_id
    if token_id:
        params["token_id"] = token_id
    if tags:
        params["tags"] = tags
    if search:
        params["search"] = search
    if status:
        params["status"] = status
    if min_volume is not None:
        params["min_volume"] = min_volume
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if pagination_key:
        params["pagination_key"] = pagination_key
    
    return call_dome_api("/polymarket/markets", params)
