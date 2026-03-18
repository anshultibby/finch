"""
Kalshi API docs fetcher — pulls the OpenAPI spec and lets you query endpoints/schemas.

Usage:
    from skills.kalshi_trading.scripts.api_docs import lookup, schema

    # Look up an endpoint
    lookup("GET /markets/{ticker}")
    lookup("POST /portfolio/orders")
    lookup("/events")  # defaults to GET

    # Look up a schema (response/request model)
    schema("Market")
    schema("Order")

    # Search endpoints by keyword
    lookup("incentive")   # finds all endpoints matching "incentive"
"""
import json
import urllib.request
from typing import Any, Dict, Optional

OPENAPI_URL = "https://docs.kalshi.com/openapi.yaml"

_spec = None


def _fetch_spec() -> Dict[str, Any]:
    """Fetch and parse the OpenAPI spec. Cached after first call."""
    global _spec
    if _spec is not None:
        return _spec

    try:
        import yaml
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
        import yaml

    with urllib.request.urlopen(OPENAPI_URL, timeout=30) as resp:
        _spec = yaml.safe_load(resp.read())
    return _spec


def _resolve_ref(ref: str, spec: Dict) -> Dict:
    """Resolve a $ref like '#/components/schemas/Market' to the actual schema."""
    parts = ref.lstrip("#/").split("/")
    obj = spec
    for p in parts:
        obj = obj.get(p, {})
    return obj


def _expand_schema(s: Dict, spec: Dict, depth: int = 0, max_depth: int = 2) -> Dict:
    """Recursively expand $ref references in a schema, up to max_depth."""
    if not isinstance(s, dict):
        return s
    if "$ref" in s:
        if depth >= max_depth:
            return {"$ref": s["$ref"], "_note": "not expanded (max depth)"}
        resolved = _resolve_ref(s["$ref"], spec)
        return _expand_schema(resolved, spec, depth + 1, max_depth)
    result = {}
    for k, v in s.items():
        if isinstance(v, dict):
            result[k] = _expand_schema(v, spec, depth, max_depth)
        elif isinstance(v, list):
            result[k] = [_expand_schema(i, spec, depth, max_depth) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result


def lookup(query: str) -> str:
    """
    Look up a Kalshi API endpoint.

    Args:
        query: "GET /markets/{ticker}", "/events", or a keyword like "incentive"

    Returns:
        Formatted string with endpoint details (method, path, description, params, response schema).
    """
    spec = _fetch_spec()
    paths = spec.get("paths", {})

    # Parse query into method + path, or treat as keyword search
    parts = query.strip().split(None, 1)
    if len(parts) == 2 and parts[0].upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        method = parts[0].lower()
        path = parts[1]
        # Direct lookup
        if path in paths and method in paths[path]:
            return _format_endpoint(method, path, paths[path][method], spec)
        return f"Endpoint not found: {method.upper()} {path}"
    elif query.startswith("/"):
        # Path without method — show all methods
        path = query
        if path in paths:
            results = []
            for m in ("get", "post", "put", "delete", "patch"):
                if m in paths[path]:
                    results.append(_format_endpoint(m, path, paths[path][m], spec))
            return "\n---\n".join(results) if results else f"No methods found for {path}"
        return f"Path not found: {path}"
    else:
        # Keyword search
        keyword = query.lower()
        matches = []
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "delete", "patch"):
                    text = f"{path} {details.get('summary', '')} {details.get('description', '')}".lower()
                    if keyword in text:
                        matches.append(f"  {method.upper()} {path} — {details.get('summary', 'No summary')}")
        if matches:
            return f"Endpoints matching '{query}':\n" + "\n".join(matches)
        return f"No endpoints matching '{query}'"


def schema(name: str) -> str:
    """
    Look up a schema/model definition from the Kalshi API spec.

    Args:
        name: Schema name like "Market", "Order", "Event", "Series"

    Returns:
        Formatted string showing all fields, their types, and descriptions.
    """
    spec = _fetch_spec()
    schemas = spec.get("components", {}).get("schemas", {})

    # Try exact match first, then case-insensitive
    s = schemas.get(name)
    if not s:
        for k, v in schemas.items():
            if k.lower() == name.lower():
                s = v
                name = k
                break

    if not s:
        # Search for partial matches
        matches = [k for k in schemas if name.lower() in k.lower()]
        if matches:
            return f"Schema '{name}' not found. Did you mean: {', '.join(matches)}"
        return f"Schema '{name}' not found."

    expanded = _expand_schema(s, spec, max_depth=1)
    return _format_schema(name, expanded)


def _format_endpoint(method: str, path: str, details: Dict, spec: Dict) -> str:
    """Format a single endpoint for display."""
    lines = [f"## {method.upper()} {path}"]
    if details.get("summary"):
        lines.append(f"**{details['summary']}**")
    if details.get("description"):
        lines.append(details["description"].strip())
    lines.append("")

    # Parameters
    params = details.get("parameters", [])
    if params:
        lines.append("### Parameters")
        for p in params:
            req = " (required)" if p.get("required") else ""
            s = p.get("schema", {})
            typ = s.get("type", "string")
            if "enum" in s:
                typ = f"enum: {s['enum']}"
            desc = p.get("description", "")
            default = f" (default: {s['default']})" if "default" in s else ""
            lines.append(f"- **{p['name']}** [{typ}]{req}{default}: {desc}")
        lines.append("")

    # Request body
    rb = details.get("requestBody", {})
    if rb:
        content = rb.get("content", {}).get("application/json", {})
        s = content.get("schema", {})
        if s:
            expanded = _expand_schema(s, spec, max_depth=1)
            lines.append("### Request Body")
            lines.append(_format_schema_brief(expanded))
            lines.append("")

    # Response
    resp_200 = details.get("responses", {}).get("200", details.get("responses", {}).get("201", {}))
    if resp_200:
        content = resp_200.get("content", {}).get("application/json", {})
        s = content.get("schema", {})
        if s:
            expanded = _expand_schema(s, spec, max_depth=2)
            lines.append("### Response (200)")
            lines.append(_format_schema_brief(expanded))

    return "\n".join(lines)


def _format_schema(name: str, s: Dict) -> str:
    """Format a schema definition for display."""
    lines = [f"## {name}"]
    if s.get("description"):
        lines.append(s["description"])
    lines.append("")

    required = set(s.get("required", []))
    props = s.get("properties", {})
    if props:
        lines.append("### Fields")
        for field, info in props.items():
            req = " **(required)**" if field in required else ""
            typ = _type_str(info)
            desc = info.get("description", "")
            dep = " *(deprecated)*" if info.get("deprecated") else ""
            lines.append(f"- **{field}** [{typ}]{req}{dep}: {desc}")

    return "\n".join(lines)


def _format_schema_brief(s: Dict) -> str:
    """Format schema properties briefly."""
    if not isinstance(s, dict):
        return str(s)
    props = s.get("properties", {})
    if not props:
        return json.dumps(s, indent=2, default=str)[:2000]

    required = set(s.get("required", []))
    lines = []
    for field, info in props.items():
        typ = _type_str(info)
        dep = " (deprecated)" if info.get("deprecated") else ""
        req = " (required)" if field in required else ""
        desc = info.get("description", "")[:100]
        lines.append(f"  {field}: {typ}{req}{dep} — {desc}")
    return "\n".join(lines)


def _type_str(info: Dict) -> str:
    """Get a human-readable type string from a schema."""
    if not isinstance(info, dict):
        return "unknown"
    if "enum" in info:
        return f"enum{info['enum']}"
    t = info.get("type", "object")
    if t == "array":
        items = info.get("items", {})
        return f"array[{_type_str(items)}]"
    fmt = info.get("format")
    if fmt:
        return f"{t} ({fmt})"
    return t
