"""
The Odds API docs — query endpoints and schemas from the live Swagger spec.

Usage:
    from skills.odds_api.scripts.api_docs import lookup, schema

    lookup("GET /v4/sports/{sport}/odds")
    lookup("historical")              # keyword search
    lookup("/v4/historical/sports/{sport}/odds")

    schema("OddsResponse")
"""
from skills._shared.api_docs import OpenAPIDocs

_docs = OpenAPIDocs(
    "https://api.swaggerhub.com/apis/the-odds-api/odds-api/4"
)

# Public API
lookup = _docs.lookup
schema = _docs.schema
list_endpoints = _docs.list_endpoints
list_schemas = _docs.list_schemas
