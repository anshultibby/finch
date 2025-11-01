"""
Financial Modeling Prep API tools for comprehensive financial data
Includes company financials, key metrics, ratios, market data, and more
"""
import httpx
import pandas as pd
from io import StringIO
from typing import Dict, Any, Optional, List, Type, TypeVar, Callable
from datetime import datetime, timedelta
from pydantic import BaseModel
from models.fmp import (
    CompanyProfile, IncomeStatement, BalanceSheet, CashFlowStatement,
    KeyMetrics, FinancialRatio, HistoricalPrice, Quote,
    AnalystRecommendation, FinancialGrowth
)
from config import Config

T = TypeVar('T', bound=BaseModel)


class FMPTools:
    """
    Comprehensive tools for fetching financial data from Financial Modeling Prep API
    
    Provides access to:
    - Company profiles and information
    - Financial statements (income statement, balance sheet, cash flow)
    - Key metrics and financial ratios
    - Historical price data
    - Real-time quotes
    - Analyst recommendations
    - Financial growth metrics
    
    Uses DRY principles with generic methods for API calls and data parsing.
    """
    
    # FMP has migrated to /stable/ endpoints (legacy v3/v4 deprecated as of Aug 2025)
    BASE_URL = "https://financialmodelingprep.com/stable"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = Config.FMP_API_KEY
        self.api_enabled = bool(self.api_key)
    
    def _check_api_key(self) -> Optional[dict]:
        """Check if API key is configured"""
        if not self.api_enabled:
            return {
                "success": False,
                "message": "Financial data features require a Financial Modeling Prep API key. Please add FMP_API_KEY to your .env file. Get your API key from: https://site.financialmodelingprep.com/developer/docs/pricing"
            }
        return None
    
    async def _fetch_api_data(
        self,
        endpoint: str,
        params: Dict[str, Any],
        data_key: Optional[str] = None
    ) -> Optional[Any]:
        """
        Generic method to fetch data from FMP API
        
        Args:
            endpoint: API endpoint path
            params: Query parameters (will automatically add apikey)
            data_key: Optional key to extract from response (e.g., 'historical')
            
        Returns:
            API response data or None on error
        """
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            params["apikey"] = self.api_key
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data_key:
                return data.get(data_key) if isinstance(data, dict) else None
            
            return data
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP error fetching {endpoint}: {str(e)}", flush=True)
            raise
        except Exception as e:
            print(f"❌ Error fetching {endpoint}: {str(e)}", flush=True)
            raise
    
    async def _fetch_and_parse_list(
        self,
        endpoint: str,
        params: Dict[str, Any],
        model_class: Type[T],
        data_key: Optional[str] = None,
        log_prefix: str = "📊",
        item_name: str = "items"
    ) -> Dict[str, Any]:
        """
        Generic method to fetch and parse list data with Pydantic models
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            model_class: Pydantic model class for parsing
            data_key: Optional key to extract from response
            log_prefix: Emoji prefix for logging
            item_name: Name of items for logging
            
        Returns:
            Dictionary with parsed data in CSV format
        """
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        symbol = params.get("symbol", "N/A")
        period = params.get("period", "")
        
        try:
            period_str = f"{period} " if period else ""
            print(f"{log_prefix} Fetching {period_str}{item_name} for {symbol}...", flush=True)
            
            data = await self._fetch_api_data(endpoint, params, data_key)
            
            if not data:
                return {
                    "success": False,
                    "message": f"No {item_name} found for {symbol}"
                }
            
            # Parse using Pydantic models
            parsed_items = []
            for item_data in data:
                try:
                    item = model_class(**item_data)
                    parsed_items.append(item)
                except Exception as e:
                    print(f"⚠️ Error parsing {item_name}: {e}", flush=True)
                    continue
            
            if not parsed_items:
                return {
                    "success": False,
                    "message": f"Could not parse {item_name} for {symbol}"
                }
            
            # Convert to DataFrame if model has list_to_df method
            if hasattr(model_class, 'list_to_df'):
                df = model_class.list_to_df(parsed_items)
                data_csv = df.to_csv(index=False)
            else:
                # Fallback: convert to dict list
                data_csv = pd.DataFrame([item.model_dump() for item in parsed_items]).to_csv(index=False)
            
            print(f"✅ Found {len(parsed_items)} {item_name} for {symbol}", flush=True)
            
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
            
        except Exception as e:
            print(f"❌ Error fetching {item_name}: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Failed to fetch {item_name}: {str(e)}"
            }
    
    async def _fetch_and_parse_single(
        self,
        endpoint: str,
        params: Dict[str, Any],
        model_class: Type[T],
        log_prefix: str = "🏢",
        item_name: str = "data"
    ) -> Dict[str, Any]:
        """
        Generic method to fetch and parse single item data with Pydantic model
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            model_class: Pydantic model class for parsing
            log_prefix: Emoji prefix for logging
            item_name: Name of item for logging
            
        Returns:
            Dictionary with parsed data
        """
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        symbol = params.get("symbol", "N/A")
        
        try:
            print(f"{log_prefix} Fetching {item_name} for {symbol}...", flush=True)
            
            data = await self._fetch_api_data(endpoint, params)
            
            if not data:
                return {
                    "success": False,
                    "message": f"No {item_name} found for {symbol}"
                }
            
            # Parse using Pydantic model
            item_data = data[0] if isinstance(data, list) else data
            item = model_class(**item_data)
            
            print(f"✅ Found {item_name} for {symbol}", flush=True)
            
            return {
                "success": True,
                "symbol": symbol,
                item_name.replace(" ", "_"): item.model_dump(),
                "message": f"Found {item_name} for {symbol}"
            }
            
        except Exception as e:
            print(f"❌ Error fetching {item_name}: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Failed to fetch {item_name}: {str(e)}"
            }
    
    # ============================================================================
    # COMPANY PROFILE & INFO
    # ============================================================================
    
    async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive company profile and information"""
        return await self._fetch_and_parse_single(
            endpoint="company/profile",
            params={"symbol": symbol.upper()},
            model_class=CompanyProfile,
            log_prefix="🏢",
            item_name="company profile"
        )
    
    # ============================================================================
    # FINANCIAL STATEMENTS
    # ============================================================================
    
    async def get_income_statement(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get income statement data"""
        return await self._fetch_and_parse_list(
            endpoint="financial-statement/income-statement",
            params={"symbol": symbol.upper(), "period": period, "limit": limit},
            model_class=IncomeStatement,
            item_name="income statements"
        )
    
    async def get_balance_sheet(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get balance sheet data"""
        return await self._fetch_and_parse_list(
            endpoint="financial-statement/balance-sheet",
            params={"symbol": symbol.upper(), "period": period, "limit": limit},
            model_class=BalanceSheet,
            item_name="balance sheets"
        )
    
    async def get_cash_flow_statement(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get cash flow statement data"""
        return await self._fetch_and_parse_list(
            endpoint="financial-statement/cash-flow-statement",
            params={"symbol": symbol.upper(), "period": period, "limit": limit},
            model_class=CashFlowStatement,
            item_name="cash flow statements"
        )
    
    # ============================================================================
    # KEY METRICS & RATIOS
    # ============================================================================
    
    async def get_key_metrics(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get key metrics and valuation ratios"""
        return await self._fetch_and_parse_list(
            endpoint="key-metrics",
            params={"symbol": symbol.upper(), "period": period, "limit": limit},
            model_class=KeyMetrics,
            log_prefix="📈",
            item_name="key metrics"
        )
    
    async def get_financial_ratios(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get financial ratios"""
        return await self._fetch_and_parse_list(
            endpoint="financial-ratios",
            params={"symbol": symbol.upper(), "period": period, "limit": limit},
            model_class=FinancialRatio,
            item_name="financial ratios"
        )
    
    async def get_financial_growth(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get financial growth metrics"""
        return await self._fetch_and_parse_list(
            endpoint="financial-growth",
            params={"symbol": symbol.upper(), "period": period, "limit": limit},
            model_class=FinancialGrowth,
            log_prefix="📈",
            item_name="financial growth periods"
        )
    
    # ============================================================================
    # MARKET DATA
    # ============================================================================
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote data"""
        return await self._fetch_and_parse_single(
            endpoint="quote",
            params={"symbol": symbol.upper()},
            model_class=Quote,
            log_prefix="💹",
            item_name="quote"
        )
    
    async def get_historical_prices(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get historical price data (end of day)"""
        params = {"symbol": symbol.upper()}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if limit:
            params["limit"] = limit
        
        result = await self._fetch_and_parse_list(
            endpoint="historical-price-eod/full",
            params=params,
            model_class=HistoricalPrice,
            data_key="historical",
            log_prefix="📈",
            item_name="days of historical prices"
        )
        
        # Add date range to result if successful
        if result.get("success"):
            result["from_date"] = from_date
            result["to_date"] = to_date
        
        return result
    
    # ============================================================================
    # ANALYST DATA
    # ============================================================================
    
    async def get_analyst_recommendations(
        self,
        symbol: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get analyst recommendations"""
        return await self._fetch_and_parse_list(
            endpoint="grade",
            params={"symbol": symbol.upper(), "limit": limit},
            model_class=AnalystRecommendation,
            log_prefix="👔",
            item_name="analyst recommendation periods"
        )
    
    # ============================================================================
    # SEARCH & SCREENER
    # ============================================================================
    
    async def search_symbol(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for stock symbols by query"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(
                endpoint="search-symbol",
                params={"query": query, "limit": limit}
            )
            return {"success": True, "results": data, "query": query}
        except Exception as e:
            return {"success": False, "message": f"Search failed: {str(e)}"}
    
    async def stock_screener(
        self,
        market_cap_more_than: Optional[int] = None,
        market_cap_lower_than: Optional[int] = None,
        price_more_than: Optional[float] = None,
        price_lower_than: Optional[float] = None,
        beta_more_than: Optional[float] = None,
        beta_lower_than: Optional[float] = None,
        volume_more_than: Optional[int] = None,
        volume_lower_than: Optional[int] = None,
        dividend_more_than: Optional[float] = None,
        dividend_lower_than: Optional[float] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        country: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Screen stocks based on various criteria"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        params = {"limit": limit}
        if market_cap_more_than: params["marketCapMoreThan"] = market_cap_more_than
        if market_cap_lower_than: params["marketCapLowerThan"] = market_cap_lower_than
        if price_more_than: params["priceMoreThan"] = price_more_than
        if price_lower_than: params["priceLowerThan"] = price_lower_than
        if beta_more_than: params["betaMoreThan"] = beta_more_than
        if beta_lower_than: params["betaLowerThan"] = beta_lower_than
        if volume_more_than: params["volumeMoreThan"] = volume_more_than
        if volume_lower_than: params["volumeLowerThan"] = volume_lower_than
        if dividend_more_than: params["dividendMoreThan"] = dividend_more_than
        if dividend_lower_than: params["dividendLowerThan"] = dividend_lower_than
        if sector: params["sector"] = sector
        if industry: params["industry"] = industry
        if country: params["country"] = country
        if exchange: params["exchange"] = exchange
        
        try:
            data = await self._fetch_api_data(endpoint="company-screener", params=params)
            return {"success": True, "results": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Screener failed: {str(e)}"}
    
    # ============================================================================
    # EARNINGS & DIVIDENDS
    # ============================================================================
    
    async def get_earnings_calendar(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get earnings calendar"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        params = {}
        if from_date: params["from"] = from_date
        if to_date: params["to"] = to_date
        
        try:
            data = await self._fetch_api_data(endpoint="earnings-calendar", params=params)
            return {"success": True, "earnings": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_dividends_calendar(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get dividends calendar"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        params = {}
        if from_date: params["from"] = from_date
        if to_date: params["to"] = to_date
        
        try:
            data = await self._fetch_api_data(endpoint="dividends-calendar", params=params)
            return {"success": True, "dividends": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_stock_splits(self, symbol: str) -> Dict[str, Any]:
        """Get stock split history for a symbol"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(
                endpoint="splits",
                params={"symbol": symbol.upper()}
            )
            return {"success": True, "symbol": symbol, "splits": data}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    # ============================================================================
    # ECONOMICS & TREASURY
    # ============================================================================
    
    async def get_treasury_rates(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
        """Get treasury rates"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        params = {}
        if from_date: params["from"] = from_date
        if to_date: params["to"] = to_date
        
        try:
            data = await self._fetch_api_data(endpoint="treasury-rates", params=params)
            return {"success": True, "rates": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_economic_indicator(self, name: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
        """Get economic indicator data (GDP, unemployment, inflation, etc.)"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        params = {"name": name}
        if from_date: params["from"] = from_date
        if to_date: params["to"] = to_date
        
        try:
            data = await self._fetch_api_data(endpoint="economic-indicators", params=params)
            return {"success": True, "indicator": name, "data": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    # ============================================================================
    # NEWS
    # ============================================================================
    
    async def get_stock_news(self, symbols: Optional[List[str]] = None, limit: int = 20) -> Dict[str, Any]:
        """Get stock news"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            if symbols:
                endpoint = "news/stock"
                params = {"symbols": ",".join(symbols), "limit": limit}
            else:
                endpoint = "news/stock-latest"
                params = {"page": 0, "limit": limit}
            
            data = await self._fetch_api_data(endpoint=endpoint, params=params)
            return {"success": True, "news": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_press_releases(self, symbols: Optional[List[str]] = None, limit: int = 20) -> Dict[str, Any]:
        """Get press releases"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            if symbols:
                endpoint = "news/press-releases"
                params = {"symbols": ",".join(symbols), "limit": limit}
            else:
                endpoint = "news/press-releases-latest"
                params = {"page": 0, "limit": limit}
            
            data = await self._fetch_api_data(endpoint=endpoint, params=params)
            return {"success": True, "press_releases": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    # ============================================================================
    # ETF & MUTUAL FUNDS
    # ============================================================================
    
    async def get_etf_holdings(self, symbol: str) -> Dict[str, Any]:
        """Get ETF holdings"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(
                endpoint="etf/holdings",
                params={"symbol": symbol.upper()}
            )
            return {"success": True, "symbol": symbol, "holdings": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_etf_info(self, symbol: str) -> Dict[str, Any]:
        """Get ETF information"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(
                endpoint="etf/info",
                params={"symbol": symbol.upper()}
            )
            result = data[0] if isinstance(data, list) and data else data
            return {"success": True, "symbol": symbol, "info": result}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_etf_sector_weighting(self, symbol: str) -> Dict[str, Any]:
        """Get ETF sector weightings"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(
                endpoint="etf/sector-weightings",
                params={"symbol": symbol.upper()}
            )
            return {"success": True, "symbol": symbol, "sectors": data}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    # ============================================================================
    # MARKET PERFORMANCE & GAINERS/LOSERS
    # ============================================================================
    
    async def get_market_gainers(self) -> Dict[str, Any]:
        """Get biggest stock gainers"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(endpoint="biggest-gainers", params={})
            return {"success": True, "gainers": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_market_losers(self) -> Dict[str, Any]:
        """Get biggest stock losers"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(endpoint="biggest-losers", params={})
            return {"success": True, "losers": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_most_active(self) -> Dict[str, Any]:
        """Get most actively traded stocks"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(endpoint="most-actives", params={})
            return {"success": True, "most_active": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_sector_performance(self) -> Dict[str, Any]:
        """Get sector performance"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(endpoint="sector-performance-snapshot", params={})
            return {"success": True, "sectors": data}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    # ============================================================================
    # STOCK PEERS & COMPARISONS
    # ============================================================================
    
    async def get_stock_peers(self, symbol: str) -> Dict[str, Any]:
        """Get stock peer companies (US stocks only due to API plan limitations)"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(
                endpoint="stock-peers",
                params={"symbol": symbol.upper()}
            )
            
            # Filter out non-US stocks (those with exchange suffixes like .TO, .L, etc.)
            # Most API plans only support US exchanges
            if isinstance(data, list):
                us_peers = [peer for peer in data if '.' not in peer.get('symbol', '')]
                if len(us_peers) < len(data):
                    filtered_count = len(data) - len(us_peers)
                    print(f"ℹ️ Filtered out {filtered_count} non-US peers (API plan limitation)", flush=True)
                data = us_peers
            
            return {"success": True, "symbol": symbol, "peers": data}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    # ============================================================================
    # PRICE TARGETS & UPGRADES/DOWNGRADES
    # ============================================================================
    
    async def get_price_target(self, symbol: str) -> Dict[str, Any]:
        """Get analyst price targets"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(
                endpoint="price-target-consensus",
                params={"symbol": symbol.upper()}
            )
            return {"success": True, "symbol": symbol, "price_target": data}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def get_upgrades_downgrades(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get analyst upgrades and downgrades"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(
                endpoint="grades",
                params={"symbol": symbol.upper(), "limit": limit}
            )
            return {"success": True, "symbol": symbol, "grades": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    # ============================================================================
    # SEC FILINGS
    # ============================================================================
    
    async def get_sec_filings(
        self,
        symbol: Optional[str] = None,
        form_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get SEC filings"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            if symbol:
                endpoint = "sec-filings-search/symbol"
                params = {"symbol": symbol.upper(), "limit": limit}
            elif form_type:
                endpoint = "sec-filings-search/form-type"
                params = {"formType": form_type, "limit": limit}
            else:
                endpoint = "sec-filings-financials"
                params = {"limit": limit, "page": 0}
            
            if from_date: params["from"] = from_date
            if to_date: params["to"] = to_date
            
            data = await self._fetch_api_data(endpoint=endpoint, params=params)
            return {"success": True, "filings": data, "count": len(data) if data else 0}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    # ============================================================================
    # SOCIAL SENTIMENT & ESG
    # ============================================================================
    
    async def get_esg_score(self, symbol: str) -> Dict[str, Any]:
        """Get ESG (Environmental, Social, Governance) score"""
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            data = await self._fetch_api_data(
                endpoint="esg-ratings",
                params={"symbol": symbol.upper()}
            )
            return {"success": True, "symbol": symbol, "esg": data}
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global tools instance
fmp_tools = FMPTools()

