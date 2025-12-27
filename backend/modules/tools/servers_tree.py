"""
Generate servers directory tree for LLM context.

Used in both:
1. Tool description (so LLM knows what APIs are available)
2. Code execution (so LLM sees the actual mounted filesystem)
"""
import os
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


def generate_servers_description() -> str:
    """
    Generate the full servers description for tool context.
    
    Returns a formatted string with:
    - The file tree
    - Usage examples
    - Important rules
    """
    tree = generate_servers_tree()
    
    return f"""
**🔌 API SERVERS - Available APIs**

The following APIs are available as importable Python modules:

```
{tree}
```

**Usage Examples:**

```python
# Historical prices (Polygon.io)
from servers.polygon_io.market.historical_prices import get_historical_prices
prices = get_historical_prices('AAPL', '2024-01-01', '2024-12-31', timespan='day')

# Company profile (FMP)
from servers.financial_modeling_prep.company.profile import get_profile
profile = get_profile('AAPL')

# Financial statements (FMP)
from servers.financial_modeling_prep.financials.income_statement import get_income_statement
income = get_income_statement('AAPL', period='annual', limit=5)

# Current quote (FMP)
from servers.financial_modeling_prep.market.quote import get_quote
quote = get_quote('AAPL')

# TradingView chart widget
from servers.tradingview.charts.embed import get_embed_widget
widget_html = get_embed_widget('AAPL', interval='D', theme='dark')
```

**Important:**
- Use `polygon_io` for historical OHLCV price data
- Use `financial_modeling_prep` for fundamentals, financials, quotes
- Use `tradingview` for interactive chart widgets
"""


if __name__ == "__main__":
    # Test the tree generation
    print(generate_servers_tree())
    print("\n" + "="*60 + "\n")
    print(generate_servers_description())

