# Custom ETF Builder - Quick Start Guide

## What You Can Do

Build custom stock portfolios (ETFs) with different weighting strategies, then backtest and visualize their historical performance.

## Quick Examples

### 1. Simple ETF
```
User: "Build an equal-weight ETF with AAPL, MSFT, and GOOGL"
```
Agent will create a portfolio with 33.33% allocation to each stock.

### 2. After Screening
```
User: "Find high-growth tech stocks with revenue growth > 20% and build a portfolio"
```
Agent will:
1. Screen stocks using code generation
2. Build custom ETF with results
3. Show allocation table

### 3. Full Workflow with Backtest
```
User: "Create a dividend ETF from top dividend aristocrats and show me 5-year performance"
```
Agent will:
1. Screen for dividend aristocrats
2. Build custom ETF
3. Generate and run backtest code
4. Visualize performance chart
5. Provide insights and recommendations

### 4. Compare Strategies
```
User: "Compare equal-weight vs market-cap weighting for FAANG stocks"
```
Agent will:
1. Build both versions
2. Backtest both
3. Show side-by-side comparison
4. Explain which performed better and why

## Weighting Methods

### Equal Weight
- Each stock gets the same allocation
- Example: 5 stocks = 20% each
- **Best for:** Diversification, giving all picks equal importance
- **Use when:** You believe all stocks have similar potential

### Market Cap
- Stocks weighted by market capitalization
- Larger companies get higher allocation
- **Best for:** Following market dynamics, institutional approach
- **Use when:** You want natural market-weighted exposure

## The Complete Flow

```
1. SCREEN STOCKS
   └─> Use financial data to find candidates
   
2. BUILD ETF
   └─> Create weighted portfolio from stocks
   
3. BACKTEST
   └─> Test historical performance
   
4. VISUALIZE
   └─> Chart portfolio value over time
   
5. INSIGHTS
   └─> Analyze and recommend next steps
```

## Example Prompts

### Thematic Portfolios
- "Build an AI stocks ETF"
- "Create a clean energy portfolio"
- "Build a dividend aristocrats ETF"
- "Make a small-cap growth portfolio"

### Value Investing
- "Find undervalued stocks with P/E < 15 and build a portfolio"
- "Create a Benjamin Graham style value ETF"
- "Build a deep value portfolio with P/B < 1"

### Growth Investing
- "Build a high-growth tech portfolio with revenue growth > 30%"
- "Create a momentum ETF with stocks near 52-week highs"
- "Find hypergrowth stocks and build an equal-weight ETF"

### Strategy Testing
- "Compare equal-weight vs market-cap for tech stocks"
- "How would a dividend ETF have performed during 2020-2024?"
- "Test a low volatility portfolio vs S&P 500"

## What the Agent Does

### Step 1: Stock Screening (if needed)
Generates and runs Python code to filter stocks by your criteria using FMP API data.

**Example criteria:**
- P/E ratio < 20
- ROE > 15%
- Revenue growth > 10%
- Dividend yield > 3%
- Market cap > $1B

### Step 2: Portfolio Construction
Calls `build_custom_etf` tool which:
- Fetches current market data for all tickers
- Calculates weights (equal or market-cap based)
- Returns portfolio composition

**You see:**
```
✓ Built "Tech Leaders ETF" with 10 stocks

| Ticker | Name                   | Weight | Price    | Market Cap |
|--------|------------------------|--------|----------|------------|
| AAPL   | Apple Inc.            | 10%    | $189.50  | $2.95T     |
| MSFT   | Microsoft Corporation  | 10%    | $378.91  | $2.82T     |
...
```

### Step 3: Backtesting
Generates Python code that:
- Fetches historical daily prices for each stock
- Calculates daily portfolio value based on weights
- Computes performance metrics

**You see:**
```
✓ Backtest Complete!

📊 Performance (Dec 2023 - Dec 2024):
- Initial Value: $10,000
- Final Value: $14,520
- Total Return: +45.2%
- Annualized Return: +42.8%
- Max Drawdown: -12.3%
```

### Step 4: Visualization
Creates an interactive chart showing portfolio growth over time.

**Features:**
- Zoomable, interactive line chart
- Hover to see exact values
- Trendline showing growth trajectory
- Clean, modern design

### Step 5: Analysis & Recommendations
Agent provides:
- Performance summary
- Comparison to benchmarks (S&P 500, etc.)
- Top/bottom performers in the portfolio
- Risk analysis (volatility, drawdown)
- Suggestions for next steps

## Behind the Scenes

### Data Source
All market data comes from Financial Modeling Prep (FMP) API:
- Real-time quotes for current prices
- Historical daily prices for backtesting
- Fundamental data for screening

### Performance Metrics

**Total Return:** `(Final Value - Initial Value) / Initial Value × 100`

**Annualized Return (CAGR):** `((Final Value / Initial Value)^(1/Years) - 1) × 100`

**Max Drawdown:** `(Peak Value - Trough Value) / Peak Value × 100`

### Time Periods
Common backtest periods:
- 1 Year: Quick performance check
- 3 Years: Medium-term view
- 5 Years: Long-term strategy test
- 10 Years: Full market cycle

## Tips for Best Results

### 1. Start with Clear Criteria
❌ "Find good stocks"
✅ "Find stocks with P/E < 20, ROE > 15%, and revenue growth > 10%"

### 2. Consider Market Conditions
- Test portfolios across different time periods
- Include bear markets in backtest (e.g., 2022)
- Check how portfolio performs in volatility

### 3. Compare to Benchmarks
Always ask to compare vs:
- S&P 500 (SPY) for general market
- Nasdaq (QQQ) for tech stocks
- Sector ETFs for specific sectors

### 4. Try Both Weighting Methods
Equal-weight and market-cap can perform very differently:
- Equal-weight: Better when small caps outperform
- Market-cap: Better when large caps lead

### 5. Understand Concentration Risk
Check your sector exposure:
- "What sectors am I concentrated in?"
- "Show me sector breakdown"
- "Is my portfolio too tech-heavy?"

## Advanced Usage

### Rebalancing Analysis
```
"How would quarterly rebalancing affect my ETF performance?"
```

### Sector Analysis
```
"Show me sector breakdown of my ETF and compare to S&P 500"
```

### Risk-Adjusted Returns
```
"Calculate Sharpe ratio for my portfolio"
```

### Correlation Analysis
```
"How correlated are the stocks in my ETF?"
```

### What-If Scenarios
```
"What if I had built this ETF in 2020? How would it have done?"
```

## Troubleshooting

### "Couldn't find ticker X"
- Check spelling (tickers are case-sensitive)
- Verify ticker is still active (not delisted)
- Try different ticker symbol (some companies have multiple)

### "Not enough historical data"
- Some stocks don't have long histories
- Try shorter time period
- Remove newer stocks from portfolio

### "Backtest shows strange results"
- Check for stock splits (FMP adjusts for these)
- Verify date range is valid (no weekends/holidays)
- Look for data gaps or missing dates

## Next Steps

After building your first ETF:
1. Try different stock selections
2. Compare weighting strategies
3. Test various time periods
4. Add benchmark comparisons
5. Explore different themes/sectors

## Documentation

- **Full Guide:** `backend/modules/tools/CUSTOM_ETF_BUILDER.md`
- **Technical Details:** `backend/modules/tools/etf_builder_tools.py`
- **Examples:** `backend/modules/tools/examples/etf_builder_example.py`
- **Tests:** `backend/tests/test_etf_builder.py`

## Support

Having issues? Check:
1. FMP_API_KEY is set correctly
2. Tickers are valid and active
3. Date ranges are reasonable
4. Backend logs for detailed errors

Happy ETF building! 🚀

