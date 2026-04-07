---
name: financial_modeling_prep
description: Stock fundamentals, financial statements, ownership data, and analyst estimates from Financial Modeling Prep. Company profiles, insider trading, institutional ownership, and more.
homepage: https://financialmodelingprep.com
metadata:
  emoji: "💹"
  category: stock_fundamentals
  is_system: true
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
```

## Historical Prices

**Use this instead of yfinance for all historical price data.**

```python
import pandas as pd
from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices

# Daily OHLCV — single symbol
data = get_historical_prices('QQQ', from_date='2025-01-01', to_date='2025-12-31')
if 'error' in data:
    raise RuntimeError(data['error'])

df = pd.DataFrame(data['prices'])
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)
print(df[['date', 'open', 'high', 'low', 'close', 'adjClose', 'volume']].tail())

# Multiple symbols — call in a loop
symbols = ['AAPL', 'MSFT', 'NVDA']
price_data = {}
for sym in symbols:
    d = get_historical_prices(sym, from_date='2025-01-01', to_date='2025-12-31')
    if 'error' not in d:
        df = pd.DataFrame(d['prices'])
        df['date'] = pd.to_datetime(df['date'])
        price_data[sym] = df.sort_values('date').set_index('date')['adjClose']

prices = pd.DataFrame(price_data)
returns = prices.pct_change().dropna()
```

Fields per bar: `date`, `open`, `high`, `low`, `close`, `adjClose`, `volume`, `changePercent`

## Company Information

```python
from skills.financial_modeling_prep.scripts.company.profile import get_profile
from skills.financial_modeling_prep.scripts.company.executives import get_executives

# Company profile
profile = get_profile(symbol="AAPL")
print(f"{profile['companyName']} ({profile['sector']})")
print(f"Market Cap: ${profile['mktCap']:,.0f}")
print(f"Employees: {profile['fullTimeEmployees']:,}")
print(f"Website: {profile['website']}")

# Executive team
executives = get_executives(symbol="AAPL")
for exec in executives[:5]:
    print(f"{exec['name']}: {exec['title']}")
```

## Financial Statements

```python
from skills.financial_modeling_prep.scripts.financials.income_statement import get_income_statement
from skills.financial_modeling_prep.scripts.financials.balance_sheet import get_balance_sheet
from skills.financial_modeling_prep.scripts.financials.cash_flow import get_cash_flow

# Income statement (annual or quarterly)
income = get_income_statement(symbol="AAPL", period="annual", limit=4)
for stmt in income:
    print(f"FY{stmt['calendarYear']}: Revenue ${stmt['revenue']:,.0f}, Net Income ${stmt['netIncome']:,.0f}")

# Balance sheet
balance = get_balance_sheet(symbol="AAPL", period="quarter", limit=1)[0]
print(f"Cash: ${balance['cashAndCashEquivalents']:,.0f}")
print(f"Total Debt: ${balance['totalDebt']:,.0f}")
print(f"Shareholders Equity: ${balance['totalStockholdersEquity']:,.0f}")

# Cash flow
cf = get_cash_flow(symbol="AAPL", period="annual", limit=1)[0]
print(f"Operating CF: ${cf['operatingCashFlow']:,.0f}")
print(f"Free Cash Flow: ${cf['freeCashFlow']:,.0f}")
```

## Key Metrics & Ratios

```python
from skills.financial_modeling_prep.scripts.financials.key_metrics import get_key_metrics, get_key_metrics_ttm
from skills.financial_modeling_prep.scripts.financials.ratios import get_ratios

# Key metrics
metrics = get_key_metrics(symbol="AAPL", period="quarter", limit=1)[0]
print(f"P/E Ratio: {metrics['peRatio']:.2f}")
print(f"P/B Ratio: {metrics['pbRatio']:.2f}")
print(f"Current Ratio: {metrics['currentRatio']:.2f}")
print(f"Debt/Equity: {metrics['debtEquityRatio']:.2f}")
print(f"ROE: {metrics['roe']:.2%}")
print(f"ROA: {metrics['roa']:.2%}")

# TTM metrics (trailing twelve months)
ttm = get_key_metrics_ttm(symbol="AAPL")
print(f"Revenue TTM: ${ttm['revenueTTM']:,.0f}")
print(f"Net Income TTM: ${ttm['netIncomeTTM']:,.0f}")

# Financial ratios
ratios = get_ratios(symbol="AAPL", period="quarter", limit=1)[0]
print(f"Quick Ratio: {ratios['quickRatio']:.2f}")
print(f"Gross Margin: {ratios['grossProfitMargin']:.2%}")
print(f"Operating Margin: {ratios['operatingProfitMargin']:.2%}")
print(f"Net Margin: {ratios['netProfitMargin']:.2%}")
```

## Market Movers

```python
from skills.financial_modeling_prep.scripts.market.gainers import get_gainers, get_losers, get_actives

# Top gainers
gainers = get_gainers()
for stock in gainers[:10]:
    print(f"{stock['symbol']}: ${stock['price']} (+{stock['changesPercentage']:.2f}%)")

# Top losers
losers = get_losers()

# Most active
actives = get_actives()
for stock in actives[:10]:
    print(f"{stock['symbol']}: Vol {stock['volume']:,}, ${stock['price']}")
```

## Insider & Institutional Activity

```python
from skills.financial_modeling_prep.scripts.insider.insider_trading import get_insider_trading
from skills.financial_modeling_prep.scripts.insider.senate_trading import get_senate_trading
from skills.financial_modeling_prep.scripts.insider.house_trading import get_house_trading
from skills.financial_modeling_prep.scripts.ownership.institutional_ownership import get_institutional_ownership

# Recent insider transactions
insider = get_insider_trading(symbol="AAPL", limit=20)
for tx in insider:
    action = "BUY" if tx['transactionType'] == "P - Purchase" else "SELL"
    print(f"{tx['reportingName']} ({tx['typeOfOwner']}): {action} {tx['securitiesTransacted']} shares @ ${tx['transactionPrice']}")

# Senate trading (politicians)
senate = get_senate_trading(symbol="AAPL")

# House trading
house = get_house_trading(symbol="AAPL")

# Institutional ownership (13F filings)
institutional = get_institutional_ownership(symbol="AAPL", date="2025-09-30")
for holder in institutional[:10]:
    print(f"{holder['investorName']}: {holder['shares']:,} shares (${holder['marketValue']:,.0f})")
```

## Analyst Estimates

```python
from skills.financial_modeling_prep.scripts.analyst.price_target import get_price_targets, get_price_target_consensus

# Individual analyst price targets
targets = get_price_targets(symbol="AAPL")
for target in targets[:5]:
    print(f"{target['analystName']} ({target['publishedDate']}): ${target['priceTarget']} - {target['rating']}")

# Consensus
consensus = get_price_target_consensus(symbol="AAPL")
print(f"Consensus: ${consensus['targetHigh']} high, ${consensus['targetLow']} low")
print(f"Mean: ${consensus['targetMean']}, Median: ${consensus['targetMedian']}")
```

## Stock Peers & Screener

```python
from skills.financial_modeling_prep.scripts.peers.stock_peers import get_stock_peers
from skills.financial_modeling_prep.scripts.peers.stock_screener import screen_stocks

# Get peer companies (same exchange, sector, similar market cap)
peers = get_stock_peers(symbol="AAPL")
print(peers)  # ['MSFT', 'NVDA', 'ADBE', 'INTC', 'CSCO', 'AVGO', 'TXN', 'QCOM', 'AMAT']

# Screen stocks by sector, industry, and market cap range
# Useful for finding TLH replacement securities
replacements = screen_stocks(
    sector="Technology",
    industry="Consumer Electronics",
    market_cap_more_than=100_000_000_000,  # $100B+
    limit=10,
)
for stock in replacements:
    print(f"{stock['symbol']}: {stock['companyName']} (${stock['marketCap']:,.0f})")
```

## Stock Search

```python
from skills.financial_modeling_prep.scripts.search.search import search

# Search by name or ticker
results = search(query="artificial intelligence", limit=10)
for stock in results:
    print(f"{stock['symbol']}: {stock['name']} ({stock['exchangeShortName']})")
```

## Common Workflows

### Value Screen

```python
def value_screen(symbols):
    for symbol in symbols:
        metrics = get_key_metrics(symbol=symbol, period="annual", limit=1)
        if not metrics:
            continue
        m = metrics[0]
        
        # Value criteria: P/E < 15, P/B < 2, positive ROE
        if m['peRatio'] and m['pbRatio'] and m['roe']:
            if m['peRatio'] < 15 and m['pbRatio'] < 2 and m['roe'] > 0.10:
                print(f"✓ {symbol}: P/E={m['peRatio']:.1f}, P/B={m['pbRatio']:.1f}, ROE={m['roe']:.1%}")

value_screen(["JPM", "BAC", "WFC", "C", "GS"])
```

### Growth Screen

```python
def growth_screen(symbol):
    income = get_income_statement(symbol=symbol, period="annual", limit=5)
    if len(income) < 5:
        return False
    
    # Calculate 4-year revenue CAGR
    old = income[-1]['revenue']
    new = income[0]['revenue']
    cagr = (new / old) ** (1/4) - 1
    
    if cagr > 0.15:  # 15%+ annual growth
        print(f"✓ {symbol}: {cagr:.1%} revenue CAGR")
        return True
    return False
```

### Check for Insider Buying

```python
def insider_buying_signal(symbol):
    trades = get_insider_trading(symbol=symbol, limit=50)
    buys = [t for t in trades if t['transactionType'] == "P - Purchase"]
    sells = [t for t in trades if t['transactionType'] == "S - Sale"]
    
    # Net buying signal
    buy_shares = sum(t['securitiesTransacted'] for t in buys)
    sell_shares = sum(t['securitiesTransacted'] for t in sells)
    
    if buy_shares > sell_shares * 2:
        print(f"🟢 {symbol}: Heavy insider buying ({buy_shares:,} vs {sell_shares:,})")
        return True
    return False
```

## Models Reference

See `financial_modeling_prep/models.py` for complete Pydantic schemas.

## When to Use This Skill

- User asks about a company's financials, revenue, earnings, or debt
- User wants insider trading or congressional trading data for a stock
- User asks for analyst price targets or institutional ownership
- User wants to screen for market movers (gainers, losers, most active)
- User asks "what do insiders think about X" or "is X undervalued"
- Combine with `polygon_io` for price data and `tradingview` for technical signals
