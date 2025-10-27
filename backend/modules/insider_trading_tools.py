"""
Financial Modeling Prep API tools for insider trading data
Includes Senate, House, and corporate insider trades
"""
import httpx
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from models.insider_trading import (
    SenateTrade, HouseTrade, InsiderTrade, InsiderTradingResponse, InsiderTradingStatistics
)
from config import Config


class InsiderTradingTools:
    """
    Tools for fetching insider trading data from Financial Modeling Prep API
    
    Tracks:
    - Senate trading disclosures
    - House trading disclosures  
    - Corporate insider trades (SEC Form 4)
    """
    
    # FMP has migrated to /stable/ endpoints (legacy v3/v4 deprecated as of Aug 2025)
    BASE_URL = "https://financialmodelingprep.com/stable"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = Config.FMP_API_KEY
        self.api_enabled = bool(self.api_key)
    
    def _check_api_key(self) -> dict:
        """Check if API key is configured"""
        if not self.api_enabled:
            return {
                "success": False,
                "message": "Insider trading features require a Financial Modeling Prep API key. Please add FMP_API_KEY to your .env file. Get your API key from: https://site.financialmodelingprep.com/developer/docs/pricing"
            }
        return None
    
    async def get_recent_senate_trades(
        self, 
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get recent Senate trading disclosures
        
        Args:
            limit: Number of trades to return (default 50)
            
        Returns:
            Dictionary with recent Senate trades
        """
        # Check API key
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            print(f"🏛️ Fetching recent Senate trades (limit: {limit})...", flush=True)
            
            # Use free tier endpoint
            url = f"{self.BASE_URL}/senate-latest"
            params = {
                "apikey": self.api_key,
                "page": 0,
                "limit": limit
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return {
                    "success": False,
                    "message": "No Senate trades found"
                }
            
            # Limit results
            trades = data[:limit] if isinstance(data, list) else []
            
            # Parse and enrich using Pydantic models
            parsed_trades = []
            for trade in trades:
                try:
                    senate_trade = SenateTrade(**trade)
                    parsed_trades.append(senate_trade.model_dump())
                except Exception as e:
                    print(f"⚠️ Error parsing Senate trade: {e}", flush=True)
                    continue
            
            # Convert to DataFrame for compact CSV format
            trades_objects = [SenateTrade(**trade) for trade in parsed_trades]
            df = SenateTrade.list_to_df(trades_objects)
            
            print(f"✅ Found {len(parsed_trades)} Senate trades", flush=True)
            
            return {
                "success": True,
                "data_type": "senate",
                "trades_csv": df.to_csv(index=False),  # CSV format is 25% more compact than split
                "total_count": len(parsed_trades),
                "message": f"Found {len(parsed_trades)} recent Senate trades. Data is in CSV format."
            }
            
        except httpx.HTTPError as e:
            error_msg = str(e)
            print(f"❌ HTTP error fetching Senate trades: {error_msg}", flush=True)
            
            # Check if it's a 402/403 (API tier restriction)
            if "402" in error_msg or "403" in error_msg:
                return {
                    "success": False,
                    "message": "Senate trading data requires a paid FMP API plan. Please upgrade at https://site.financialmodelingprep.com/developer/docs/pricing"
                }
            
            return {
                "success": False,
                "message": f"Failed to fetch Senate trades: {error_msg}"
            }
        except Exception as e:
            print(f"❌ Error fetching Senate trades: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def get_recent_house_trades(
        self, 
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get recent House trading disclosures
        
        Args:
            limit: Number of trades to return (default 50)
            
        Returns:
            Dictionary with recent House trades
        """
        # Check API key
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            print(f"🏛️ Fetching recent House trades (limit: {limit})...", flush=True)
            
            # Use free tier endpoint
            url = f"{self.BASE_URL}/house-latest"
            params = {
                "apikey": self.api_key,
                "page": 0,
                "limit": limit
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return {
                    "success": False,
                    "message": "No House trades found"
                }
            
            # Limit results
            trades = data[:limit] if isinstance(data, list) else []
            
            # Parse and enrich using Pydantic models
            parsed_trades = []
            for trade in trades:
                try:
                    house_trade = HouseTrade(**trade)
                    parsed_trades.append(house_trade.model_dump())
                except Exception as e:
                    print(f"⚠️ Error parsing House trade: {e}", flush=True)
                    continue
            
            # Convert to DataFrame for compact CSV format
            trades_objects = [HouseTrade(**trade) for trade in parsed_trades]
            df = HouseTrade.list_to_df(trades_objects)
            
            print(f"✅ Found {len(parsed_trades)} House trades", flush=True)
            
            return {
                "success": True,
                "data_type": "house",
                "trades_csv": df.to_csv(index=False),  # CSV format is 25% more compact than split
                "total_count": len(parsed_trades),
                "message": f"Found {len(parsed_trades)} recent House trades. Data is in CSV format."
            }
            
        except httpx.HTTPError as e:
            error_msg = str(e)
            print(f"❌ HTTP error fetching House trades: {error_msg}", flush=True)
            
            # Check if it's a 402/403 (API tier restriction)
            if "402" in error_msg or "403" in error_msg:
                return {
                    "success": False,
                    "message": "House trading data requires a paid FMP API plan. Please upgrade at https://site.financialmodelingprep.com/developer/docs/pricing"
                }
            
            return {
                "success": False,
                "message": f"Failed to fetch House trades: {error_msg}"
            }
        except Exception as e:
            print(f"❌ Error fetching House trades: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def get_recent_insider_trades(
        self, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get recent corporate insider trades (SEC Form 4 filings)
        
        Args:
            limit: Number of trades to return (default 20)
            
        Returns:
            Dictionary with recent insider trades
        """
        # Check API key
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            print(f"💼 Fetching recent insider trades (limit: {limit})...", flush=True)
            
            # Use stable endpoint with /latest
            url = f"{self.BASE_URL}/insider-trading/latest"
            params = {
                "apikey": self.api_key,
                "page": 0,
                "limit": limit
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return {
                    "success": False,
                    "message": "No insider trades found"
                }
            
            # Limit results
            trades = data[:limit] if isinstance(data, list) else []
            
            # Parse and enrich using Pydantic models
            parsed_trades = []
            for trade in trades:
                try:
                    insider_trade = InsiderTrade(**trade)  # Pydantic will handle the camelCase to snake_case conversion
                    parsed_trades.append(insider_trade.model_dump())
                except Exception as e:
                    print(f"⚠️ Error parsing insider trade: {e}", flush=True)
                    continue
            
            # Convert to DataFrame for compact CSV format
            trades_objects = [InsiderTrade(**trade) for trade in parsed_trades]
            df = InsiderTrade.list_to_df(trades_objects)
            
            print(f"✅ Found {len(parsed_trades)} insider trades", flush=True)
            
            return {
                "success": True,
                "data_type": "insider",
                "trades_csv": df.to_csv(index=False),  # CSV format is 25% more compact than split
                "total_count": len(parsed_trades),
                "message": f"Found {len(parsed_trades)} recent insider trades. Data is in CSV format."
            }
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP error fetching insider trades: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Failed to fetch insider trades: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Error fetching insider trades: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def search_ticker_insider_activity(
        self, 
        ticker: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for all insider trading activity for a specific ticker
        Includes Senate, House, and corporate insider trades
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum trades per source
            
        Returns:
            Dictionary with all insider activity for the ticker
        """
        # Check API key
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            print(f"🔍 Searching insider activity for {ticker}...", flush=True)
            
            # Fetch corporate insider trades for this ticker (stable endpoint)
            url = f"{self.BASE_URL}/insider-trading/latest"
            params = {
                "symbol": ticker.upper(),
                "apikey": self.api_key,
                "page": 0,
                "limit": limit
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            insider_data = response.json()
            
            # Parse corporate insider trades using Pydantic
            corporate_trades = []
            if insider_data and isinstance(insider_data, list):
                for trade in insider_data[:limit]:
                    try:
                        insider_trade = InsiderTrade(**trade)  # Pydantic will handle the camelCase to snake_case conversion
                        trade_dict = insider_trade.model_dump()
                        trade_dict["source"] = "Corporate Insider"
                        corporate_trades.append(trade_dict)
                    except Exception as e:
                        continue
            
            # Get Senate/House trades for this ticker (API supports symbol parameter)
            senate_url = f"{self.BASE_URL}/senate-latest"
            senate_params = {
                "symbol": ticker.upper(),
                "apikey": self.api_key,
                "page": 0,
                "limit": limit
            }
            
            senate_trades = []
            house_trades = []
            
            # Fetch Senate trades
            try:
                senate_response = await self.client.get(senate_url, params=senate_params)
                if senate_response.status_code == 200:
                    senate_data = senate_response.json()
                    if senate_data and isinstance(senate_data, list):
                        for trade in senate_data:
                            try:
                                senate_trade = SenateTrade(**trade)
                                trade_dict = senate_trade.model_dump()
                                trade_dict["source"] = "Senate"
                                senate_trades.append(trade_dict)
                            except Exception as e:
                                continue
            except Exception as e:
                print(f"⚠️ Could not fetch Senate trades for {ticker}: {e}", flush=True)
            
            # Fetch House trades
            house_url = f"{self.BASE_URL}/house-latest"
            house_params = {
                "symbol": ticker.upper(),
                "apikey": self.api_key,
                "page": 0,
                "limit": limit
            }
            try:
                house_response = await self.client.get(house_url, params=house_params)
                if house_response.status_code == 200:
                    house_data = house_response.json()
                    if house_data and isinstance(house_data, list):
                        for trade in house_data:
                            try:
                                house_trade = HouseTrade(**trade)
                                trade_dict = house_trade.model_dump()
                                trade_dict["source"] = "House"
                                house_trades.append(trade_dict)
                            except Exception as e:
                                continue
            except Exception as e:
                print(f"⚠️ Could not fetch House trades for {ticker}: {e}", flush=True)
            
            # Combine all trades
            all_trades = corporate_trades + senate_trades + house_trades
            
            if not all_trades:
                return {
                    "success": False,
                    "message": f"No insider trading activity found for {ticker}"
                }
            
            # Sort by date (most recent first)
            all_trades.sort(
                key=lambda x: x.get("transaction_date") or x.get("filing_date") or "", 
                reverse=True
            )
            
            # Calculate summary stats
            total_purchases = sum(1 for t in all_trades if "Purchase" in str(t.get("transaction_type", t.get("type", ""))))
            total_sales = sum(1 for t in all_trades if "Sale" in str(t.get("transaction_type", t.get("type", ""))))
            
            # Convert to DataFrame for compact CSV format
            df_data = []
            for t in all_trades:
                df_data.append({
                    "date": t.get("transaction_date") or t.get("filing_date") or "N/A",
                    "insider": (t.get("reporting_name") or t.get("firstName", "") + " " + t.get("lastName", ""))[:30],
                    "position": (t.get("type_of_owner") or t.get("office") or "N/A")[:25],
                    "type": t.get("transaction_type") or t.get("type") or "N/A",
                    "shares": t.get("securities_transacted") or t.get("amount") or "N/A",
                    "price": t.get("price") or "N/A",
                    "source": t.get("source") or "N/A"
                })
            df = pd.DataFrame(df_data)
            
            print(f"✅ Found {len(all_trades)} total trades for {ticker} ({total_purchases} buys, {total_sales} sells)", flush=True)
            
            return {
                "success": True,
                "ticker": ticker.upper(),
                "data_type": "mixed",
                "trades_csv": df.to_csv(index=False),  # CSV format is 25% more compact
                "total_count": len(all_trades),
                "summary": {
                    "total_trades": len(all_trades),
                    "purchases": total_purchases,
                    "sales": total_sales,
                    "congressional_trades": len(senate_trades) + len(house_trades),
                    "corporate_insider_trades": len(corporate_trades)
                },
                "message": f"Found {len(all_trades)} insider trades for {ticker} ({total_purchases} purchases, {total_sales} sales). Data is in CSV format."
            }
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP error searching ticker activity: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Failed to search ticker activity: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Error searching ticker activity: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def get_portfolio_insider_activity(
        self,
        tickers: List[str],
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get insider trading activity for multiple tickers (user's portfolio)
        
        Args:
            tickers: List of ticker symbols in user's portfolio
            days_back: Look back this many days for activity
            
        Returns:
            Dictionary with insider activity across portfolio (SUMMARIZED to avoid huge responses)
        """
        # Check API key
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            print(f"📊 Fetching insider activity for portfolio tickers: {', '.join(tickers)}", flush=True)
            
            portfolio_activity = {}
            tickers_with_activity = []
            
            for ticker in tickers:
                result = await self.search_ticker_insider_activity(ticker, limit=20)  # Reduce from 50 to 20
                
                if result.get("success"):
                    # Filter to recent activity only
                    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                    recent_trades = [
                        t for t in result.get("trades", [])
                        if (t.get("transaction_date") or t.get("filing_date") or "9999-99-99") >= cutoff_date
                    ]
                    
                    if recent_trades:
                        # Sort by date and limit to top 3 most recent (now using snake_case from Pydantic)
                        recent_trades.sort(
                            key=lambda x: x.get("transaction_date") or x.get("filing_date") or x.get("disclosure_date") or "", 
                            reverse=True
                        )
                        top_trades = recent_trades[:3]
                        
                        # Calculate stats (using snake_case field names from Pydantic)
                        purchases = sum(1 for t in recent_trades if "Purchase" in str(t.get("transaction_type") or t.get("type") or ""))
                        sales = sum(1 for t in recent_trades if "Sale" in str(t.get("transaction_type") or t.get("type") or ""))
                        
                        # Create DataFrame from trades - Pydantic models now output snake_case
                        df_data = []
                        for t in top_trades:
                            # Get trader name (Pydantic outputs snake_case now)
                            trader_name = (
                                t.get("reporting_name") or  # Corporate insider
                                f"{t.get('first_name', '')} {t.get('last_name', '')}".strip() or  # Senate/House
                                "Unknown"
                            )[:25]
                            
                            df_data.append({
                                "date": t.get("transaction_date") or t.get("filing_date") or t.get("disclosure_date"),
                                "trader": trader_name,
                                "type": t.get("transaction_type") or t.get("type") or "Unknown",
                                "shares": t.get("securities_transacted") or t.get("amount") or "N/A",
                                "price": t.get("price") or "N/A",
                                "source": t.get("source") or "N/A"
                            })
                        
                        # Convert to DataFrame and then to compact CSV format
                        df = pd.DataFrame(df_data)
                        
                        portfolio_activity[ticker] = {
                            "ticker": ticker,
                            "total_trades": len(recent_trades),
                            "purchases": purchases,
                            "sales": sales,
                            "sentiment": "BULLISH" if purchases > sales else "BEARISH" if sales > purchases else "NEUTRAL",
                            # Use CSV format: 25% more compact than split format
                            "trades_csv": df.to_csv(index=False)
                        }
                        tickers_with_activity.append(ticker)
            
            if not portfolio_activity:
                return {
                    "success": True,
                    "message": f"No insider activity found for your portfolio in the last {days_back} days",
                    "portfolio_activity": {},
                    "tickers_with_activity": [],
                    "days_back": days_back
                }
            
            # Sort by most activity
            sorted_activity = sorted(
                portfolio_activity.items(),
                key=lambda x: x[1]["total_trades"],
                reverse=True
            )
            
            print(f"✅ Found insider activity in {len(portfolio_activity)} of {len(tickers)} portfolio tickers", flush=True)
            
            return {
                "success": True,
                "message": f"Found insider activity in {len(portfolio_activity)} of your {len(tickers)} portfolio stocks in the last {days_back} days. Data is in CSV format.",
                "data_format": "CSV format - Each ticker has 'trades_csv' with CSV data (header + rows) for easy reading",
                "portfolio_activity": dict(sorted_activity),
                "tickers_with_activity": tickers_with_activity,
                "days_back": days_back
            }
            
        except Exception as e:
            print(f"❌ Error fetching portfolio insider activity: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def get_insider_trading_statistics(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        Get quarterly aggregated insider trading statistics for a specific stock
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with quarterly insider trading statistics
        """
        # Check API key
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            print(f"📊 Fetching insider trading statistics for {symbol}...", flush=True)
            
            url = f"{self.BASE_URL}/insider-trading/statistics"
            params = {
                "apikey": self.api_key,
                "symbol": symbol.upper()
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return {
                    "success": False,
                    "message": f"No insider trading statistics found for {symbol}"
                }
            
            # Parse using Pydantic models
            parsed_stats = []
            for stat in data:
                try:
                    insider_stat = InsiderTradingStatistics(**stat)
                    parsed_stats.append(insider_stat.model_dump())
                except Exception as e:
                    print(f"⚠️ Error parsing statistic: {e}", flush=True)
                    continue
            
            if not parsed_stats:
                return {
                    "success": False,
                    "message": f"Could not parse statistics data for {symbol}"
                }
            
            # Create DataFrame for easier analysis
            stats_objects = [InsiderTradingStatistics(**stat) for stat in parsed_stats]
            df = InsiderTradingStatistics.list_to_df(stats_objects)
            
            # Get recent quarters (last 8 quarters = 2 years)
            recent_stats = parsed_stats[:8]
            
            # Calculate summary metrics
            recent_buys = sum(s['acquired_transactions'] for s in recent_stats)
            recent_sells = sum(s['disposed_transactions'] for s in recent_stats)
            avg_ratio = sum(s['acquired_disposed_ratio'] for s in recent_stats) / len(recent_stats) if recent_stats else 0
            
            print(f"✅ Found {len(parsed_stats)} quarters of statistics for {symbol}", flush=True)
            
            return {
                "success": True,
                "message": f"Found {len(parsed_stats)} quarters of insider trading statistics for {symbol}",
                "symbol": symbol,
                "quarterly_statistics": recent_stats,
                "summary": {
                    "total_quarters": len(parsed_stats),
                    "recent_buy_transactions": recent_buys,
                    "recent_sell_transactions": recent_sells,
                    "avg_buy_sell_ratio": round(avg_ratio, 2),
                    "periods_analyzed": f"Last {len(recent_stats)} quarters"
                },
                "statistics_csv": df.to_csv(index=False)
            }
            
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP error fetching insider statistics: {e}", flush=True)
            return {
                "success": False,
                "message": f"Error fetching insider statistics for {symbol}: {e.response.status_code} {e.response.reason_phrase}"
            }
        except Exception as e:
            print(f"❌ Error fetching insider statistics: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def search_insider_trades(
        self,
        symbol: Optional[str] = None,
        reporting_cik: Optional[str] = None,
        company_cik: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: int = 50,
        page: int = 0
    ) -> Dict[str, Any]:
        """
        Search insider trades with advanced filters
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            reporting_cik: CIK of the person reporting (insider)
            company_cik: CIK of the company
            transaction_type: Transaction type (e.g., "P-Purchase", "S-Sale", "A-Award")
            limit: Number of results to return (default 50)
            page: Page number for pagination (default 0)
            
        Returns:
            Dictionary with filtered insider trades
        """
        # Check API key
        api_check = self._check_api_key()
        if api_check:
            return api_check
        
        try:
            filters_str = []
            if symbol:
                filters_str.append(f"symbol={symbol}")
            if reporting_cik:
                filters_str.append(f"reportingCik={reporting_cik}")
            if company_cik:
                filters_str.append(f"companyCik={company_cik}")
            if transaction_type:
                filters_str.append(f"type={transaction_type}")
            
            filters_display = ", ".join(filters_str) if filters_str else "no filters"
            print(f"🔍 Searching insider trades with filters: {filters_display}...", flush=True)
            
            url = f"{self.BASE_URL}/insider-trading/search"
            params = {
                "apikey": self.api_key,
                "page": page,
                "limit": limit
            }
            
            # Add optional filters
            if symbol:
                params["symbol"] = symbol.upper()
            if reporting_cik:
                params["reportingCik"] = reporting_cik
            if company_cik:
                params["companyCik"] = company_cik
            if transaction_type:
                params["transactionType"] = transaction_type
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return {
                    "success": False,
                    "message": f"No insider trades found matching filters: {filters_display}"
                }
            
            # Limit results
            trades = data[:limit] if isinstance(data, list) else []
            
            # Parse using Pydantic models
            parsed_trades = []
            for trade in trades:
                try:
                    insider_trade = InsiderTrade(**trade)
                    parsed_trades.append(insider_trade.model_dump())
                except Exception as e:
                    print(f"⚠️ Error parsing trade: {e}", flush=True)
                    continue
            
            if not parsed_trades:
                return {
                    "success": False,
                    "message": "Could not parse any trades from the search results"
                }
            
            # Create DataFrame for compact CSV format
            trades_objects = [InsiderTrade(**trade) for trade in parsed_trades]
            df = InsiderTrade.list_to_df(trades_objects)
            
            print(f"✅ Found {len(parsed_trades)} insider trades matching filters", flush=True)
            
            return {
                "success": True,
                "message": f"Found {len(parsed_trades)} insider trades matching your search. Data is in CSV format.",
                "filters": {
                    "symbol": symbol,
                    "reporting_cik": reporting_cik,
                    "company_cik": company_cik,
                    "transaction_type": transaction_type,
                    "page": page,
                    "limit": limit
                },
                "total_count": len(parsed_trades),
                "trades_csv": df.to_csv(index=False)  # CSV format is 25% more compact
            }
            
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP error searching insider trades: {e}", flush=True)
            return {
                "success": False,
                "message": f"Error searching insider trades: {e.response.status_code} {e.response.reason_phrase}"
            }
        except Exception as e:
            print(f"❌ Error searching insider trades: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Tool definitions for LiteLLM
INSIDER_TRADING_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_recent_senate_trades",
            "description": "Get recent stock trading disclosures from U.S. Senators. Shows what stocks senators are buying and selling. Use when user asks about Senate trades, congressional trades, or what politicians are buying.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent trades to return (default 50, max 100)",
                        "default": 50
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_house_trades",
            "description": "Get recent stock trading disclosures from U.S. House Representatives. Shows what stocks house members are buying and selling. Use when user asks about House trades or congressional activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent trades to return (default 50, max 100)",
                        "default": 50
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_insider_trades",
            "description": "Get recent corporate insider trades (SEC Form 4 filings). Shows what company executives, directors, and major shareholders are buying and selling. Use when user asks about insider trades, insider buying/selling, or Form 4 filings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent trades to return (default 100, max 200)",
                        "default": 100
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_ticker_insider_activity",
            "description": "Search for all insider trading activity (Senate, House, and corporate insiders) for a specific stock ticker. Use when user asks about insider activity for a particular stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., 'AAPL', 'TSLA', 'NVDA')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum trades to return per source (default 50)",
                        "default": 50
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_insider_activity",
            "description": "Get insider trading activity for stocks in the user's portfolio. Shows which portfolio stocks have recent insider/congressional activity. REQUIRES get_portfolio to be called first to get the list of tickers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ticker symbols from user's portfolio"
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Look back this many days for activity (default 30)",
                        "default": 30
                    }
                },
                "required": ["tickers"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_insider_trading_statistics",
            "description": "Get quarterly aggregated insider trading statistics for a specific stock. Shows historical trends of insider buying vs selling over time, including buy/sell ratios, average transaction sizes, and patterns. Useful for analyzing long-term insider sentiment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., 'AAPL', 'TSLA')"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_insider_trades",
            "description": "Search insider trades with advanced filters. Filter by specific stock, insider CIK, company CIK, or transaction type (P-Purchase, S-Sale, A-Award, etc.). Useful for finding specific patterns or tracking particular insiders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol to filter by (optional)"
                    },
                    "reporting_cik": {
                        "type": "string",
                        "description": "CIK of the person reporting (insider) to filter by (optional)"
                    },
                    "company_cik": {
                        "type": "string",
                        "description": "CIK of the company to filter by (optional)"
                    },
                    "transaction_type": {
                        "type": "string",
                        "description": "Transaction type to filter by: P-Purchase, S-Sale, A-Award, M-Exempt, etc. (optional)",
                        "enum": ["P-Purchase", "S-Sale", "A-Award", "M-Exempt", "F-InKind", "G-Gift", "C-Conversion", "D-Return", "J-Other"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default 50, max 100)",
                        "default": 50
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination (default 0)",
                        "default": 0
                    }
                },
                "required": []
            }
        }
    }
]


# Global tools instance
insider_trading_tools = InsiderTradingTools()

