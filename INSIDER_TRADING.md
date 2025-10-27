# Insider Trading & Congressional Trading Features

This document describes the insider trading and congressional trading features integrated into Finch using the Financial Modeling Prep (FMP) API.

## Overview

Finch now provides comprehensive insider trading intelligence, including:

1. **Senate Trading Disclosures** - Track what U.S. Senators are buying and selling
2. **House Trading Disclosures** - Track what U.S. House Representatives are buying and selling  
3. **Corporate Insider Trades** - Track SEC Form 4 filings from company executives, directors, and major shareholders
4. **Portfolio Monitoring** - Get alerts for insider activity in your portfolio stocks

## Features

### 1. Recent High-Profile Trades

Get the latest trading activity from politicians and corporate insiders:

```
User: "What stocks are senators buying?"
User: "Show me recent congressional trades"
User: "What are the latest insider trades?"
```

The bot will show:
- Who made the trade (politician or insider name)
- What stock/asset was traded
- Transaction type (Purchase/Sale)
- Amount/value of the transaction
- When the transaction occurred
- Links to official disclosures

### 2. Ticker-Specific Insider Activity

Search for all insider activity on a specific stock:

```
User: "What insider activity is happening with NVDA?"
User: "Show me insider trades for Apple"
User: "Are any politicians trading Tesla?"
```

The bot will aggregate:
- Corporate insider trades (executives, directors)
- Senate trades
- House trades
- Summary statistics (total purchases vs sales)

### 3. Portfolio Insider Monitoring

Monitor insider activity across your entire portfolio:

```
User: "What insider activity is happening in my portfolio?"
User: "Are there any insider trades in stocks I own?"
User: "Show me congressional trades for my holdings"
```

The bot will:
1. Fetch your current portfolio holdings
2. Check each ticker for recent insider activity
3. Highlight stocks with significant activity
4. Show summary stats per ticker

### 4. Combining with Other Features

You can combine insider trading with Reddit sentiment:

```
User: "What's trending on Reddit and what are insiders buying?"
User: "Show me insider activity for the top 5 Reddit stocks"
User: "Are politicians buying any of the stocks Reddit is talking about?"
```

## API Configuration

### Getting Your FMP API Key

1. Go to [Financial Modeling Prep](https://site.financialmodelingprep.com/developer/docs)
2. Sign up for a free account (or upgrade for higher rate limits)
3. Get your API key from the dashboard
4. Add it to your `.env` file:

```bash
FMP_API_KEY=your_fmp_api_key_here
```

### API Rate Limits & Availability

**✅ Free Tier Endpoints (250 requests/day):**

All three endpoints support **symbol filtering** via query parameter:

1. **`/stable/insider-trading/latest?symbol=AAPL`** - Corporate insider trades (SEC Form 4)
   - Company executives, directors, and 10%+ shareholders
   - Filter by ticker symbol
   
2. **`/stable/senate-latest?symbol=AAPL`** - Latest Senate financial disclosures
   - Recent trades from U.S. Senators
   - Filter by ticker symbol
   
3. **`/stable/house-latest?symbol=AAPL`** - Latest House financial disclosures
   - Recent trades from U.S. House Representatives
   - Filter by ticker symbol

**💰 Premium Endpoints (Paid Plans):**
- Historical data beyond latest trades
- Advanced filtering options (date ranges, amounts, etc.)
- Higher rate limits for frequent polling
- Additional congressional data endpoints

**The free tier provides full functionality for:**
- ✅ Monitoring corporate insider activity
- ✅ Tracking congressional trading activity  
- ✅ Portfolio-specific insider analysis with symbol filtering
- ✅ Real-time latest disclosures

**You'll need a paid plan for:**
- Historical insider trading data beyond recent trades
- Higher API rate limits (>250 requests/day)
- Advanced analytics and bulk data access

## Tool Descriptions

### Available Tools

1. **`get_recent_senate_trades`**
   - Fetches recent Senate trading disclosures
   - Shows senator name, office, ticker, transaction details
   - Configurable limit (default 50, max 100)

2. **`get_recent_house_trades`**
   - Fetches recent House trading disclosures
   - Shows representative name, district, ticker, transaction details
   - Configurable limit (default 50, max 100)

3. **`get_recent_insider_trades`**
   - Fetches recent corporate insider trades (SEC Form 4)
   - Shows insider name, title, transaction details, value
   - Configurable limit (default 100, max 200)

4. **`search_ticker_insider_activity`**
   - Searches all insider activity for a specific ticker
   - Aggregates Senate, House, and corporate insider trades
   - Returns comprehensive summary statistics

5. **`get_portfolio_insider_activity`**
   - Monitors insider activity across multiple tickers
   - Filters to recent activity (configurable days back)
   - Identifies which portfolio stocks have activity
   - Requires portfolio data from `get_portfolio` first

## Data Sources

### Congressional Trading Data

- **Source**: Senate and House financial disclosure databases
- **Update Frequency**: Real-time as disclosures are filed
- **Disclosure Requirements**: 
  - Must be filed within 30-45 days of transaction
  - Applies to trades over $1,000
  - Includes spouse and dependent children

### Corporate Insider Trading Data

- **Source**: SEC Form 4 filings (EDGAR database)
- **Update Frequency**: Real-time as forms are filed
- **Filing Requirements**:
  - Form 4 must be filed within 2 business days
  - Applies to officers, directors, and 10%+ shareholders
  - Includes open market purchases, sales, option exercises

## Example Queries

### Basic Queries

```
"What stocks are senators buying?"
"Show me the latest House trades"
"What are corporate insiders doing?"
```

### Ticker-Specific

```
"What insider activity is there for NVDA?"
"Are any politicians trading Apple?"
"Show me insider trades for Microsoft in the last 30 days"
```

### Portfolio-Focused

```
"What insider activity is in my portfolio?"
"Show me insider trades for my holdings"
"Are there any congressional trades in stocks I own?"
```

### Complex Analysis

```
"Compare Reddit sentiment and insider activity for TSLA"
"Which of my portfolio stocks have both insider buying and Reddit hype?"
"Show me stocks that senators are buying that are also trending on wallstreetbets"
```

## Understanding the Data

### Transaction Types

- **Purchase/Acquisition** - Insider is buying shares (generally bullish)
- **Sale/Disposition** - Insider is selling shares (can be neutral or bearish)
- **Exercise** - Insider exercising stock options
- **Grant** - Company granting shares (usually compensation)

### Amount Ranges (Congressional)

Congressional disclosures use ranges instead of exact amounts:
- $1,001 - $15,000
- $15,001 - $50,000
- $50,001 - $100,000
- $100,001 - $250,000
- $250,001 - $500,000
- $500,001 - $1,000,000
- Over $1,000,000

### Interpreting Insider Activity

**Bullish Signals:**
- Multiple insiders buying (especially unusual)
- C-level executives buying
- Purchases significantly larger than normal
- Insider buying during market downturns

**Neutral/Expected:**
- Routine option exercises and sales
- Sales to cover taxes
- Diversification sales (large % of holdings)
- Planned 10b5-1 trading programs

**Bearish Signals:**
- Multiple insiders selling (especially unusual)
- C-level executives selling significantly
- Selling despite positive company news
- Insider selling before bad news

## Privacy & Security

- All insider trading data is public information
- Congressional trading disclosures are mandated by the STOCK Act
- Corporate insider trades are mandated by SEC regulations
- No private information is accessed or stored
- Your portfolio data remains secure and is only used for matching

## Technical Details

### Data Models

See `backend/models/insider_trading.py` for full data structures:
- `SenateTrade` - Senate trading disclosure
- `HouseTrade` - House trading disclosure
- `InsiderTrade` - Corporate insider trade
- `InsiderTradingResponse` - Generic response wrapper

### Tools Implementation

See `backend/modules/insider_trading_tools.py` for implementation details:
- Async HTTP client for FMP API
- Error handling and retry logic
- Data parsing and enrichment
- Aggregation and filtering

### Agent Integration

The tools are integrated into the ChatAgent (`backend/agent.py`):
- Tools are always available (no auth required)
- Automatically called based on user intent
- Can be chained with portfolio tools
- Results formatted for conversational response

## Troubleshooting

### API Key Issues

If you see errors about FMP_API_KEY:
1. Make sure you've added it to your `.env` file
2. Restart the backend server
3. Check that the key is valid in the FMP dashboard

### Rate Limit Errors

If you hit rate limits:
1. Check your FMP dashboard for usage
2. Consider upgrading your plan
3. Reduce the frequency of requests
4. Use smaller limit values in queries

### No Data Returned

If queries return no data:
1. Check that the ticker symbol is correct
2. Try a more popular/larger ticker
3. Some stocks may have no recent insider activity
4. Congressional trades are only filed periodically

### Connection Errors

If you see HTTP errors:
1. Check your internet connection
2. Verify FMP API is operational
3. Check for firewall/proxy issues
4. Try again (API may be temporarily unavailable)

## Future Enhancements

Potential future features:
- **Filtering**: Filter by transaction type, amount, date range
- **Alerts**: Real-time alerts for insider activity in portfolio
- **Analysis**: Aggregate statistics and trends
- **Visualization**: Charts showing insider sentiment over time
- **Historical**: Track insider activity history for tickers
- **Correlation**: Correlate insider activity with price movements

## Resources

- [FMP API Documentation](https://site.financialmodelingprep.com/developer/docs)
- [SEC Form 4 Overview](https://www.sec.gov/files/form4data.pdf)
- [STOCK Act Congressional Trading Rules](https://www.congress.gov/bill/112th-congress/senate-bill/2038)
- [Understanding Insider Trading Signals](https://www.investopedia.com/articles/stocks/11/corporate-insiders.asp)

