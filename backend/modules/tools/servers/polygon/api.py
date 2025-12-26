"""Universal Polygon API caller"""
from ._client import get_polygon_client

def polygon():
    """Get Polygon REST client for direct API access"""
    return get_polygon_client()

