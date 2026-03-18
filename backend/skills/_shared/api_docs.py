"""
Shared OpenAPI docs utility — fetch any OpenAPI spec and query endpoints/schemas.

Usage from any skill:
    from skills._shared.api_docs import OpenAPIDocs

    docs = OpenAPIDocs("https://example.com/openapi.yaml")
    docs.lookup("GET /markets/{ticker}")
    docs.lookup("incentive")  # keyword search
    docs.schema("Market")
"""
import json
import urllib.request
from typing import Any, Dict, Optional


class OpenAPIDocs:
    """
    Fetches an OpenAPI spec (YAML or JSON) and provides lookup/schema helpers.

    Caches the spec after first fetch. Supports:
    - Direct endpoint lookup:  lookup("GET /path")
    - Path lookup (all methods): lookup("/path")
    - Keyword search:          lookup("keyword")
    - Schema lookup:           schema("ModelName")
    """

    def __init__(self, spec_url: str):
        self._spec_url = spec_url
        self._spec: Optional[Dict] = None

    def _fetch_spec(self) -> Dict[str, Any]:
        """Fetch and parse the OpenAPI spec. Cached after first call."""
        if self._spec is not None:
            return self._spec

        with urllib.request.urlopen(self._spec_url, timeout=30) as resp:
            raw = resp.read()

        # Try JSON first, fall back to YAML
        try:
            self._spec = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            try:
                import yaml
            except ImportError:
                import subprocess, sys
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "pyyaml", "-q"]
                )
                import yaml
            self._spec = yaml.safe_load(raw)

        return self._spec

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup(self, query: str) -> str:
        """
        Look up an API endpoint.

        Args:
            query: "GET /path", "/path" (all methods), or a keyword to search.

        Returns:
            Formatted string with endpoint details.
        """
        spec = self._fetch_spec()
        paths = spec.get("paths", {})

        parts = query.strip().split(None, 1)
        if len(parts) == 2 and parts[0].upper() in (
            "GET", "POST", "PUT", "DELETE", "PATCH",
        ):
            method = parts[0].lower()
            path = parts[1]
            if path in paths and method in paths[path]:
                return self._format_endpoint(method, path, paths[path][method], spec)
            return f"Endpoint not found: {method.upper()} {path}"

        if query.startswith("/"):
            path = query
            if path in paths:
                results = []
                for m in ("get", "post", "put", "delete", "patch"):
                    if m in paths[path]:
                        results.append(
                            self._format_endpoint(m, path, paths[path][m], spec)
                        )
                return "\n---\n".join(results) if results else f"No methods for {path}"
            return f"Path not found: {path}"

        # Keyword search
        keyword = query.lower()
        matches = []
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "delete", "patch"):
                    text = f"{path} {details.get('summary', '')} {details.get('description', '')}".lower()
                    if keyword in text:
                        matches.append(
                            f"  {method.upper()} {path} — {details.get('summary', 'No summary')}"
                        )
        if matches:
            return f"Endpoints matching '{query}':\n" + "\n".join(matches)
        return f"No endpoints matching '{query}'"

    def schema(self, name: str) -> str:
        """
        Look up a schema/model definition from the spec.

        Args:
            name: Schema name like "Market", "Event", etc.

        Returns:
            Formatted string showing all fields, types, and descriptions.
        """
        spec = self._fetch_spec()
        schemas = spec.get("components", {}).get("schemas", {})

        # Also check definitions (Swagger 2.0)
        if not schemas:
            schemas = spec.get("definitions", {})

        s = schemas.get(name)
        if not s:
            for k, v in schemas.items():
                if k.lower() == name.lower():
                    s = v
                    name = k
                    break

        if not s:
            matches = [k for k in schemas if name.lower() in k.lower()]
            if matches:
                return f"Schema '{name}' not found. Did you mean: {', '.join(matches)}"
            return f"Schema '{name}' not found."

        expanded = self._expand_schema(s, spec, max_depth=1)
        return self._format_schema(name, expanded)

    def list_endpoints(self) -> str:
        """List all endpoints in the spec."""
        spec = self._fetch_spec()
        paths = spec.get("paths", {})
        lines = []
        for path, methods in sorted(paths.items()):
            for method in ("get", "post", "put", "delete", "patch"):
                if method in methods:
                    summary = methods[method].get("summary", "")
                    lines.append(f"  {method.upper()} {path} — {summary}")
        return "\n".join(lines) if lines else "No endpoints found."

    def list_schemas(self) -> str:
        """List all schema names in the spec."""
        spec = self._fetch_spec()
        schemas = spec.get("components", {}).get("schemas", {})
        if not schemas:
            schemas = spec.get("definitions", {})
        if not schemas:
            return "No schemas found."
        return "\n".join(f"  {k}" for k in sorted(schemas))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_ref(self, ref: str, spec: Dict) -> Dict:
        parts = ref.lstrip("#/").split("/")
        obj = spec
        for p in parts:
            obj = obj.get(p, {})
        return obj

    def _expand_schema(
        self, s: Any, spec: Dict, depth: int = 0, max_depth: int = 2
    ) -> Any:
        if not isinstance(s, dict):
            return s
        if "$ref" in s:
            if depth >= max_depth:
                return {"$ref": s["$ref"], "_note": "not expanded (max depth)"}
            resolved = self._resolve_ref(s["$ref"], spec)
            return self._expand_schema(resolved, spec, depth + 1, max_depth)
        result = {}
        for k, v in s.items():
            if isinstance(v, dict):
                result[k] = self._expand_schema(v, spec, depth, max_depth)
            elif isinstance(v, list):
                result[k] = [
                    self._expand_schema(i, spec, depth, max_depth)
                    if isinstance(i, dict)
                    else i
                    for i in v
                ]
            else:
                result[k] = v
        return result

    def _format_endpoint(
        self, method: str, path: str, details: Dict, spec: Dict
    ) -> str:
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
                s = p.get("schema", p)
                typ = s.get("type", "string")
                if "enum" in s:
                    typ = f"enum: {s['enum']}"
                desc = p.get("description", "")
                default = f" (default: {s['default']})" if "default" in s else ""
                lines.append(
                    f"- **{p['name']}** [{typ}]{req}{default}: {desc}"
                )
            lines.append("")

        # Request body
        rb = details.get("requestBody", {})
        if rb:
            content = rb.get("content", {}).get("application/json", {})
            s = content.get("schema", {})
            if s:
                expanded = self._expand_schema(s, spec, max_depth=1)
                lines.append("### Request Body")
                lines.append(self._format_schema_brief(expanded))
                lines.append("")

        # Response
        resp_200 = details.get("responses", {}).get(
            "200", details.get("responses", {}).get("201", {})
        )
        if resp_200:
            content = resp_200.get("content", {}).get("application/json", {})
            s = content.get("schema", {})
            if not s:
                # Swagger 2.0 style
                s = resp_200.get("schema", {})
            if s:
                expanded = self._expand_schema(s, spec, max_depth=2)
                lines.append("### Response (200)")
                lines.append(self._format_schema_brief(expanded))

        return "\n".join(lines)

    def _format_schema(self, name: str, s: Dict) -> str:
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
                typ = self._type_str(info)
                desc = info.get("description", "")
                dep = " *(deprecated)*" if info.get("deprecated") else ""
                lines.append(f"- **{field}** [{typ}]{req}{dep}: {desc}")

        return "\n".join(lines)

    def _format_schema_brief(self, s: Any) -> str:
        if not isinstance(s, dict):
            return str(s)
        props = s.get("properties", {})
        if not props:
            return json.dumps(s, indent=2, default=str)[:2000]

        required = set(s.get("required", []))
        lines = []
        for field, info in props.items():
            typ = self._type_str(info)
            dep = " (deprecated)" if info.get("deprecated") else ""
            req = " (required)" if field in required else ""
            desc = info.get("description", "")[:100]
            lines.append(f"  {field}: {typ}{req}{dep} — {desc}")
        return "\n".join(lines)

    def _type_str(self, info: Any) -> str:
        if not isinstance(info, dict):
            return "unknown"
        if "enum" in info:
            return f"enum{info['enum']}"
        t = info.get("type", "object")
        if t == "array":
            items = info.get("items", {})
            return f"array[{self._type_str(items)}]"
        fmt = info.get("format")
        if fmt:
            return f"{t} ({fmt})"
        return t
