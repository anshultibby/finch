"""
ApeWisdom API tools for Reddit stock sentiment analysis

ApeWisdom tracks stock mentions across Reddit communities including:
- r/wallstreetbets
- r/stocks
- r/investing
- r/stockmarket
- And many more
"""
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
from models.apewisdom import (
    StockMention, RedditSentiment, TickerDetails, TrendingStocksResponse
)


class ApeWisdomTools:
    """
    Tools for fetching Reddit stock sentiment data from ApeWisdom API
    
    ApeWisdom aggregates stock mentions and sentiment from multiple
    Reddit stock communities.
    """
    
    BASE_URL = "https://apewisdom.io/api/v1.0"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_trending_stocks(
        self, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get trending stocks from Reddit communities (stocks only, no crypto)
        
        Args:
            limit: Number of stocks to return (default 10, max 50)
            
        Returns:
            Dictionary with trending stocks data
        """
        try:
            print(f"🔍 Fetching top {limit} trending stocks from Reddit...", flush=True)
            
            # ApeWisdom API endpoint - using all-stocks filter to exclude crypto
            url = f"{self.BASE_URL}/filter/all-stocks"
            params = {"page": 1}
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse results
            results = data.get("results", [])[:limit]
            
            if not results:
                return {
                    "success": False,
                    "message": "No trending stocks found on Reddit"
                }
            
            # Convert to our models
            stock_mentions = []
            for item in results:
                try:
                    mention = StockMention(
                        ticker=item.get("ticker", ""),
                        name=item.get("name"),
                        mentions=item.get("mentions", 0),
                        upvotes=item.get("upvotes", 0),
                        rank=item.get("rank", 0),
                        mentions_24h_ago=item.get("mentions_24h_ago"),
                        rank_24h_ago=item.get("rank_24h_ago")
                    )
                    stock_mentions.append(mention)
                except Exception as e:
                    print(f"⚠️ Error parsing stock mention: {e}", flush=True)
                    continue
            
            print(f"✅ Found {len(stock_mentions)} trending stocks", flush=True)
            
            # Build response
            sentiment = RedditSentiment(
                success=True,
                mentions=stock_mentions,
                total_tickers=len(stock_mentions),
                data_source="ApeWisdom - Reddit Stock Mentions"
            )
            
            return sentiment.model_dump()
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP error fetching trending stocks: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Failed to fetch Reddit data: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Error fetching trending stocks: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def get_ticker_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        Get Reddit sentiment for a specific stock ticker
        
        Args:
            ticker: Stock ticker symbol (e.g., 'GME', 'TSLA')
            
        Returns:
            Dictionary with ticker sentiment data
        """
        try:
            print(f"🔍 Fetching Reddit sentiment for {ticker}...", flush=True)
            
            # First get all stocks and find the specific one
            url = f"{self.BASE_URL}/filter/all-stocks"
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            # Find the ticker
            ticker_data = None
            for item in results:
                if item.get("ticker", "").upper() == ticker.upper():
                    ticker_data = item
                    break
            
            if not ticker_data:
                return {
                    "success": False,
                    "message": f"Ticker {ticker} not found in current Reddit trending data. It may not be actively discussed right now."
                }
            
            # Parse the data
            details = TickerDetails(
                ticker=ticker_data.get("ticker", ticker),
                name=ticker_data.get("name"),
                mentions=ticker_data.get("mentions", 0),
                upvotes=ticker_data.get("upvotes", 0),
                rank=ticker_data.get("rank", 0),
                mentions_24h_ago=ticker_data.get("mentions_24h_ago"),
                rank_24h_ago=ticker_data.get("rank_24h_ago")
            )
            
            print(f"✅ Found sentiment for {ticker}: {details.mentions} mentions, rank #{details.rank}", flush=True)
            
            return {
                "success": True,
                "ticker_details": details.model_dump(),
                "message": f"{ticker} has {details.mentions} mentions on Reddit (rank #{details.rank})"
            }
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP error fetching ticker sentiment: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Failed to fetch Reddit data: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Error fetching ticker sentiment: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def compare_tickers_sentiment(
        self, 
        tickers: List[str]
    ) -> Dict[str, Any]:
        """
        Compare Reddit sentiment for multiple tickers
        
        Args:
            tickers: List of ticker symbols to compare
            
        Returns:
            Dictionary with comparison data
        """
        try:
            print(f"🔍 Comparing Reddit sentiment for: {', '.join(tickers)}", flush=True)
            
            # Get all stocks
            url = f"{self.BASE_URL}/filter/all-stocks"
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            # Find all requested tickers
            found_tickers = []
            not_found = []
            
            for ticker in tickers:
                ticker_data = None
                for item in results:
                    if item.get("ticker", "").upper() == ticker.upper():
                        ticker_data = item
                        break
                
                if ticker_data:
                    mention = StockMention(
                        ticker=ticker_data.get("ticker", ticker),
                        name=ticker_data.get("name"),
                        mentions=ticker_data.get("mentions", 0),
                        upvotes=ticker_data.get("upvotes", 0),
                        rank=ticker_data.get("rank", 0),
                        mentions_24h_ago=ticker_data.get("mentions_24h_ago"),
                        rank_24h_ago=ticker_data.get("rank_24h_ago")
                    )
                    found_tickers.append(mention)
                else:
                    not_found.append(ticker)
            
            if not found_tickers:
                return {
                    "success": False,
                    "message": f"None of the tickers were found in current Reddit trending data: {', '.join(tickers)}"
                }
            
            # Sort by mentions (descending)
            found_tickers.sort(key=lambda x: x.mentions, reverse=True)
            
            print(f"✅ Found {len(found_tickers)} tickers, {len(not_found)} not found", flush=True)
            
            return {
                "success": True,
                "comparison": [t.model_dump() for t in found_tickers],
                "not_found": not_found,
                "message": f"Compared {len(found_tickers)} tickers. Most mentioned: {found_tickers[0].ticker} ({found_tickers[0].mentions} mentions)"
            }
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP error comparing tickers: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Failed to fetch Reddit data: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Error comparing tickers: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Tool definitions for LiteLLM
APEWISDOM_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_reddit_trending_stocks",
            "description": "Get the most talked about and trending stocks from Reddit communities like r/wallstreetbets, r/stocks, and r/investing. Shows current mentions, upvotes, and ranking. Use this when user asks about what's popular/trending on Reddit, what stocks Reddit is talking about, or meme stocks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of trending stocks to return (default 10, max 50)",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_reddit_ticker_sentiment",
            "description": "Get Reddit sentiment and mentions for a specific stock ticker. Shows how many times it's been mentioned, upvotes, rank, and 24h change. Use this when user asks about Reddit sentiment for a specific stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., 'GME', 'TSLA', 'AAPL')"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_reddit_sentiment",
            "description": "Compare Reddit sentiment for multiple stock tickers. Shows which stocks are more popular on Reddit. Use this when user wants to compare multiple stocks or asks which one Reddit prefers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ticker symbols to compare (e.g., ['GME', 'AMC', 'TSLA'])"
                    }
                },
                "required": ["tickers"]
            }
        }
    }
]


# Global tools instance
apewisdom_tools = ApeWisdomTools()

