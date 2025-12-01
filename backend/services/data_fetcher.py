"""
Data Fetcher Service - Fetch data from various sources for strategy rules
"""
from typing import Dict, Any, Optional
from models.strategy_v2 import DataSource
from modules.tools.clients.fmp import fmp_tools
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class DataFetcherService:
    """Service to fetch data from various sources for strategy execution"""
    
    def __init__(self):
        self.fmp_client = fmp_tools
        # Rate limiting: small delay between API calls to prevent overwhelming the API
        self._last_call_time = None
        self._min_delay_seconds = 0.1  # 100ms between calls
    
    async def fetch_data(self, source: DataSource, ticker: str) -> Dict[str, Any]:
        """
        Fetch data from a source with rate limiting
        
        Args:
            source: DataSource specification
            ticker: Stock ticker symbol
            
        Returns:
            Dict containing the fetched data
        """
        # Rate limiting: wait if needed
        await self._rate_limit()
        
        try:
            if source.type == "fmp":
                return await self._fetch_fmp(source.endpoint, ticker, source.parameters)
            elif source.type == "reddit":
                return await self._fetch_reddit(source.endpoint, ticker, source.parameters)
            elif source.type == "calculated":
                return await self._fetch_calculated(source.endpoint, ticker, source.parameters)
            elif source.type == "portfolio":
                return await self._fetch_portfolio(source.endpoint, ticker, source.parameters)
            else:
                logger.error(f"Unknown data source type: {source.type}")
                return {"success": False, "error": f"Unknown source type: {source.type}"}
        except Exception as e:
            logger.error(f"Error fetching data from {source.type}/{source.endpoint}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _rate_limit(self):
        """Apply rate limiting between API calls"""
        if self._last_call_time is not None:
            elapsed = datetime.now().timestamp() - self._last_call_time
            if elapsed < self._min_delay_seconds:
                await asyncio.sleep(self._min_delay_seconds - elapsed)
        self._last_call_time = datetime.now().timestamp()
    
    async def _fetch_fmp(self, endpoint: str, ticker: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Financial Modeling Prep API"""
        
        # Map strategy endpoint names to FMP endpoint names
        endpoint_map = {
            # Financial statements
            "income-statement": "income-statement",
            "balance-sheet": "balance-sheet-statement",
            "balance-sheet-statement": "balance-sheet-statement",  # Also accept full name
            "cash-flow": "cash-flow-statement",
            "cash-flow-statement": "cash-flow-statement",  # Also accept full name
            
            # Company info
            "company-profile": "profile",
            "profile": "profile",  # Also accept 'profile' directly
            
            # Trading data
            "insider-trading": "insider-trading-search",
            
            # Price data
            "price-history": "historical-price-full",
            "quote": "quote",
            
            # Metrics
            "key-metrics": "key-metrics",
            "financial-ratios": "ratios",
            "financial-growth": "financial-growth",
            
            # Analyst data
            "price-target-consensus": "price-target-consensus",
            "analyst-recommendations": "grade",
            
            # Screening & Market data
            "company-screener": "company-screener",
            "sector-performance": "sector-performance-snapshot",
            "market-movers": "biggest-gainers",
        }
        
        if endpoint not in endpoint_map:
            logger.warning(f"FMP endpoint not implemented: {endpoint}")
            return {"success": False, "error": f"Endpoint not implemented: {endpoint}"}
        
        try:
            fmp_endpoint = endpoint_map[endpoint]
            
            # Endpoints that don't require a symbol
            no_symbol_endpoints = ["company-screener", "sector-performance", "market-movers"]
            
            # Build FMP params
            fmp_params = {}
            
            # Only add symbol if endpoint requires it
            if endpoint not in no_symbol_endpoints and ticker and ticker.upper() not in ["N/A", "UNKNOWN", "NULL", ""]:
                fmp_params["symbol"] = ticker
            
            # Add period and limit for financial data
            if endpoint in ["income-statement", "balance-sheet", "balance-sheet-statement", "cash-flow", "cash-flow-statement", "key-metrics", "financial-ratios", "financial-growth"]:
                fmp_params["period"] = params.get("period", "annual")
                fmp_params["limit"] = params.get("limit", 4)
            
            # Add limit for insider trading
            elif endpoint == "insider-trading":
                fmp_params["limit"] = params.get("limit", 100)
            
            # Add date range for price history
            elif endpoint == "price-history":
                if params.get("from_date"):
                    fmp_params["from"] = params.get("from_date")
                if params.get("to_date"):
                    fmp_params["to"] = params.get("to_date")
                if params.get("limit"):
                    fmp_params["limit"] = params.get("limit")
            
            # Add limit for analyst recommendations
            elif endpoint == "analyst-recommendations":
                fmp_params["limit"] = params.get("limit", 10)
            
            # Add screener params
            elif endpoint == "company-screener":
                # Pass through all screening params
                for key in ["marketCapMoreThan", "marketCapLowerThan", "sector", "industry",
                           "betaMoreThan", "betaLowerThan", "priceMoreThan", "priceLowerThan",
                           "dividendMoreThan", "dividendLowerThan", "volumeMoreThan", "volumeLowerThan",
                           "exchange", "country", "isEtf", "isFund", "isActivelyTrading", "limit"]:
                    if key in params:
                        fmp_params[key] = params[key]
            
            # Call FMP - it already returns {success, data/error, ...}
            result = await self.fmp_client.get_fmp_data(fmp_endpoint, fmp_params)
            
            # Log the result
            if result.get("success"):
                data_preview = str(result.get("data", ""))[:200]
                logger.info(f"✅ FMP {endpoint} for {ticker}: success, data preview: {data_preview}...")
            else:
                error_msg = result.get('error') or result.get('message') or 'Unknown error'
                logger.warning(f"❌ FMP {endpoint} for {ticker}: {error_msg}")
                logger.debug(f"Full FMP result: {result}")
            
            # Add metadata
            result["source"] = "fmp"
            result["endpoint"] = endpoint
            
            return result
            
        except Exception as e:
            logger.error(f"FMP API error for {endpoint}: {str(e)}")
            return {"success": False, "error": str(e), "source": "fmp", "endpoint": endpoint}
    
    async def _fetch_reddit(self, endpoint: str, ticker: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Reddit sentiment API"""
        from modules.tools.definitions import tool_registry
        
        try:
            if endpoint == "ticker_sentiment":
                # Use existing reddit sentiment tool
                tool = tool_registry.get_tool("get_reddit_ticker_sentiment")
                if tool:
                    result = await tool.func(ticker=ticker)
                    return {"success": True, "data": result, "source": "reddit", "endpoint": endpoint}
            
            elif endpoint == "trending_stocks":
                tool = tool_registry.get_tool("get_reddit_trending_stocks")
                if tool:
                    result = await tool.func(limit=params.get("limit", 20))
                    return {"success": True, "data": result, "source": "reddit", "endpoint": endpoint}
            
            return {"success": False, "error": f"Reddit endpoint not implemented: {endpoint}"}
            
        except Exception as e:
            logger.error(f"Reddit API error for {endpoint}: {str(e)}")
            return {"success": False, "error": str(e), "source": "reddit", "endpoint": endpoint}
    
    async def _fetch_calculated(self, endpoint: str, ticker: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate technical indicators"""
        try:
            # First get price history
            days = params.get("days", 100)
            result = await self.fmp_client.get_fmp_data(
                "historical-price-full",
                {"symbol": ticker, "limit": days}
            )
            
            if not result.get("success"):
                return {"success": False, "error": "Failed to fetch price data"}
            
            # Extract price data - FMP returns it under "data" key
            price_data = result.get("data")
            if not price_data:
                return {"success": False, "error": "No price data available"}
            
            if endpoint == "rsi":
                period = params.get("period", 14)
                rsi = self._calculate_rsi(price_data, period)
                return {"success": True, "data": {"rsi": rsi, "period": period}, "source": "calculated", "endpoint": "rsi"}
            
            elif endpoint == "moving_average":
                period = params.get("period", 50)
                ma = self._calculate_ma(price_data, period)
                return {"success": True, "data": {"ma": ma, "period": period}, "source": "calculated", "endpoint": "moving_average"}
            
            elif endpoint == "volume_analysis":
                avg_volume = sum(d.get("volume", 0) for d in price_data[:20]) / 20
                current_volume = price_data[0].get("volume", 0) if price_data else 0
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
                return {
                    "success": True,
                    "data": {
                        "current_volume": current_volume,
                        "avg_volume_20d": avg_volume,
                        "volume_ratio": volume_ratio
                    },
                    "source": "calculated",
                    "endpoint": "volume_analysis"
                }
            
            return {"success": False, "error": f"Calculated indicator not implemented: {endpoint}"}
            
        except Exception as e:
            logger.error(f"Calculation error for {endpoint}: {str(e)}")
            return {"success": False, "error": str(e), "source": "calculated", "endpoint": endpoint}
    
    async def _fetch_portfolio(self, endpoint: str, ticker: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch user portfolio data"""
        from modules.tools.definitions import tool_registry
        
        try:
            if endpoint == "current_positions":
                # This would need user context
                # For now, return placeholder
                return {"success": False, "error": "Portfolio data requires user context"}
            
            return {"success": False, "error": f"Portfolio endpoint not implemented: {endpoint}"}
            
        except Exception as e:
            logger.error(f"Portfolio error for {endpoint}: {str(e)}")
            return {"success": False, "error": str(e), "source": "portfolio", "endpoint": endpoint}
    
    def _calculate_rsi(self, price_data: list, period: int = 14) -> Optional[float]:
        """Calculate RSI from price data"""
        if len(price_data) < period + 1:
            return None
        
        # Calculate price changes
        changes = []
        for i in range(len(price_data) - 1):
            change = price_data[i]["close"] - price_data[i + 1]["close"]
            changes.append(change)
        
        # Separate gains and losses
        gains = [c if c > 0 else 0 for c in changes[:period]]
        losses = [-c if c < 0 else 0 for c in changes[:period]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def _calculate_ma(self, price_data: list, period: int) -> Optional[float]:
        """Calculate moving average"""
        if len(price_data) < period:
            return None
        
        prices = [d["close"] for d in price_data[:period]]
        ma = sum(prices) / period
        
        return round(ma, 2)

