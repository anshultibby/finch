---
name: indian_stocks
description: Indian (NSE/BSE) stock market data via indianapi.in — fundamentals, quarterly financials, key ratios, analyst price targets & consensus, shareholding patterns, corporate actions, peers, market screeners (trending/most-active/52-week/price-shockers), market news, IPOs, mutual funds, and MCX commodities. Use for any Indian-listed company (e.g. Reliance, MTAR Technologies, Shaily Engineering). For US stocks use financial_modeling_prep instead.
metadata:
  emoji: "🇮🇳"
  category: market_data
  is_system: true
  requires:
    env:
      - INDIAN_API_KEY
---

# Indian Stock Market Skill (indianapi.in)

Data for **NSE/BSE-listed Indian equities**, mutual funds, IPOs and MCX
commodities. This is the right skill whenever the question is about an Indian
company or the Indian market. (FMP works for `.NS` *prices* but lacks quarterly
results, ratios, shareholding, and analyst targets for Indian small/mid-caps —
this skill fills that gap.)

- **Companies are addressed by NAME**, not ticker — `"MTAR Technologies"`,
  `"Reliance"`, `"Shaily Engineering"`. The `/stock` response echoes the
  BSE/NSE codes under `companyProfile`. Use `search_industry(...)` if you're
  unsure of the exact name.
- All amounts are **INR (₹)**; timestamps are **IST**.
- Base host: `https://stock.indianapi.in`, auth header `X-API-Key`. The key is
  injected as the `INDIAN_API_KEY` env var by the backend — never print it.

## Start here — one call does most of the job

```python
from skills.indian_stocks.scripts.stocks import stock

d = stock("MTAR Technologies")
```

`stock(name)` returns the **whole mosaic** in a single request — for the common
"analyse this stock after its Q4 result, should I hold/add/trim?" question you
usually need nothing else:

| Field | What's in it |
|-------|--------------|
| `companyName`, `industry` | basics |
| `companyProfile` | description, `peerCompanyList`, `officers`, `exchangeCodeBse`, `exchangeCodeNse` |
| `currentPrice` | `{BSE, NSE}` |
| `percentChange`, `yearHigh`, `yearLow` | quote context |
| `stockTechnicalData` | moving averages / technicals |
| **`financials`** | **list of ~18 periods** — each has `FiscalYear`, `EndDate`, `Type`, `fiscalPeriodNumber`, and `stockFinancialMap` with `INC` (P&L), `BAL` (balance sheet), `CAS` (cash flow) line items (`displayName`, `key`, `value`, `qoQComp`, `yqoQComp` = QoQ / YoY comparison). **This already includes quarterly results.** |
| **`keyMetrics`** | grouped ratios: `margins`, `valuation`, `growth`, `persharedata`, `financialstrength`, `mgmtEffectiveness`, `priceandVolume`, `incomeStatement` |
| `analystView`, **`recosBar`** | analyst recommendations + consensus rating (`meanValue`, `noOfRecommendations`, `tickerRatingValue`) |
| `riskMeter` | risk category + stdDev |
| **`shareholding`** | list of categories (Promoter, FII, DII, Public…) each with a `holdingDate → percentage` time series |
| `stockCorporateActionData` | `bonus`, `dividend`, `rights`, `splits`, `annualGeneralMeeting`, `boardMeetings` |

```python
# Pull the latest quarterly P&L straight out of the embedded financials:
fin = d["financials"]                      # newest period first
latest = fin[0]
inc = latest["stockFinancialMap"]["INC"]   # list of {displayName, key, value, qoQComp, yqoQComp}
promoter = next(c for c in d["shareholding"] if c["displayName"] == "Promoter")
target = stock_target  # see below for the dedicated analyst-target endpoint
```

## Endpoint reference

Import any of these:

```python
from skills.indian_stocks.scripts.stocks import (
    stock, target_price, forecasts, corporate_actions,        # company
    trending, fifty_two_week_high_low, nse_most_active,        # screeners
    bse_most_active, price_shockers, search_industry,
    news, ipo,                                                 # news / ipo
    mutual_funds, mutual_fund_details, search_mutual_fund,     # mutual funds
    commodities,                                               # commodities
)
```

### ✅ Working (verified on the free plan)

| Function | Endpoint | Args | Returns |
|----------|----------|------|---------|
| `stock(name)` | `GET /stock` | `name` | full company mosaic (see table above) |
| `target_price(stock_id)` | `GET /stock_target_price` | `stock_id` (name) | analyst consensus target: `Mean/Median/High/Low`, `NumberOfEstimates`, `StandardDeviation` (INR) + history |
| `forecasts(stock_id, measure_code, period_type, data_type, age)` | `GET /stock_forecasts` | `measure_code`=EPS/Revenue/… `period_type`=Annual/Interim `data_type`=Actuals/Estimates `age`=Current/OneWeekAgo/… | estimates vs actuals per period |
| `corporate_actions(stock_name)` | `GET /corporate_actions` | `stock_name` | board meetings, dividends, splits, bonus, rights, AGM |
| `trending(exchange=None)` | `GET /trending` | optional `exchange`=NSE/BSE | top gainers & losers |
| `fifty_two_week_high_low()` | `GET /fetch_52_week_high_low_data` | — | 52-week highs/lows (BSE + NSE) |
| `nse_most_active()` | `GET /NSE_most_active` | — | highest-volume NSE stocks |
| `bse_most_active()` | `GET /BSE_most_active` | — | highest-volume BSE stocks |
| `price_shockers()` | `GET /price_shockers` | — | stocks with large intraday swings |
| `search_industry(query)` | `GET /industry_search` | `query` | companies by industry/sector (ids + names) |
| `news(page_no=1, size=20)` | `GET /news` | `page_no`, `size` | market news headlines (paginated) |
| `ipo()` | `GET /ipo` | — | upcoming / open / listed IPOs + subscription data |
| `mutual_funds()` | `GET /mutual_funds` | — | MF catalogue by category w/ NAV + 1/3/5-yr returns |
| `mutual_fund_details(stock_name)` | `GET /mutual_funds_details` | `stock_name` | one fund's info, returns, holdings |
| `search_mutual_fund(query)` | `GET /mutual_fund_search` | `query` | MF schemes by name |
| `commodities()` | `GET /commodities` | — | live MCX futures (gold, silver, crude…) |

### ⚠️ Heavy endpoints — currently return HTTP 504 on the free plan

`quarterly_results()`, `historical_stats(stats=…)`, `statement(stats=…)`,
`historical_data(period=, filter=)`, `recent_announcements()` →
`GET /historical_stats`, `/statement`, `/historical_data`,
`/recent_announcements`. These time out server-side on the free tier.

**You usually don't need them** — `stock()` already embeds quarterly financials,
the shareholding time series, and corporate actions. For Indian *price history*,
fall back to FMP: `get_historical_prices('MTARTECH.NS', from_date=…)`. Wrappers
are kept so they "just work" if the plan is upgraded; each returns
`{"error": ..., "status": 504}` rather than throwing.

### 🔒 Not available on this plan (HTTP 404 "Endpoint not allowed")

`/get_stock_data`, `/indices`, `/logo`, `/company_news`, `/credit_ratings`,
`/concalls`, `/annual_reports`, `/documents`, `/ai_news`, `/ping`, `/usage`.
These are documented on `analyst.indianapi.in` but gated to higher tiers — don't
call them. (Concalls / annual reports / company news would need a plan upgrade;
until then use `web_search`/`scrape_url` for those qualitative sources.)

## Worked example — the htibdewal flow ("Q4 out, hold/add/trim?")

```python
from skills.indian_stocks.scripts.stocks import stock, target_price, corporate_actions

name = "Shaily Engineering"
d = stock(name)

# 1) Latest quarter P&L + QoQ/YoY moves
inc = d["financials"][0]["stockFinancialMap"]["INC"]
for row in inc:
    print(row["displayName"], row["value"], "QoQ", row["qoQComp"], "YoY", row["yqoQComp"])

# 2) Valuation + growth ratios
print(d["keyMetrics"]["valuation"], d["keyMetrics"]["growth"])

# 3) Analyst consensus rating + price target vs current price
print("reco:", d["recosBar"]["meanValue"], "of", d["recosBar"]["noOfRecommendations"])
print("price target:", target_price(name)["priceTarget"])     # Mean/High/Low INR
print("current:", d["currentPrice"])

# 4) Promoter holding trend (pledging / dilution signal)
prom = next(c for c in d["shareholding"] if c["displayName"] == "Promoter")
print(prom["categories"])                                      # holdingDate -> percentage
```

## Notes & gotchas

- **Name resolution**: pass the company's common name. If a call returns empty,
  try `search_industry(...)` or a shorter/cleaner name (drop "Ltd", "Limited").
- **Errors don't throw**: `get(...)` returns `{"error": ..., "status": ...}` so a
  bad call won't kill the run — check for an `"error"` key.
- **Free-plan limits**: heavy endpoints 504; some endpoints 404 (see above). The
  16 working endpoints cover the core research/decision workflow.
- **US stocks**: use the `financial_modeling_prep` skill, not this one.
