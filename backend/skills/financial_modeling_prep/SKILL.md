---
name: financial_modeling_prep
description: Stock fundamentals, financial statements, earnings calendar & history, ownership data, and analyst estimates from Financial Modeling Prep. Company profiles, earnings beat/miss rates, insider trading, institutional ownership, and more.
homepage: https://financialmodelingprep.com
metadata:
  emoji: "💹"
  category: stock_fundamentals
  is_system: true
  auto_on: true
  requires:
    env:
      - FMP_API_KEY
    bins: []
---

# Financial Modeling Prep (FMP) Skill

Stock fundamentals, financial statements, ownership data, and analyst estimates.

## Import Pattern

```python
from skills.financial_modeling_prep.scripts.company.profile import get_profile
from skills.financial_modeling_prep.scripts.company.executives import get_executives
from skills.financial_modeling_prep.scripts.financials.income_statement import get_income_statement
from skills.financial_modeling_prep.scripts.financials.balance_sheet import get_balance_sheet
from skills.financial_modeling_prep.scripts.financials.cash_flow import get_cash_flow
from skills.financial_modeling_prep.scripts.financials.key_metrics import get_key_metrics, get_key_metrics_ttm
from skills.financial_modeling_prep.scripts.financials.ratios import get_ratios
from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices
from skills.financial_modeling_prep.scripts.market.gainers import get_gainers, get_losers, get_actives
from skills.financial_modeling_prep.scripts.insider.insider_trading import get_insider_trading
from skills.financial_modeling_prep.scripts.insider.senate_trading import get_senate_trading
from skills.financial_modeling_prep.scripts.insider.house_trading import get_house_trading
from skills.financial_modeling_prep.scripts.ownership.institutional_ownership import get_institutional_ownership
from skills.financial_modeling_prep.scripts.analyst.price_target import get_price_targets, get_price_target_consensus
from skills.financial_modeling_prep.scripts.peers.stock_peers import get_stock_peers
from skills.financial_modeling_prep.scripts.peers.stock_screener import screen_stocks
from skills.financial_modeling_prep.scripts.search.search import search
from skills.financial_modeling_prep.scripts.etf.holdings import get_etf_holdings
from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import get_earnings_calendar, get_historical_earnings
```

## International Stocks (Indian Market / NSE / BSE)

FMP covers Indian stocks on both NSE and BSE. Use the `.NS` suffix for NSE and `.BO` suffix for BSE.

```python
# Indian stock examples
profile = get_profile("RELIANCE.NS")       # Reliance Industries (NSE)
income = get_income_statement("RELIANCE.NS", period="annual", limit=4)  # financials in INR
prices = get_historical_prices("TCS.NS", from_date="2025-01-01", to_date="2025-12-31")
results = search("infosys", exchange="NSE")  # search Indian stocks

# Common tickers: RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ICICIBANK.NS, WIPRO.NS
# BSE alternative: RELIANCE.BO, TCS.BO, etc.
```

If you're unsure of the exact ticker, use `search(query="company name")` — the results include `exchangeShortName` ("NSE" or "BSE") and the full symbol.

## Historical Prices

**Use this instead of yfinance for all historical price data.**

```python
data = get_historical_prices('QQQ', from_date='2025-01-01', to_date='2025-12-31')
if 'error' in data:
    raise RuntimeError(data['error'])
df = pd.DataFrame(data['prices'])
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)
```

For multiple symbols, call `get_historical_prices` in a loop and join on `date`.

Fields per bar: `date`, `open`, `high`, `low`, `close`, `adjClose`, `volume`, `changePercent`

## Company Information

```python
profile = get_profile(symbol="AAPL")
# Returns: companyName, sector, industry, mktCap, fullTimeEmployees, website, description, etc.

executives = get_executives(symbol="AAPL")
# Returns list of: name, title, pay, currencyPay
```

## Financial Statements

All accept `symbol`, `period` ("annual" or "quarter"), and `limit`.

```python
income = get_income_statement(symbol="AAPL", period="annual", limit=4)
# Key fields: revenue, netIncome, grossProfit, operatingIncome, eps, calendarYear

balance = get_balance_sheet(symbol="AAPL", period="quarter", limit=1)[0]
# Key fields: cashAndCashEquivalents, totalDebt, totalStockholdersEquity, totalAssets

cf = get_cash_flow(symbol="AAPL", period="annual", limit=1)[0]
# Key fields: operatingCashFlow, freeCashFlow, capitalExpenditure
```

## Key Metrics & Ratios

```python
metrics = get_key_metrics(symbol="AAPL", period="quarter", limit=1)[0]
# Key fields: peRatio, pbRatio, currentRatio, debtEquityRatio, roe, roa

ttm = get_key_metrics_ttm(symbol="AAPL")
# Key fields: revenueTTM, netIncomeTTM, peRatioTTM, roeTTM

ratios = get_ratios(symbol="AAPL", period="quarter", limit=1)[0]
# Key fields: quickRatio, grossProfitMargin, operatingProfitMargin, netProfitMargin
```

## Market Movers

```python
gainers = get_gainers()   # Top gainers
losers = get_losers()     # Top losers
actives = get_actives()   # Most active by volume
# Each returns list of: symbol, price, changesPercentage, volume
```

## Insider & Institutional Activity

```python
insider = get_insider_trading(symbol="AAPL", limit=20)
# Fields: reportingName, typeOfOwner, transactionType ("P - Purchase" / "S - Sale"),
#         securitiesTransacted, transactionPrice

senate = get_senate_trading(symbol="AAPL")
house = get_house_trading(symbol="AAPL")

institutional = get_institutional_ownership(symbol="AAPL", date="2025-09-30")
# Fields: investorName, shares, marketValue
```

## Analyst Estimates

```python
targets = get_price_targets(symbol="AAPL")
# Fields: analystName, publishedDate, priceTarget, rating

consensus = get_price_target_consensus(symbol="AAPL")
# Fields: targetHigh, targetLow, targetMean, targetMedian
```

## Stock Peers & Screener

```python
peers = get_stock_peers(symbol="AAPL")
# Returns list of ticker strings: ['MSFT', 'NVDA', 'ADBE', ...]

replacements = screen_stocks(
    sector="Technology", industry="Consumer Electronics",
    market_cap_more_than=100_000_000_000, limit=10,
)
# Returns list of: symbol, companyName, marketCap, sector, industry
```

## Stock Search

```python
results = search(query="artificial intelligence", limit=10)
# Returns list of: symbol, name, exchangeShortName
```

## ETF Holdings

```python
holdings = get_etf_holdings('QQQ')                       # current holdings
holdings_2024 = get_etf_holdings('SPY', date='2024-12-31')  # historical snapshot
# Fields: asset (ticker), name, weightPercentage (0.082 = 8.2%), sharesNumber, marketValue
```

## Earnings Calendar & History

**Use this for all earnings data — dates, EPS surprises, beat/miss rates, revenue estimates.**

```python
# Upcoming earnings for a date range (or today if no args)
upcoming = get_earnings_calendar(from_date='2026-05-01', to_date='2026-05-15')
# Fields: date, symbol, time (bmo/amc/dmh), eps, epsEstimated, revenue, revenueEstimated, fiscalDateEnding

# Historical earnings for a specific stock — beat/miss history & surprises
history = get_historical_earnings('AAPL')
# Fields: date, symbol, eps, epsEstimated, revenue, revenueEstimated
# Compute beat rate: compare eps > epsEstimated across quarters
```

### When to use earnings data

- **Any stock analysis** — always check upcoming earnings date and recent beat/miss history
- **Earnings plays** — pull beat rate, average surprise magnitude, revenue trends
- **Pre-earnings screening** — scan a date range, filter by estimate availability
- **Post-earnings review** — compare actual vs estimated to assess reaction

## Models Reference

See `financial_modeling_prep/models.py` for complete Pydantic schemas.

## When to Use This Skill

- User asks about a company's financials, revenue, earnings, or debt
- **Any stock analysis** — always pull upcoming earnings date and beat/miss history via `get_historical_earnings`
- **Earnings plays or earnings season** — use `get_earnings_calendar` for date ranges and `get_historical_earnings` for beat rates
- User wants insider trading or congressional trading data for a stock
- User asks for analyst price targets or institutional ownership
- User wants to screen for market movers (gainers, losers, most active)
- User asks "what do insiders think about X" or "is X undervalued"
- User wants to know what stocks an ETF holds (use `get_etf_holdings`)
- For price data, use `get_historical_prices` from this skill — do NOT use yfinance, polygon, or alpha_vantage
- **For earnings data, use `get_earnings_calendar` and `get_historical_earnings`** — do NOT scrape news or guess dates
