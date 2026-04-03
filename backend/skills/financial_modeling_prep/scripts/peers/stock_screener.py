"""Screen stocks by sector, industry, market cap, and other criteria."""
from ..api import fmp


def screen_stocks(
    sector: str = None,
    industry: str = None,
    market_cap_more_than: int = None,
    market_cap_lower_than: int = None,
    beta_more_than: float = None,
    beta_lower_than: float = None,
    dividend_more_than: float = None,
    dividend_lower_than: float = None,
    price_more_than: float = None,
    price_lower_than: float = None,
    volume_more_than: int = None,
    country: str = None,
    exchange: str = None,
    limit: int = 20,
):
    """
    Screen stocks by fundamental criteria. Useful for finding replacement
    securities in the same sector/industry with similar market cap.

    Args:
        sector: e.g. 'Technology', 'Healthcare', 'Financial Services', 'Consumer Cyclical',
                'Industrials', 'Energy', 'Consumer Defensive', 'Real Estate',
                'Basic Materials', 'Communication Services', 'Utilities'
        industry: e.g. 'Software—Infrastructure', 'Banks—Diversified', 'Semiconductors'
        market_cap_more_than: Min market cap in dollars
        market_cap_lower_than: Max market cap in dollars
        beta_more_than: Min beta (volatility relative to market)
        beta_lower_than: Max beta
        dividend_more_than: Min dividend yield
        dividend_lower_than: Max dividend yield
        price_more_than: Min share price
        price_lower_than: Max share price
        volume_more_than: Min average volume
        country: e.g. 'US', 'GB', 'JP'
        exchange: e.g. 'NYSE', 'NASDAQ'
        limit: Max results (default 20)

    Returns:
        list[dict]: Matching stocks with symbol, companyName, marketCap, sector, industry, price, beta
    """
    params = {"limit": limit}
    if sector:
        params["sector"] = sector
    if industry:
        params["industry"] = industry
    if market_cap_more_than is not None:
        params["marketCapMoreThan"] = market_cap_more_than
    if market_cap_lower_than is not None:
        params["marketCapLowerThan"] = market_cap_lower_than
    if beta_more_than is not None:
        params["betaMoreThan"] = beta_more_than
    if beta_lower_than is not None:
        params["betaLowerThan"] = beta_lower_than
    if dividend_more_than is not None:
        params["dividendMoreThan"] = dividend_more_than
    if dividend_lower_than is not None:
        params["dividendLowerThan"] = dividend_lower_than
    if price_more_than is not None:
        params["priceMoreThan"] = price_more_than
    if price_lower_than is not None:
        params["priceLowerThan"] = price_lower_than
    if volume_more_than is not None:
        params["volumeMoreThan"] = volume_more_than
    if country:
        params["country"] = country
    if exchange:
        params["exchange"] = exchange

    return fmp("/stock-screener", params)
