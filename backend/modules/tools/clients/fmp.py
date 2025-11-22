"""
Financial Modeling Prep API - Simplified Universal Client

MAIN METHOD:
    get_fmp_data(endpoint, params, ...) - Universal method for ALL endpoints

USAGE EXAMPLES:
    # Simple fetch
    await fmp_tools.get_fmp_data("quote", {"symbol": "AAPL"})
    
    # With Pydantic parsing
    await fmp_tools.get_fmp_data("quote", {"symbol": "AAPL"}, model_class=Quote, expect_list=False)
    
    # List data with CSV output
    await fmp_tools.get_fmp_data("income-statement", {"symbol": "AAPL", "period": "annual"}, 
                                  model_class=IncomeStatement)
    
    # Market movers (no params)
    await fmp_tools.get_fmp_data("biggest-gainers")

INVALID PARAMS:
    Invalid query parameters are silently ignored by the FMP API.
    The API will only use parameters it recognizes.
"""
import httpx
import pandas as pd
from models.fmp import (
    CompanyProfile, IncomeStatement, BalanceSheet, CashFlowStatement,
    KeyMetrics, FinancialRatio, HistoricalPrice, Quote,
    AnalystRecommendation, FinancialGrowth
)
from config import Config


# ===================================================================================
# ENDPOINT CATALOG - Documentation of available endpoints and their parameters
# ===================================================================================
ENDPOINTS = {
    # Company Info
    "profile": {
        "params": ["symbol"],
        "model": CompanyProfile,
        "list": False,
        "description": "Get comprehensive company profile and information"
    },
    
    # Financial Statements  
    "income-statement": {
        "params": ["symbol", "period", "limit"],
        "model": IncomeStatement,
        "list": True,
        "description": "Get income statement data (period: annual/quarter)"
    },
    "balance-sheet": {
        "params": ["symbol", "period", "limit"],
        "model": BalanceSheet,
        "list": True,
        "description": "Get balance sheet data"
    },
    "cash-flow-statement": {
        "params": ["symbol", "period", "limit"],
        "model": CashFlowStatement,
        "list": True,
        "description": "Get cash flow statement data"
    },
    
    # Key Metrics & Ratios
    "key-metrics": {
        "params": ["symbol", "period", "limit"],
        "model": KeyMetrics,
        "list": True,
        "description": "Get key metrics and valuation ratios"
    },
    "financial-ratios": {
        "params": ["symbol", "period", "limit"],
        "model": FinancialRatio,
        "list": True,
        "description": "Get financial ratios (liquidity, profitability, etc.)"
    },
    "financial-growth": {
        "params": ["symbol", "period", "limit"],
        "model": FinancialGrowth,
        "list": True,
        "description": "Get financial growth metrics"
    },
    
    # Market Data
    "quote": {
        "params": ["symbol"],
        "model": Quote,
        "list": False,
        "description": "Get real-time quote data"
    },
    "historical-price-eod/full": {
        "params": ["symbol", "from", "to", "limit"],
        "data_key": "historical",
        "model": HistoricalPrice,
        "list": True,
        "description": "Get historical end-of-day prices"
    },
    
    # Analyst Data
    "grade": {
        "params": ["symbol", "limit"],
        "model": AnalystRecommendation,
        "list": True,
        "description": "Get analyst recommendations"
    },
    "price-target-consensus": {
        "params": ["symbol"],
        "description": "Get analyst price target consensus"
    },
    "grades": {
        "params": ["symbol", "limit"],
        "description": "Get analyst upgrades and downgrades"
    },
    
    # Search & Screening
    "search-symbol": {
        "params": ["query", "limit"],
        "description": "Search for stock symbols by query"
    },
    "company-screener": {
        "params": ["marketCapMoreThan", "marketCapLowerThan", "priceMoreThan", 
                   "priceLowerThan", "betaMoreThan", "betaLowerThan", "limit"],
        "description": "Screen stocks based on criteria"
    },
    
    # Market Movers
    "biggest-gainers": {
        "params": [],
        "description": "Get biggest stock gainers"
    },
    "biggest-losers": {
        "params": [],
        "description": "Get biggest stock losers"
    },
    "most-actives": {
        "params": [],
        "description": "Get most actively traded stocks"
    },
    "sector-performance-snapshot": {
        "params": [],
        "description": "Get sector performance"
    },
    
    # News
    "news/stock": {
        "params": ["symbols", "limit"],
        "description": "Get stock news for specific symbols"
    },
    "news/stock-latest": {
        "params": ["page", "limit"],
        "description": "Get latest stock news"
    },
    
    # ETF
    "etf/holdings": {
        "params": ["symbol"],
        "description": "Get ETF holdings"
    },
    "etf/info": {
        "params": ["symbol"],
        "description": "Get ETF information"
    },
    "etf/sector-weightings": {
        "params": ["symbol"],
        "description": "Get ETF sector weightings"
    },
    
    # Corporate Events
    "earnings-calendar": {
        "params": ["from", "to"],
        "description": "Get earnings calendar"
    },
    "dividends-calendar": {
        "params": ["from", "to"],
        "description": "Get dividends calendar"
    },
    "splits": {
        "params": ["symbol"],
        "description": "Get stock split history"
    },
    
    # Economic Data
    "treasury-rates": {
        "params": ["from", "to"],
        "description": "Get treasury rates"
    },
    "economic-indicators": {
        "params": ["name", "from", "to"],
        "description": "Get economic indicator data (GDP, unemployment, etc.)"
    },
    
    # Peers & Comparisons
    "stock-peers": {
        "params": ["symbol"],
        "description": "Get stock peer companies"
    },
    
    # SEC Filings
    "sec-filings-search/symbol": {
        "params": ["symbol", "limit", "from", "to"],
        "description": "Search SEC filings by symbol"
    },
    "sec-filings-search/form-type": {
        "params": ["formType", "limit", "from", "to"],
        "description": "Search SEC filings by form type"
    },
    
    # ESG
    "esg-ratings": {
        "params": ["symbol"],
        "description": "Get ESG (Environmental, Social, Governance) score"
    },
    
    # ============ Insider Trading ============
    "senate-latest": {
        "params": ["page", "limit"],
        "description": "Get recent Senate trading disclosures"
    },
    "house-latest": {
        "params": ["page", "limit"],
        "description": "Get recent House trading disclosures"
    },
    "insider-trading/latest": {
        "params": ["page", "limit"],
        "description": "Get recent corporate insider trades (SEC Form 4)"
    },
    "insider-trading-search": {
        "params": ["symbol", "reportingCik", "companyCik", "transactionType", "limit", "page"],
        "description": "Search insider trades with filters"
    },
    "insider-trading-statistics": {
        "params": ["symbol"],
        "description": "Get quarterly insider trading statistics for a stock"
    },
}


class FMPTools:
    """
    Universal FMP API client.
    
    Use get_fmp_data() for ALL endpoints.
    See ENDPOINTS dict for available endpoints and parameters.
    """
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = Config.FMP_API_KEY
        self.api_enabled = bool(self.api_key)
    
    async def _fetch_api_data(self, endpoint, params, data_key=None, stream_handler=None):
        """Low-level method to fetch from API"""
        if not self.api_enabled:
            raise ValueError(
                "Financial data features require a Financial Modeling Prep API key. "
                "Please add FMP_API_KEY to your .env file. "
                "Get your API key from: https://site.financialmodelingprep.com/developer/docs/pricing"
            )
        
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            params["apikey"] = self.api_key
            
            # Build detailed status message with endpoint and key params
            symbol = params.get('symbol', '')
            period = params.get('period', '')
            param_details = []
            if symbol:
                param_details.append(f"symbol={symbol}")
            if period:
                param_details.append(f"period={period}")
            
            param_str = f" ({', '.join(param_details)})" if param_details else ""
            await stream_handler.emit_status("fetching", f"Connecting to FMP API: {endpoint}{param_str}")
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            # Get content length for progress info
            content_length = response.headers.get('content-length', 'unknown')
            if content_length != 'unknown':
                size_kb = int(content_length) / 1024
                await stream_handler.emit_status("processing", f"Receiving {size_kb:.1f}KB of data from FMP API...")
            else:
                await stream_handler.emit_status("processing", f"Receiving data from FMP API...")
            
            data = response.json()
            
            if data_key:
                return data.get(data_key) if isinstance(data, dict) else None
            
            return data
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP error fetching {endpoint}: {str(e)}", flush=True)
            await stream_handler.emit_log("error", f"✗ HTTP error on {endpoint}: {str(e)}")
            raise
        except Exception as e:
            print(f"❌ Error fetching {endpoint}: {str(e)}", flush=True)
            await stream_handler.emit_log("error", f"✗ API error on {endpoint}: {str(e)}")
            raise
    
    async def get_fmp_data(
        self,
        endpoint,
        params=None,
        model_class=None,
        expect_list=None,
        result_key=None,
        log_prefix="📊",
        item_name=None,
        stream_handler=None
    ):
        """
        *** MAIN METHOD - Use this for ALL FMP endpoints ***
        
        Args:
            endpoint: API endpoint (e.g., "quote", "income-statement", "biggest-gainers")
                     See ENDPOINTS dict for full list
            params: Dict of query parameters (invalid params are ignored by API)
            model_class: Optional Pydantic model for parsing (e.g., Quote, IncomeStatement)
            expect_list: Whether to expect list data (auto-detected if not provided)
            result_key: Optional key name for results (e.g., "quote", "earnings")
            log_prefix: Emoji for logging
            item_name: Name for logging (auto-generated if not provided)
            stream_handler: Optional SSE stream handler for status updates
        
        Returns:
            Dict with success, data/data_csv, message, etc.
            - Simple fetch returns: {"success": bool, "data": any, "count": int}
            - With model_class and expect_list=True: {"success": bool, "data_csv": str, "count": int}
            - With model_class and expect_list=False: {"success": bool, "<item_name>": dict}
            
        Examples:
            # Simple fetch (no parsing)
            await get_fmp_data("quote", {"symbol": "AAPL"})
            
            # With Pydantic parsing to CSV
            await get_fmp_data("income-statement", {"symbol": "AAPL", "period": "annual"}, 
                               model_class=IncomeStatement)
            
            # Single item with parsing
            await get_fmp_data("quote", {"symbol": "AAPL"}, model_class=Quote, expect_list=False)
            
            # Market movers (no params)
            await get_fmp_data("biggest-gainers")
        """
        params = params or {}
        
        # Auto-detect settings from ENDPOINTS catalog
        endpoint_info = ENDPOINTS.get(endpoint, {})
        if expect_list is None:
            expect_list = endpoint_info.get("list", True)
        data_key = endpoint_info.get("data_key")
        if model_class is None:
            model_class = endpoint_info.get("model")
        
        # Use Pydantic parsing if model_class provided
        if model_class:
            return await self._fetch_and_parse(
                endpoint, params, model_class, data_key=data_key,
                log_prefix=log_prefix, item_name=item_name or endpoint,
                expect_list=expect_list, stream_handler=stream_handler
            )
        
        # Otherwise simple fetch
        try:
            data = await self._fetch_api_data(endpoint, params, data_key, stream_handler=stream_handler)
            result = {"success": True}
            
            if result_key:
                result[result_key] = data
            else:
                result["data"] = data
                
            if isinstance(data, list):
                result["count"] = len(data)
            
            # Add symbol if present
            if "symbol" in params:
                result["symbol"] = params["symbol"]
            
            return result
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def _fetch_and_parse(
        self,
        endpoint,
        params,
        model_class,
        data_key=None,
        log_prefix="📊",
        item_name="items",
        expect_list=True,
        stream_handler=None
    ):
        """Parse data using Pydantic models"""
        symbol = params.get("symbol", "N/A")
        period = params.get("period", "")
        limit = params.get("limit", "all available")
        
        try:
            period_str = f"{period} " if period else ""
            limit_str = f" (limit: {limit})" if limit != "all available" else ""
            print(f"{log_prefix} Fetching {period_str}{item_name} for {symbol}...", flush=True)
            
            await stream_handler.emit_status("fetching", f"Requesting {period_str}{item_name} for {symbol} from FMP API{limit_str}...")
            
            data = await self._fetch_api_data(endpoint, params, data_key, stream_handler=stream_handler)
            
            if not data:
                await stream_handler.emit_log("warning", f"⚠ No {item_name} data returned for {symbol} from FMP API")
                return {
                    "success": False,
                    "message": f"No {item_name} found for {symbol}"
                }
            
            # Normalize data to list for processing
            data_list = data if isinstance(data, list) else [data]
            total_items = len(data_list)
            
            await stream_handler.emit_status("processing", f"Parsing {total_items} {item_name} records for {symbol}...")
            
            # Parse using Pydantic models
            parsed_items = []
            failed_items = 0
            for idx, item_data in enumerate(data_list, 1):
                try:
                    item = model_class(**item_data)
                    parsed_items.append(item)
                    
                    # Emit progress for large datasets
                    if total_items > 20 and idx % 10 == 0:
                        progress = (idx / total_items) * 100
                        await stream_handler.emit_progress(
                            progress, 
                            f"Parsed {idx}/{total_items} {item_name} records for {symbol}"
                        )
                except Exception as e:
                    print(f"⚠️ Error parsing {item_name} record {idx}: {e}", flush=True)
                    failed_items += 1
                    continue
            
            if failed_items > 0:
                await stream_handler.emit_log("warning", f"⚠ Failed to parse {failed_items} of {total_items} records for {symbol}")
            
            if not parsed_items:
                await stream_handler.emit_log("error", f"✗ Could not parse any {item_name} records for {symbol}")
                return {
                    "success": False,
                    "message": f"Could not parse {item_name} for {symbol}"
                }
            
            # Handle single vs list returns
            if expect_list:
                await stream_handler.emit_status("processing", f"Converting {len(parsed_items)} {item_name} records to CSV format for {symbol}...")
                
                # Return as CSV for list data
                if hasattr(model_class, 'list_to_df'):
                    df = model_class.list_to_df(parsed_items)
                    data_csv = df.to_csv(index=False)
                    csv_size_kb = len(data_csv) / 1024
                else:
                    # Fallback: convert to dict list
                    df = pd.DataFrame([item.model_dump() for item in parsed_items])
                    data_csv = df.to_csv(index=False)
                    csv_size_kb = len(data_csv) / 1024
                
                print(f"✅ Found {len(parsed_items)} {item_name} for {symbol}", flush=True)
                
                await stream_handler.emit_log("info", f"✓ Successfully retrieved {len(parsed_items)} {period_str}{item_name} records for {symbol} ({csv_size_kb:.1f}KB CSV)")
                
                result = {
                    "success": True,
                    "symbol": symbol,
                    "data_csv": data_csv,
                    "count": len(parsed_items),
                    "message": f"Found {len(parsed_items)} {period_str}{item_name} for {symbol}. Data is in CSV format."
                }
                
                if period:
                    result["period"] = period
                
                return result
            else:
                # Return single item as dict
                item = parsed_items[0]
                print(f"✅ Found {item_name} for {symbol}", flush=True)
                
                await stream_handler.emit_log("info", f"✓ Successfully retrieved {item_name} for {symbol}")
                
                return {
                    "success": True,
                    "symbol": symbol,
                    item_name.replace(" ", "_"): item.model_dump(),
                    "message": f"Found {item_name} for {symbol}"
                }
            
        except Exception as e:
            print(f"❌ Error fetching {item_name}: {str(e)}", flush=True)
            await stream_handler.emit_log("error", f"✗ Failed to fetch {item_name} for {symbol}: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to fetch {item_name}: {str(e)}"
            }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global tools instance
fmp_tools = FMPTools()

