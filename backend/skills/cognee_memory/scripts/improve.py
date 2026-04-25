from .setup import _post


async def improve_memory(ticker: str = None, session_ids: list = None) -> dict:
    """
    Bridge session memory into the permanent knowledge graph.

    Args:
        ticker: Optional ticker to scope improvement to a specific dataset.
        session_ids: List of session/chat IDs whose memory to consolidate.

    Returns:
        dict with status.
    """
    body = {}
    if ticker:
        body["ticker"] = ticker
    if session_ids:
        body["session_ids"] = session_ids
    return _post("/memory/improve", body)
