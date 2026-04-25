from .setup import _post


async def remember_stock(ticker: str, content: str, session_id: str = None) -> dict:
    """
    Store stock-related knowledge into the Cognee knowledge graph via backend API.

    Args:
        ticker: Stock symbol (e.g. "AAPL").
        content: Text content — news, analysis, earnings data, etc.
        session_id: Optional chat/session ID for session-scoped storage.

    Returns:
        dict with status and details.
    """
    body = {"ticker": ticker, "content": content}
    if session_id:
        body["session_id"] = session_id
    return _post("/memory/remember", body)
