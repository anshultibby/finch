from .setup import _post


async def recall_stock(query: str, ticker: str = None, session_id: str = None, top_k: int = 5) -> list:
    """
    Retrieve relevant stock knowledge from the Cognee knowledge graph via backend API.

    Args:
        query: Natural language query about stocks.
        ticker: Optional ticker to scope search to a specific stock's dataset.
        session_id: Optional session ID to check session cache first.
        top_k: Number of results to return.

    Returns:
        list of relevant knowledge entries.
    """
    body = {"query": query, "top_k": top_k}
    if ticker:
        body["ticker"] = ticker
    if session_id:
        body["session_id"] = session_id
    result = _post("/memory/recall", body)
    return result.get("results", []) if isinstance(result, dict) else result
