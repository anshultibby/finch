"""
Financial Code Patterns (Knowledge Base)

Reusable code patterns for common financial analysis tasks.
Not "strategies" - just useful code snippets.
"""
from typing import Dict, List, Optional

# Best practices for financial code
BEST_PRACTICES = {
    "data_validation": """
# Always validate data exists and has required fields
data = input_data.get('income-statement', [])
if not data or len(data) == 0:
    return {"error": "No data available"}

# Check required fields exist
value = data[0].get('revenue')
if value is None:
    return {"error": "Missing required field"}
""",
    
    "safe_math": """
# Avoid division by zero
denominator = previous_value if previous_value != 0 else 1
growth_rate = (current_value - previous_value) / denominator

# Handle None values
value = data.get('field', 0) or 0  # Treat None as 0
""",
    
    "multi_period": """
# Calculate trend over multiple periods
periods = data.get('income-statement', [])
if len(periods) < 3:
    return {"error": "Need at least 3 periods"}

# Calculate growth for each period
growth_rates = []
for i in range(len(periods) - 1):
    curr = periods[i].get('revenue', 0)
    prev = periods[i + 1].get('revenue', 1)
    growth = ((curr - prev) / prev) * 100
    growth_rates.append(growth)

avg_growth = sum(growth_rates) / len(growth_rates)
"""
}


# Common financial calculations
PATTERNS = {
    "revenue_growth": {
        "description": "Calculate revenue growth rate",
        "data_needed": ["income-statement"],
        "code": """
def calculate_revenue_growth(data):
    income_stmt = data.get('income-statement', [])
    if len(income_stmt) < 2:
        return {"error": "Need at least 2 periods"}
    
    current = income_stmt[0].get('revenue', 0)
    previous = income_stmt[1].get('revenue', 1)
    growth_pct = ((current - previous) / previous) * 100
    
    return {"growth_pct": growth_pct}
"""
    },
    
    "valuation_ratios": {
        "description": "Calculate P/E, P/B ratios",
        "data_needed": ["key-metrics", "quote"],
        "code": """
def calculate_valuation(data):
    metrics = data.get('key-metrics', [{}])[0]
    pe = metrics.get('peRatio')
    pb = metrics.get('pbRatio')
    
    return {
        "pe_ratio": pe,
        "pb_ratio": pb,
        "undervalued": pe and pe < 15
    }
"""
    },
    
    "profitability": {
        "description": "Analyze profitability metrics",
        "data_needed": ["financial-ratios"],
        "code": """
def analyze_profitability(data):
    ratios = data.get('financial-ratios', [{}])[0]
    roe = ratios.get('returnOnEquity', 0) * 100
    roa = ratios.get('returnOnAssets', 0) * 100
    
    return {
        "roe_pct": roe,
        "roa_pct": roa,
        "highly_profitable": roe > 15
    }
"""
    }
}


def suggest_data_sources(description: str) -> List[str]:
    """Suggest FMP endpoints based on task description"""
    desc_lower = description.lower()
    sources = set()
    
    keywords = {
        "income-statement": ["revenue", "earnings", "profit", "income", "sales"],
        "balance-sheet": ["assets", "liabilities", "debt", "equity", "cash"],
        "key-metrics": ["p/e", "valuation", "market cap", "eps"],
        "financial-ratios": ["roe", "roa", "margin", "ratio"],
        "cash-flow": ["cash flow", "fcf", "operating cash"],
    }
    
    for endpoint, keywords_list in keywords.items():
        if any(kw in desc_lower for kw in keywords_list):
            sources.add(endpoint)
    
    return list(sources) if sources else ["key-metrics"]


def get_error_fix(error_msg: str) -> Optional[str]:
    """Get suggested fix for common errors"""
    fixes = {
        "KeyError": "Use .get() method: data.get('key', default_value)",
        "ZeroDivisionError": "Check denominator: if denom != 0 else 1",
        "IndexError": "Check length: if len(list) > index",
        "TypeError": "Validate types: if value is not None and isinstance(value, (int, float))",
    }
    
    for error_type, fix in fixes.items():
        if error_type in error_msg:
            return fix
    return None

