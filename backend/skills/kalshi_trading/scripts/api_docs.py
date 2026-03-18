"""
Kalshi API docs — query endpoints and schemas from the live OpenAPI spec.

Usage:
    from skills.kalshi_trading.scripts.api_docs import lookup, schema

    lookup("GET /markets/{ticker}")
    lookup("POST /portfolio/orders")
    lookup("/events")              # all methods for a path
    lookup("incentive")            # keyword search

    schema("Market")
    schema("Order")
"""
from skills._shared.api_docs import OpenAPIDocs

_docs = OpenAPIDocs("https://docs.kalshi.com/openapi.yaml")

# Public API — same interface as before
lookup = _docs.lookup
schema = _docs.schema
list_endpoints = _docs.list_endpoints
list_schemas = _docs.list_schemas
