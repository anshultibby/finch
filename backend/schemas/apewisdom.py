"""
ApeWisdom API Pydantic models for Reddit stock sentiment data
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StockMention(BaseModel):
    """Individual stock mention data from ApeWisdom"""
    ticker: str = Field(description="Stock ticker symbol")
    name: Optional[str] = Field(None, description="Company name")
    mentions: int = Field(description="Number of mentions")
    upvotes: int = Field(description="Total upvotes")
    rank: int = Field(description="Rank by mentions")
    mentions_24h_ago: Optional[int] = Field(None, description="Mentions 24 hours ago")
    rank_24h_ago: Optional[int] = Field(None, description="Rank 24 hours ago")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "GME",
                "name": "GameStop Corp.",
                "mentions": 1523,
                "upvotes": 8542,
                "rank": 1,
                "mentions_24h_ago": 892,
                "rank_24h_ago": 3
            }
        }


class RedditSentiment(BaseModel):
    """Aggregated Reddit sentiment for stocks"""
    success: bool = True
    mentions: List[StockMention]
    total_tickers: int
    data_source: str = "ApeWisdom - Reddit Stock Mentions"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "mentions": [
                    {
                        "ticker": "GME",
                        "name": "GameStop Corp.",
                        "mentions": 1523,
                        "upvotes": 8542,
                        "rank": 1
                    }
                ],
                "total_tickers": 50,
                "data_source": "ApeWisdom - Reddit Stock Mentions",
                "timestamp": "2025-10-27T12:00:00Z"
            }
        }


class TickerDetails(BaseModel):
    """Detailed information for a specific ticker"""
    ticker: str
    name: Optional[str] = None
    mentions: int
    upvotes: int
    rank: int
    mentions_24h_ago: Optional[int] = None
    rank_24h_ago: Optional[int] = None
    comments: Optional[List[dict]] = None  # Top comments mentioning the ticker
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "TSLA",
                "name": "Tesla Inc.",
                "mentions": 892,
                "upvotes": 4521,
                "rank": 2,
                "mentions_24h_ago": 654,
                "rank_24h_ago": 4
            }
        }


class TrendingStocksResponse(BaseModel):
    """Response for trending stocks from Reddit"""
    success: bool
    trending_stocks: List[StockMention]
    message: str
    data_source: str = "ApeWisdom"
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "trending_stocks": [
                    {
                        "ticker": "GME",
                        "name": "GameStop Corp.",
                        "mentions": 1523,
                        "upvotes": 8542,
                        "rank": 1
                    }
                ],
                "message": "Found 10 trending stocks on Reddit",
                "data_source": "ApeWisdom"
            }
        }

