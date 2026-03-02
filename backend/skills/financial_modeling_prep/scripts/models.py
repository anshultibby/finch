"""
Pydantic models for Financial Modeling Prep API.

These models provide:
1. Clear documentation of response structure
2. Type safety and validation
3. IDE autocomplete support
4. Self-documenting code for the LLM agent
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# ============================================================================
# COMPANY PROFILE & EXECUTIVES
# ============================================================================

class CompanyProfile(BaseModel):
    """Company profile information"""
    symbol: str = Field(description="Stock ticker symbol")
    price: Optional[float] = Field(default=None, description="Current stock price")
    beta: Optional[float] = Field(default=None, description="Stock beta (volatility)")
    volAvg: Optional[int] = Field(default=None, description="Average daily volume")
    mktCap: Optional[float] = Field(default=None, description="Market capitalization")
    lastDiv: Optional[float] = Field(default=None, description="Last dividend")
    range: Optional[str] = Field(default=None, description="52-week range")
    changes: Optional[float] = Field(default=None, description="Price change")
    companyName: str = Field(description="Company name")
    currency: Optional[str] = Field(default=None, description="Trading currency")
    cik: Optional[str] = Field(default=None, description="SEC CIK number")
    isin: Optional[str] = Field(default=None, description="ISIN identifier")
    cusip: Optional[str] = Field(default=None, description="CUSIP identifier")
    exchange: Optional[str] = Field(default=None, description="Stock exchange")
    exchangeShortName: Optional[str] = Field(default=None, description="Exchange short name")
    industry: Optional[str] = Field(default=None, description="Industry")
    website: Optional[str] = Field(default=None, description="Company website")
    description: Optional[str] = Field(default=None, description="Company description")
    ceo: Optional[str] = Field(default=None, description="CEO name")
    sector: Optional[str] = Field(default=None, description="Market sector")
    country: Optional[str] = Field(default=None, description="Headquarters country")
    fullTimeEmployees: Optional[str] = Field(default=None, description="Number of employees")
    phone: Optional[str] = Field(default=None, description="Company phone")
    address: Optional[str] = Field(default=None, description="Headquarters address")
    city: Optional[str] = Field(default=None, description="Headquarters city")
    state: Optional[str] = Field(default=None, description="Headquarters state")
    zip: Optional[str] = Field(default=None, description="Headquarters ZIP")
    image: Optional[str] = Field(default=None, description="Company logo URL")
    ipoDate: Optional[str] = Field(default=None, description="IPO date")
    isEtf: Optional[bool] = Field(default=None, description="Whether it's an ETF")
    isActivelyTrading: Optional[bool] = Field(default=None, description="Whether actively trading")


class Executive(BaseModel):
    """Company executive"""
    title: str = Field(description="Job title")
    name: str = Field(description="Executive name")
    pay: Optional[float] = Field(default=None, description="Compensation")
    currencyPay: Optional[str] = Field(default=None, description="Pay currency")
    gender: Optional[str] = Field(default=None, description="Gender")
    yearBorn: Optional[int] = Field(default=None, description="Birth year")
    titleSince: Optional[str] = Field(default=None, description="Title start date")


# ============================================================================
# MARKET QUOTES
# ============================================================================

class Quote(BaseModel):
    """Stock quote - IMPORTANT: get_quote_snapshot returns a LIST"""
    symbol: str = Field(description="Stock ticker")
    name: Optional[str] = Field(default=None, description="Company name")
    price: float = Field(description="Current price")
    changesPercentage: Optional[float] = Field(default=None, description="Percent change")
    change: Optional[float] = Field(default=None, description="Price change")
    dayLow: Optional[float] = Field(default=None, description="Day low")
    dayHigh: Optional[float] = Field(default=None, description="Day high")
    yearHigh: Optional[float] = Field(default=None, description="52-week high")
    yearLow: Optional[float] = Field(default=None, description="52-week low")
    marketCap: Optional[float] = Field(default=None, description="Market cap")
    priceAvg50: Optional[float] = Field(default=None, description="50-day MA")
    priceAvg200: Optional[float] = Field(default=None, description="200-day MA")
    volume: Optional[int] = Field(default=None, description="Current volume")
    avgVolume: Optional[int] = Field(default=None, description="Average volume")
    open: Optional[float] = Field(default=None, description="Opening price")
    previousClose: Optional[float] = Field(default=None, description="Previous close")
    eps: Optional[float] = Field(default=None, description="Earnings per share")
    pe: Optional[float] = Field(default=None, description="P/E ratio")
    earningsAnnouncement: Optional[str] = Field(default=None, description="Next earnings date")
    sharesOutstanding: Optional[int] = Field(default=None, description="Shares outstanding")
    timestamp: Optional[int] = Field(default=None, description="Quote timestamp")


# ============================================================================
# FINANCIALS
# ============================================================================

class IncomeStatement(BaseModel):
    """Income statement data"""
    date: str = Field(description="Reporting date")
    symbol: str = Field(description="Stock ticker")
    reportedCurrency: Optional[str] = Field(default=None, description="Currency")
    cik: Optional[str] = Field(default=None, description="SEC CIK")
    fillingDate: Optional[str] = Field(default=None, description="Filing date")
    acceptedDate: Optional[str] = Field(default=None, description="Acceptance date")
    calendarYear: Optional[str] = Field(default=None, description="Calendar year")
    period: Optional[str] = Field(default=None, description="Period (Q1, Q2, FY, etc)")
    revenue: Optional[float] = Field(default=None, description="Total revenue")
    costOfRevenue: Optional[float] = Field(default=None, description="Cost of revenue")
    grossProfit: Optional[float] = Field(default=None, description="Gross profit")
    grossProfitRatio: Optional[float] = Field(default=None, description="Gross profit margin")
    operatingIncome: Optional[float] = Field(default=None, description="Operating income")
    operatingIncomeRatio: Optional[float] = Field(default=None, description="Operating margin")
    netIncome: Optional[float] = Field(default=None, description="Net income")
    netIncomeRatio: Optional[float] = Field(default=None, description="Net profit margin")
    eps: Optional[float] = Field(default=None, description="Earnings per share")
    epsdiluted: Optional[float] = Field(default=None, description="Diluted EPS")
    ebitda: Optional[float] = Field(default=None, description="EBITDA")
    ebitdaratio: Optional[float] = Field(default=None, description="EBITDA margin")


class BalanceSheet(BaseModel):
    """Balance sheet data"""
    date: str = Field(description="Reporting date")
    symbol: str = Field(description="Stock ticker")
    reportedCurrency: Optional[str] = Field(default=None, description="Currency")
    period: Optional[str] = Field(default=None, description="Period")
    totalAssets: Optional[float] = Field(default=None, description="Total assets")
    totalCurrentAssets: Optional[float] = Field(default=None, description="Current assets")
    totalNonCurrentAssets: Optional[float] = Field(default=None, description="Non-current assets")
    totalLiabilities: Optional[float] = Field(default=None, description="Total liabilities")
    totalCurrentLiabilities: Optional[float] = Field(default=None, description="Current liabilities")
    totalNonCurrentLiabilities: Optional[float] = Field(default=None, description="Non-current liabilities")
    totalStockholdersEquity: Optional[float] = Field(default=None, description="Shareholders' equity")
    cashAndCashEquivalents: Optional[float] = Field(default=None, description="Cash and equivalents")
    inventory: Optional[float] = Field(default=None, description="Inventory")
    totalDebt: Optional[float] = Field(default=None, description="Total debt")
    netDebt: Optional[float] = Field(default=None, description="Net debt")


class CashFlowStatement(BaseModel):
    """Cash flow statement data"""
    date: str = Field(description="Reporting date")
    symbol: str = Field(description="Stock ticker")
    reportedCurrency: Optional[str] = Field(default=None, description="Currency")
    period: Optional[str] = Field(default=None, description="Period")
    netIncome: Optional[float] = Field(default=None, description="Net income")
    operatingCashFlow: Optional[float] = Field(default=None, description="Operating cash flow")
    capitalExpenditure: Optional[float] = Field(default=None, description="CapEx")
    freeCashFlow: Optional[float] = Field(default=None, description="Free cash flow")
    dividendsPaid: Optional[float] = Field(default=None, description="Dividends paid")


class KeyMetrics(BaseModel):
    """Key financial metrics"""
    date: str = Field(description="Reporting date")
    symbol: str = Field(description="Stock ticker")
    period: Optional[str] = Field(default=None, description="Period")
    revenuePerShare: Optional[float] = Field(default=None, description="Revenue per share")
    netIncomePerShare: Optional[float] = Field(default=None, description="Net income per share")
    operatingCashFlowPerShare: Optional[float] = Field(default=None, description="OCF per share")
    freeCashFlowPerShare: Optional[float] = Field(default=None, description="FCF per share")
    cashPerShare: Optional[float] = Field(default=None, description="Cash per share")
    bookValuePerShare: Optional[float] = Field(default=None, description="Book value per share")
    peRatio: Optional[float] = Field(default=None, description="P/E ratio")
    priceToSalesRatio: Optional[float] = Field(default=None, description="P/S ratio")
    pocfratio: Optional[float] = Field(default=None, description="Price/OCF ratio")
    pfcfRatio: Optional[float] = Field(default=None, description="Price/FCF ratio")
    pbRatio: Optional[float] = Field(default=None, description="P/B ratio")
    evToSales: Optional[float] = Field(default=None, description="EV/Sales")
    enterpriseValueOverEBITDA: Optional[float] = Field(default=None, description="EV/EBITDA")
    evToOperatingCashFlow: Optional[float] = Field(default=None, description="EV/OCF")
    evToFreeCashFlow: Optional[float] = Field(default=None, description="EV/FCF")
    earningsYield: Optional[float] = Field(default=None, description="Earnings yield")
    freeCashFlowYield: Optional[float] = Field(default=None, description="FCF yield")
    debtToEquity: Optional[float] = Field(default=None, description="Debt/Equity")
    debtToAssets: Optional[float] = Field(default=None, description="Debt/Assets")
    returnOnEquity: Optional[float] = Field(default=None, description="ROE")
    returnOnAssets: Optional[float] = Field(default=None, description="ROA")


class FinancialRatios(BaseModel):
    """Financial ratios"""
    date: str = Field(description="Reporting date")
    symbol: str = Field(description="Stock ticker")
    period: Optional[str] = Field(default=None, description="Period")
    currentRatio: Optional[float] = Field(default=None, description="Current ratio")
    quickRatio: Optional[float] = Field(default=None, description="Quick ratio")
    cashRatio: Optional[float] = Field(default=None, description="Cash ratio")
    grossProfitMargin: Optional[float] = Field(default=None, description="Gross margin")
    operatingProfitMargin: Optional[float] = Field(default=None, description="Operating margin")
    netProfitMargin: Optional[float] = Field(default=None, description="Net margin")
    returnOnAssets: Optional[float] = Field(default=None, description="ROA")
    returnOnEquity: Optional[float] = Field(default=None, description="ROE")
    debtRatio: Optional[float] = Field(default=None, description="Debt ratio")
    debtEquityRatio: Optional[float] = Field(default=None, description="Debt/Equity")


# ============================================================================
# INSIDER & INSTITUTIONAL
# ============================================================================

class InsiderRoster(BaseModel):
    """Insider roster entry"""
    name: str = Field(description="Insider name")
    position: Optional[str] = Field(default=None, description="Position/title")
    ownershipType: Optional[str] = Field(default=None, description="Ownership type")
    sharesHeld: Optional[int] = Field(default=None, description="Shares held")
    percentHeld: Optional[float] = Field(default=None, description="Percent ownership")


class InsiderTrade(BaseModel):
    """Insider trading transaction"""
    symbol: str = Field(description="Stock ticker")
    filingDate: str = Field(description="Filing date")
    transactionDate: str = Field(description="Transaction date")
    reportingCik: Optional[str] = Field(default=None, description="Reporter CIK")
    transactionType: Optional[str] = Field(default=None, description="Transaction type")
    securitiesOwned: Optional[int] = Field(default=None, description="Securities owned")
    companyCik: Optional[str] = Field(default=None, description="Company CIK")
    reportingName: Optional[str] = Field(default=None, description="Reporting person")
    typeOfOwner: Optional[str] = Field(default=None, description="Owner type")
    acquistionOrDisposition: Optional[str] = Field(default=None, description="A (buy) or D (sell)")
    formType: Optional[str] = Field(default=None, description="Form type (4, 5, etc)")
    securitiesTransacted: Optional[float] = Field(default=None, description="Shares transacted")
    price: Optional[float] = Field(default=None, description="Transaction price")
    securityName: Optional[str] = Field(default=None, description="Security name")


class InstitutionalOwnership(BaseModel):
    """Institutional ownership (13F filer)"""
    symbol: str = Field(description="Stock ticker")
    cik: Optional[str] = Field(default=None, description="CIK")
    date: str = Field(description="Reporting date")
    investorName: str = Field(description="Institution name")
    shares: Optional[int] = Field(default=None, description="Shares held")
    change: Optional[int] = Field(default=None, description="Change in shares")
    changePercent: Optional[float] = Field(default=None, description="Percent change")
    portfolioPercent: Optional[float] = Field(default=None, description="Percent of portfolio")


# ============================================================================
# ANALYST ESTIMATES
# ============================================================================

class PriceTarget(BaseModel):
    """Analyst price target"""
    symbol: str = Field(description="Stock ticker")
    publishedDate: str = Field(description="Publication date")
    newsURL: Optional[str] = Field(default=None, description="News article URL")
    newsTitle: Optional[str] = Field(default=None, description="Article title")
    analystName: Optional[str] = Field(default=None, description="Analyst name")
    priceTarget: Optional[float] = Field(default=None, description="Price target")
    adjPriceTarget: Optional[float] = Field(default=None, description="Adjusted price target")
    priceWhenPosted: Optional[float] = Field(default=None, description="Price when posted")
    newsPublisher: Optional[str] = Field(default=None, description="Publisher")
    newsBaseURL: Optional[str] = Field(default=None, description="Publisher base URL")


class PriceTargetConsensus(BaseModel):
    """Consensus price target"""
    symbol: str = Field(description="Stock ticker")
    targetHigh: Optional[float] = Field(default=None, description="Highest target")
    targetLow: Optional[float] = Field(default=None, description="Lowest target")
    targetConsensus: Optional[float] = Field(default=None, description="Consensus target")
    targetMedian: Optional[float] = Field(default=None, description="Median target")


# ============================================================================
# SEARCH
# ============================================================================

class SearchResult(BaseModel):
    """Search result for a stock"""
    symbol: str = Field(description="Stock ticker")
    name: str = Field(description="Company name")
    currency: Optional[str] = Field(default=None, description="Currency")
    stockExchange: Optional[str] = Field(default=None, description="Exchange")
    exchangeShortName: Optional[str] = Field(default=None, description="Exchange short name")
