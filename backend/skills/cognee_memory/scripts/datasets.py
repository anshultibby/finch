from .setup import _get


async def list_datasets() -> list:
    """
    List all stock knowledge datasets that have been stored.

    Returns:
        list of dataset names.
    """
    result = _get("/memory/datasets")
    return result.get("datasets", []) if isinstance(result, dict) else []
