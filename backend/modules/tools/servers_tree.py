"""
Generate servers directory tree and capability descriptions for LLM context.

Used in both:
1. Tool description (so LLM knows what APIs are available)
2. Code execution (so LLM sees the actual mounted filesystem)
"""
from pathlib import Path
from typing import Optional


def get_servers_dir() -> Path:
    """Get the path to the servers directory."""
    return Path(__file__).parent / "servers"


def generate_servers_tree(base_dir: Optional[Path] = None) -> str:
    """
    Generate a tree representation of the servers directory.
    
    Args:
        base_dir: Base directory containing servers/. If None, uses the default location.
        
    Returns:
        String representation of the file tree with import paths.
    """
    if base_dir is None:
        servers_dir = get_servers_dir()
    else:
        servers_dir = base_dir / "servers"
    
    if not servers_dir.exists():
        return "servers/ directory not found"
    
    lines = ["servers/"]
    
    # Get all server directories (skip __pycache__, hidden files)
    server_dirs = sorted([
        d for d in servers_dir.iterdir() 
        if d.is_dir() and not d.name.startswith('_') and not d.name.startswith('.')
    ])
    
    for i, server_dir in enumerate(server_dirs):
        is_last_server = (i == len(server_dirs) - 1)
        prefix = "└── " if is_last_server else "├── "
        lines.append(f"{prefix}{server_dir.name}/")
        
        # Build tree for this server
        _add_directory_contents(
            server_dir, 
            lines, 
            "    " if is_last_server else "│   ",
            server_dir.name
        )
    
    return "\n".join(lines)


def _add_directory_contents(
    directory: Path, 
    lines: list, 
    prefix: str,
    import_prefix: str
):
    """Recursively add directory contents to the tree."""
    # Get all items, filter out __pycache__, hidden, and internal files
    items = sorted([
        item for item in directory.iterdir()
        if not item.name.startswith('_') 
        and not item.name.startswith('.')
        and item.name != '__pycache__'
    ])
    
    # Separate directories and Python files
    dirs = [item for item in items if item.is_dir()]
    py_files = [item for item in items if item.is_file() and item.suffix == '.py']
    
    all_items = dirs + py_files
    
    for i, item in enumerate(all_items):
        is_last = (i == len(all_items) - 1)
        connector = "└── " if is_last else "├── "
        
        if item.is_dir():
            lines.append(f"{prefix}{connector}{item.name}/")
            new_prefix = prefix + ("    " if is_last else "│   ")
            new_import = f"{import_prefix}.{item.name}"
            _add_directory_contents(item, lines, new_prefix, new_import)
        else:
            # Python file - show the import path
            module_name = item.stem
            import_path = f"servers.{import_prefix}.{module_name}"
            lines.append(f"{prefix}{connector}{item.name:<30} # from {import_path} import ...")


def _load_server_docstring(server_name: str, servers_dir: Optional[Path] = None) -> str:
    """Load the docstring from a server's __init__.py by parsing the file."""
    if servers_dir is None:
        servers_dir = get_servers_dir()
    
    init_file = servers_dir / server_name / "__init__.py"
    if not init_file.exists():
        return ""
    
    try:
        import ast
        content = init_file.read_text()
        tree = ast.parse(content)
        docstring = ast.get_docstring(tree)
        return docstring.strip() if docstring else ""
    except Exception:
        return ""


def generate_servers_description() -> str:
    """
    Generate the full servers description for tool context.
    
    Loads capabilities from each server's __init__.py docstring for
    a clean, high-level overview without code examples.
    """
    servers_dir = get_servers_dir()
    
    # Get all server directories
    server_dirs = sorted([
        d.name for d in servers_dir.iterdir() 
        if d.is_dir() and not d.name.startswith('_') and not d.name.startswith('.')
    ])
    
    # Build server descriptions from docstrings
    server_docs = []
    for server_name in server_dirs:
        docstring = _load_server_docstring(server_name)
        if docstring:
            server_docs.append(f"### servers.{server_name}\n{docstring}")
    
    servers_section = "\n\n".join(server_docs)
    
    description = f"""
**API SERVERS - Available Python Modules**

Import APIs from the `servers/` directory. All functions return dicts - always check for 'error' key.

{servers_section}

---

**CRITICAL USAGE RULES:**

1. **Always check for errors:**
   ```python
   result = some_api_function(...)
   if 'error' in result:
       print(f"Error: {{result['error']}}")
   else:
       # Safe to use result
   ```

2. **Polygon.io uses `symbol=` parameter** (not `ticker=`):
   ```python
   get_historical_prices(symbol='AAPL', from_date='2024-01-01', to_date='2024-12-31')
   ```

3. **FMP quote returns a LIST** - use `[0]` for single stock:
   ```python
   quotes = get_quote_snapshot('AAPL')
   quote = quotes[0]
   ```

4. **Price data is in 'bars' key** with timestamps in milliseconds:
   ```python
   df = pd.DataFrame(response['bars'])
   df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
   ```

5. **Explore the servers/ filesystem** to discover function signatures and parameters.
   Each module has docstrings with detailed usage instructions.
"""
    return description


if __name__ == "__main__":
    # Test the tree generation
    print(generate_servers_tree())
    print("\n" + "="*60 + "\n")
    print(generate_servers_description())

