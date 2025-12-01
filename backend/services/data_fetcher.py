"""
Data Fetcher Service - Fetch data from various sources for strategy rules
"""
from typing import Dict, Any, Optional
from models.strategy_v2 import DataSource
from modules.tools.clients.fmp import FMPClient
import logging

logger = logging.getLogger(__name__)


class DataFetcherService:
    """Service to fetch data from various sources for strategy execution"""
    
    def __init__(self):
        self.fmp_client = FMPClient()
    
    async def fetch_data(self, source: DataSource, ticker: str) -> Dict[str, Any]:
        """
        Fetch data from a source
        
        Args:
            source: DataSource specification
            ticker: Stock ticker symbol
            
        Returns:
            Dict containing the fetched data
        """
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
                return {"error": f"Unknown source type: {source.type}"}
        except Exception as e:
            logger.error(f"Error fetching data from {source.type}/{source.endpoint}: {str(e)}")
            return {"error": str(e)}
    
    async def _fetch_fmp(self, endpoint: str, ticker: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Financial Modeling Prep API"""
        
        endpoint_map = {
            # Financial statements
            "income-statement": lambda: self.fmp_client.get_income_statement(
                ticker, 
                period=params.get("period", "annual"),
                limit=params.get("limit", 4)
            ),
            "balance-sheet": lambda: self.fmp_client.get_balance_sheet(
                ticker,
                period=params.get("period", "annual"),
                limit=params.get("limit", 4)
            ),
            "cash-flow": lambda: self.fmp_client.get_cash_flow_statement(
                ticker,
                period=params.get("period", "annual"),
                limit=params.get("limit", 4)
            ),
            
            # Company info
            "company-profile": lambda: self.fmp_client.get_company_profile(ticker),
            
            # Trading data
            "insider-trading": lambda: self.fmp_client.get_insider_trading(
                ticker,
                limit=params.get("limit", 100)
            ),
            "institutional-ownership": lambda: self.fmp_client.get_institutional_holders(ticker),
            
            # Price data
            "price-history": lambda: self.fmp_client.get_historical_price(
                ticker,
                from_date=params.get("from_date"),
                to_date=params.get("to_date")
            ),
            "quote": lambda: self.fmp_client.get_quote(ticker),
            
            # Metrics
            "key-metrics": lambda: self.fmp_client.get_key_metrics(
                ticker,
                period=params.get("period", "annual"),
                limit=params.get("limit", 4)
            ),
            "financial-ratios": lambda: self.fmp_client.get_financial_ratios(
                ticker,
                period=params.get("period", "annual"),
                limit=params.get("limit", 4)
            ),
        }
        
        if endpoint not in endpoint_map:
            logger.warning(f"FMP endpoint not implemented: {endpoint}")
            return {"error": f"Endpoint not implemented: {endpoint}"}
        
        try:
            data = await endpoint_map[endpoint]()
            return {"success": True, "data": data, "source": "fmp", "endpoint": endpoint}
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
            price_data = await self.fmp_client.get_historical_price(ticker, limit=days)
            
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

