"""
Financial Modeling Prep API Pydantic models for financial data
Comprehensive models for company financials, metrics, ratios, and market data
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd


# ============================================================================
# COMPANY PROFILE & INFO
# ============================================================================

class CompanyProfile(BaseModel):
    """Company profile and basic information"""
    symbol: str = Field(description="Stock ticker symbol")
    price: Optional[float] = Field(None, description="Current stock price")
    beta: Optional[float] = Field(None, description="Beta (volatility measure)")
    vol_avg: Optional[int] = Field(None, description="Average volume", alias="volAvg")
    mkt_cap: Optional[int] = Field(None, description="Market capitalization", alias="mktCap")
    last_div: Optional[float] = Field(None, description="Last dividend", alias="lastDiv")
    range: Optional[str] = Field(None, description="52-week range")
    changes: Optional[float] = Field(None, description="Price change")
    company_name: Optional[str] = Field(None, description="Company name", alias="companyName")
    currency: Optional[str] = Field(None, description="Trading currency")
    cik: Optional[str] = Field(None, description="CIK number")
    isin: Optional[str] = Field(None, description="ISIN")
    cusip: Optional[str] = Field(None, description="CUSIP")
    exchange: Optional[str] = Field(None, description="Stock exchange", alias="exchange")
    exchange_short_name: Optional[str] = Field(None, description="Exchange short name", alias="exchangeShortName")
    industry: Optional[str] = Field(None, description="Industry")
    website: Optional[str] = Field(None, description="Company website")
    description: Optional[str] = Field(None, description="Company description")
    ceo: Optional[str] = Field(None, description="CEO name")
    sector: Optional[str] = Field(None, description="Sector")
    country: Optional[str] = Field(None, description="Country")
    full_time_employees: Optional[str] = Field(None, description="Number of employees", alias="fullTimeEmployees")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Company address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    zip: Optional[str] = Field(None, description="ZIP code")
    dcf_diff: Optional[float] = Field(None, description="DCF difference", alias="dcfDiff")
    dcf: Optional[float] = Field(None, description="Discounted cash flow")
    image: Optional[str] = Field(None, description="Company logo URL")
    ipo_date: Optional[str] = Field(None, description="IPO date", alias="ipoDate")
    
    class Config:
        populate_by_name = True


# ============================================================================
# FINANCIAL STATEMENTS
# ============================================================================

class IncomeStatement(BaseModel):
    """Income statement data"""
    date: str = Field(description="Report date")
    symbol: str = Field(description="Stock ticker symbol")
    reported_currency: Optional[str] = Field(None, description="Currency", alias="reportedCurrency")
    cik: Optional[str] = Field(None, description="CIK number")
    filling_date: Optional[str] = Field(None, description="SEC filing date", alias="fillingDate")
    accepted_date: Optional[str] = Field(None, description="Acceptance date", alias="acceptedDate")
    calendar_year: Optional[str] = Field(None, description="Calendar year", alias="calendarYear")
    period: Optional[str] = Field(None, description="Period (Q1, Q2, Q3, Q4, FY)")
    
    # Revenue metrics
    revenue: Optional[float] = Field(None, description="Total revenue")
    cost_of_revenue: Optional[float] = Field(None, description="Cost of revenue", alias="costOfRevenue")
    gross_profit: Optional[float] = Field(None, description="Gross profit", alias="grossProfit")
    gross_profit_ratio: Optional[float] = Field(None, description="Gross profit ratio", alias="grossProfitRatio")
    
    # Operating expenses
    research_and_development_expenses: Optional[float] = Field(None, description="R&D expenses", alias="researchAndDevelopmentExpenses")
    general_and_administrative_expenses: Optional[float] = Field(None, description="G&A expenses", alias="generalAndAdministrativeExpenses")
    selling_and_marketing_expenses: Optional[float] = Field(None, description="S&M expenses", alias="sellingAndMarketingExpenses")
    selling_general_and_administrative_expenses: Optional[float] = Field(None, description="SG&A expenses", alias="sellingGeneralAndAdministrativeExpenses")
    other_expenses: Optional[float] = Field(None, description="Other expenses", alias="otherExpenses")
    operating_expenses: Optional[float] = Field(None, description="Total operating expenses", alias="operatingExpenses")
    cost_and_expenses: Optional[float] = Field(None, description="Total costs and expenses", alias="costAndExpenses")
    
    # Operating income
    interest_income: Optional[float] = Field(None, description="Interest income", alias="interestIncome")
    interest_expense: Optional[float] = Field(None, description="Interest expense", alias="interestExpense")
    depreciation_and_amortization: Optional[float] = Field(None, description="Depreciation and amortization", alias="depreciationAndAmortization")
    ebitda: Optional[float] = Field(None, description="EBITDA")
    ebitda_ratio: Optional[float] = Field(None, description="EBITDA ratio", alias="ebitdaratio")
    operating_income: Optional[float] = Field(None, description="Operating income", alias="operatingIncome")
    operating_income_ratio: Optional[float] = Field(None, description="Operating income ratio", alias="operatingIncomeRatio")
    
    # Net income
    total_other_income_expenses_net: Optional[float] = Field(None, description="Other income/expenses", alias="totalOtherIncomeExpensesNet")
    income_before_tax: Optional[float] = Field(None, description="Income before tax", alias="incomeBeforeTax")
    income_before_tax_ratio: Optional[float] = Field(None, description="Income before tax ratio", alias="incomeBeforeTaxRatio")
    income_tax_expense: Optional[float] = Field(None, description="Income tax expense", alias="incomeTaxExpense")
    net_income: Optional[float] = Field(None, description="Net income", alias="netIncome")
    net_income_ratio: Optional[float] = Field(None, description="Net income ratio", alias="netIncomeRatio")
    
    # Per share metrics
    eps: Optional[float] = Field(None, description="Earnings per share")
    eps_diluted: Optional[float] = Field(None, description="Diluted EPS", alias="epsdiluted")
    weighted_average_shs_out: Optional[float] = Field(None, description="Weighted average shares outstanding", alias="weightedAverageShsOut")
    weighted_average_shs_out_dil: Optional[float] = Field(None, description="Weighted average diluted shares", alias="weightedAverageShsOutDil")
    
    # Additional fields
    link: Optional[str] = Field(None, description="Link to SEC filing")
    final_link: Optional[str] = Field(None, description="Final link", alias="finalLink")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def list_to_df(cls, statements: List['IncomeStatement']) -> pd.DataFrame:
        """Convert list of income statements to DataFrame"""
        data = []
        for stmt in statements:
            data.append({
                "date": stmt.date,
                "period": stmt.period or "FY",
                "revenue": stmt.revenue,
                "gross_profit": stmt.gross_profit,
                "operating_income": stmt.operating_income,
                "net_income": stmt.net_income,
                "eps": stmt.eps,
                "ebitda": stmt.ebitda
            })
        return pd.DataFrame(data)


class BalanceSheet(BaseModel):
    """Balance sheet data"""
    date: str = Field(description="Report date")
    symbol: str = Field(description="Stock ticker symbol")
    reported_currency: Optional[str] = Field(None, description="Currency", alias="reportedCurrency")
    cik: Optional[str] = Field(None, description="CIK number")
    filling_date: Optional[str] = Field(None, description="SEC filing date", alias="fillingDate")
    accepted_date: Optional[str] = Field(None, description="Acceptance date", alias="acceptedDate")
    calendar_year: Optional[str] = Field(None, description="Calendar year", alias="calendarYear")
    period: Optional[str] = Field(None, description="Period (Q1, Q2, Q3, Q4, FY)")
    
    # Assets
    cash_and_cash_equivalents: Optional[float] = Field(None, description="Cash and equivalents", alias="cashAndCashEquivalents")
    short_term_investments: Optional[float] = Field(None, description="Short-term investments", alias="shortTermInvestments")
    cash_and_short_term_investments: Optional[float] = Field(None, description="Total cash and ST investments", alias="cashAndShortTermInvestments")
    net_receivables: Optional[float] = Field(None, description="Net receivables", alias="netReceivables")
    inventory: Optional[float] = Field(None, description="Inventory")
    other_current_assets: Optional[float] = Field(None, description="Other current assets", alias="otherCurrentAssets")
    total_current_assets: Optional[float] = Field(None, description="Total current assets", alias="totalCurrentAssets")
    property_plant_equipment_net: Optional[float] = Field(None, description="PP&E net", alias="propertyPlantEquipmentNet")
    goodwill: Optional[float] = Field(None, description="Goodwill")
    intangible_assets: Optional[float] = Field(None, description="Intangible assets", alias="intangibleAssets")
    goodwill_and_intangible_assets: Optional[float] = Field(None, description="Goodwill and intangible assets", alias="goodwillAndIntangibleAssets")
    long_term_investments: Optional[float] = Field(None, description="Long-term investments", alias="longTermInvestments")
    tax_assets: Optional[float] = Field(None, description="Tax assets", alias="taxAssets")
    other_non_current_assets: Optional[float] = Field(None, description="Other non-current assets", alias="otherNonCurrentAssets")
    total_non_current_assets: Optional[float] = Field(None, description="Total non-current assets", alias="totalNonCurrentAssets")
    other_assets: Optional[float] = Field(None, description="Other assets", alias="otherAssets")
    total_assets: Optional[float] = Field(None, description="Total assets", alias="totalAssets")
    
    # Liabilities
    account_payables: Optional[float] = Field(None, description="Accounts payable", alias="accountPayables")
    short_term_debt: Optional[float] = Field(None, description="Short-term debt", alias="shortTermDebt")
    tax_payables: Optional[float] = Field(None, description="Tax payables", alias="taxPayables")
    deferred_revenue: Optional[float] = Field(None, description="Deferred revenue", alias="deferredRevenue")
    other_current_liabilities: Optional[float] = Field(None, description="Other current liabilities", alias="otherCurrentLiabilities")
    total_current_liabilities: Optional[float] = Field(None, description="Total current liabilities", alias="totalCurrentLiabilities")
    long_term_debt: Optional[float] = Field(None, description="Long-term debt", alias="longTermDebt")
    deferred_revenue_non_current: Optional[float] = Field(None, description="Non-current deferred revenue", alias="deferredRevenueNonCurrent")
    deferred_tax_liabilities_non_current: Optional[float] = Field(None, description="Non-current deferred tax liabilities", alias="deferredTaxLiabilitiesNonCurrent")
    other_non_current_liabilities: Optional[float] = Field(None, description="Other non-current liabilities", alias="otherNonCurrentLiabilities")
    total_non_current_liabilities: Optional[float] = Field(None, description="Total non-current liabilities", alias="totalNonCurrentLiabilities")
    other_liabilities: Optional[float] = Field(None, description="Other liabilities", alias="otherLiabilities")
    capital_lease_obligations: Optional[float] = Field(None, description="Capital lease obligations", alias="capitalLeaseObligations")
    total_liabilities: Optional[float] = Field(None, description="Total liabilities", alias="totalLiabilities")
    
    # Equity
    preferred_stock: Optional[float] = Field(None, description="Preferred stock", alias="preferredStock")
    common_stock: Optional[float] = Field(None, description="Common stock", alias="commonStock")
    retained_earnings: Optional[float] = Field(None, description="Retained earnings", alias="retainedEarnings")
    accumulated_other_comprehensive_income_loss: Optional[float] = Field(None, description="Accumulated OCI", alias="accumulatedOtherComprehensiveIncomeLoss")
    othertotal_stockholders_equity: Optional[float] = Field(None, description="Other equity", alias="othertotalStockholdersEquity")
    total_stockholders_equity: Optional[float] = Field(None, description="Total stockholders equity", alias="totalStockholdersEquity")
    total_equity: Optional[float] = Field(None, description="Total equity", alias="totalEquity")
    total_liabilities_and_stockholders_equity: Optional[float] = Field(None, description="Total liabilities and equity", alias="totalLiabilitiesAndStockholdersEquity")
    minority_interest: Optional[float] = Field(None, description="Minority interest", alias="minorityInterest")
    total_liabilities_and_total_equity: Optional[float] = Field(None, description="Total liabilities and equity", alias="totalLiabilitiesAndTotalEquity")
    total_investments: Optional[float] = Field(None, description="Total investments", alias="totalInvestments")
    total_debt: Optional[float] = Field(None, description="Total debt", alias="totalDebt")
    net_debt: Optional[float] = Field(None, description="Net debt", alias="netDebt")
    
    # Additional fields
    link: Optional[str] = Field(None, description="Link to SEC filing")
    final_link: Optional[str] = Field(None, description="Final link", alias="finalLink")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def list_to_df(cls, statements: List['BalanceSheet']) -> pd.DataFrame:
        """Convert list of balance sheets to DataFrame"""
        data = []
        for stmt in statements:
            data.append({
                "date": stmt.date,
                "period": stmt.period or "FY",
                "total_assets": stmt.total_assets,
                "total_liabilities": stmt.total_liabilities,
                "total_equity": stmt.total_equity,
                "cash": stmt.cash_and_cash_equivalents,
                "debt": stmt.total_debt,
                "net_debt": stmt.net_debt
            })
        return pd.DataFrame(data)


class CashFlowStatement(BaseModel):
    """Cash flow statement data"""
    date: str = Field(description="Report date")
    symbol: str = Field(description="Stock ticker symbol")
    reported_currency: Optional[str] = Field(None, description="Currency", alias="reportedCurrency")
    cik: Optional[str] = Field(None, description="CIK number")
    filling_date: Optional[str] = Field(None, description="SEC filing date", alias="fillingDate")
    accepted_date: Optional[str] = Field(None, description="Acceptance date", alias="acceptedDate")
    calendar_year: Optional[str] = Field(None, description="Calendar year", alias="calendarYear")
    period: Optional[str] = Field(None, description="Period (Q1, Q2, Q3, Q4, FY)")
    
    # Operating activities
    net_income: Optional[float] = Field(None, description="Net income", alias="netIncome")
    depreciation_and_amortization: Optional[float] = Field(None, description="Depreciation and amortization", alias="depreciationAndAmortization")
    deferred_income_tax: Optional[float] = Field(None, description="Deferred income tax", alias="deferredIncomeTax")
    stock_based_compensation: Optional[float] = Field(None, description="Stock-based compensation", alias="stockBasedCompensation")
    change_in_working_capital: Optional[float] = Field(None, description="Change in working capital", alias="changeInWorkingCapital")
    accounts_receivables: Optional[float] = Field(None, description="Change in receivables", alias="accountsReceivables")
    inventory: Optional[float] = Field(None, description="Change in inventory")
    accounts_payables: Optional[float] = Field(None, description="Change in payables", alias="accountsPayables")
    other_working_capital: Optional[float] = Field(None, description="Other working capital changes", alias="otherWorkingCapital")
    other_non_cash_items: Optional[float] = Field(None, description="Other non-cash items", alias="otherNonCashItems")
    net_cash_provided_by_operating_activities: Optional[float] = Field(None, description="Cash from operations", alias="netCashProvidedByOperatingActivities")
    
    # Investing activities
    investments_in_property_plant_and_equipment: Optional[float] = Field(None, description="CapEx", alias="investmentsInPropertyPlantAndEquipment")
    acquisitions_net: Optional[float] = Field(None, description="Acquisitions net", alias="acquisitionsNet")
    purchases_of_investments: Optional[float] = Field(None, description="Purchases of investments", alias="purchasesOfInvestments")
    sales_maturities_of_investments: Optional[float] = Field(None, description="Sales/maturities of investments", alias="salesMaturitiesOfInvestments")
    other_investing_activites: Optional[float] = Field(None, description="Other investing activities", alias="otherInvestingActivites")
    net_cash_used_for_investing_activites: Optional[float] = Field(None, description="Cash from investing", alias="netCashUsedForInvestingActivites")
    
    # Financing activities
    debt_repayment: Optional[float] = Field(None, description="Debt repayment", alias="debtRepayment")
    common_stock_issued: Optional[float] = Field(None, description="Common stock issued", alias="commonStockIssued")
    common_stock_repurchased: Optional[float] = Field(None, description="Stock buybacks", alias="commonStockRepurchased")
    dividends_paid: Optional[float] = Field(None, description="Dividends paid", alias="dividendsPaid")
    other_financing_activites: Optional[float] = Field(None, description="Other financing activities", alias="otherFinancingActivites")
    net_cash_used_provided_by_financing_activities: Optional[float] = Field(None, description="Cash from financing", alias="netCashUsedProvidedByFinancingActivities")
    
    # Summary
    effect_of_forex_changes_on_cash: Optional[float] = Field(None, description="Forex effect on cash", alias="effectOfForexChangesOnCash")
    net_change_in_cash: Optional[float] = Field(None, description="Net change in cash", alias="netChangeInCash")
    cash_at_end_of_period: Optional[float] = Field(None, description="Cash at end of period", alias="cashAtEndOfPeriod")
    cash_at_beginning_of_period: Optional[float] = Field(None, description="Cash at beginning of period", alias="cashAtBeginningOfPeriod")
    operating_cash_flow: Optional[float] = Field(None, description="Operating cash flow", alias="operatingCashFlow")
    capital_expenditure: Optional[float] = Field(None, description="CapEx", alias="capitalExpenditure")
    free_cash_flow: Optional[float] = Field(None, description="Free cash flow", alias="freeCashFlow")
    
    # Additional fields
    link: Optional[str] = Field(None, description="Link to SEC filing")
    final_link: Optional[str] = Field(None, description="Final link", alias="finalLink")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def list_to_df(cls, statements: List['CashFlowStatement']) -> pd.DataFrame:
        """Convert list of cash flow statements to DataFrame"""
        data = []
        for stmt in statements:
            data.append({
                "date": stmt.date,
                "period": stmt.period or "FY",
                "operating_cf": stmt.net_cash_provided_by_operating_activities,
                "investing_cf": stmt.net_cash_used_for_investing_activites,
                "financing_cf": stmt.net_cash_used_provided_by_financing_activities,
                "capex": stmt.capital_expenditure,
                "free_cash_flow": stmt.free_cash_flow
            })
        return pd.DataFrame(data)


# ============================================================================
# KEY METRICS & RATIOS
# ============================================================================

class KeyMetrics(BaseModel):
    """Company key metrics and valuation ratios"""
    date: str = Field(description="Report date")
    symbol: str = Field(description="Stock ticker symbol")
    period: Optional[str] = Field(None, description="Period (Q1, Q2, Q3, Q4, FY)")
    calendar_year: Optional[str] = Field(None, description="Calendar year", alias="calendarYear")
    
    # Valuation metrics
    market_cap: Optional[float] = Field(None, description="Market capitalization", alias="marketCap")
    enterprise_value: Optional[float] = Field(None, description="Enterprise value", alias="enterpriseValue")
    pe_ratio: Optional[float] = Field(None, description="P/E ratio", alias="peRatio")
    price_to_sales_ratio: Optional[float] = Field(None, description="P/S ratio", alias="priceToSalesRatio")
    pocf_ratio: Optional[float] = Field(None, description="Price to operating cash flow", alias="pocfratio")
    pfcf_ratio: Optional[float] = Field(None, description="Price to free cash flow", alias="pfcfRatio")
    pb_ratio: Optional[float] = Field(None, description="P/B ratio", alias="pbRatio")
    ptb_ratio: Optional[float] = Field(None, description="Price to tangible book", alias="ptbRatio")
    ev_to_sales: Optional[float] = Field(None, description="EV/Sales", alias="evToSales")
    ev_to_ebitda: Optional[float] = Field(None, description="EV/EBITDA", alias="enterpriseValueOverEBITDA")
    ev_to_operating_cash_flow: Optional[float] = Field(None, description="EV/Operating CF", alias="evToOperatingCashFlow")
    ev_to_free_cash_flow: Optional[float] = Field(None, description="EV/Free CF", alias="evToFreeCashFlow")
    
    # Profitability metrics
    earnings_yield: Optional[float] = Field(None, description="Earnings yield", alias="earningsYield")
    free_cash_flow_yield: Optional[float] = Field(None, description="FCF yield", alias="freeCashFlowYield")
    debt_to_equity: Optional[float] = Field(None, description="Debt/Equity", alias="debtToEquity")
    debt_to_assets: Optional[float] = Field(None, description="Debt/Assets", alias="debtToAssets")
    net_debt_to_ebitda: Optional[float] = Field(None, description="Net Debt/EBITDA", alias="netDebtToEBITDA")
    current_ratio: Optional[float] = Field(None, description="Current ratio", alias="currentRatio")
    interest_coverage: Optional[float] = Field(None, description="Interest coverage", alias="interestCoverage")
    income_quality: Optional[float] = Field(None, description="Income quality", alias="incomeQuality")
    
    # Returns
    roe: Optional[float] = Field(None, description="Return on equity", alias="roe")
    roa: Optional[float] = Field(None, description="Return on assets", alias="returnOnTangibleAssets")
    roic: Optional[float] = Field(None, description="Return on invested capital", alias="roic")
    
    # Growth metrics
    revenue_per_share: Optional[float] = Field(None, description="Revenue per share", alias="revenuePerShare")
    net_income_per_share: Optional[float] = Field(None, description="Net income per share", alias="netIncomePerShare")
    operating_cash_flow_per_share: Optional[float] = Field(None, description="Operating CF per share", alias="operatingCashFlowPerShare")
    free_cash_flow_per_share: Optional[float] = Field(None, description="FCF per share", alias="freeCashFlowPerShare")
    cash_per_share: Optional[float] = Field(None, description="Cash per share", alias="cashPerShare")
    book_value_per_share: Optional[float] = Field(None, description="Book value per share", alias="bookValuePerShare")
    tangible_book_value_per_share: Optional[float] = Field(None, description="Tangible book value per share", alias="tangibleBookValuePerShare")
    shareholders_equity_per_share: Optional[float] = Field(None, description="Equity per share", alias="shareholdersEquityPerShare")
    
    # Dividend metrics
    dividend_yield: Optional[float] = Field(None, description="Dividend yield", alias="dividendYield")
    payout_ratio: Optional[float] = Field(None, description="Payout ratio", alias="payoutRatio")
    
    # Other metrics
    working_capital: Optional[float] = Field(None, description="Working capital", alias="workingCapital")
    average_receivables: Optional[float] = Field(None, description="Average receivables", alias="averageReceivables")
    average_payables: Optional[float] = Field(None, description="Average payables", alias="averagePayables")
    average_inventory: Optional[float] = Field(None, description="Average inventory", alias="averageInventory")
    days_sales_outstanding: Optional[float] = Field(None, description="Days sales outstanding", alias="daysSalesOutstanding")
    days_payables_outstanding: Optional[float] = Field(None, description="Days payables outstanding", alias="daysPayablesOutstanding")
    days_of_inventory_on_hand: Optional[float] = Field(None, description="Days inventory on hand", alias="daysOfInventoryOnHand")
    receivables_turnover: Optional[float] = Field(None, description="Receivables turnover", alias="receivablesTurnover")
    payables_turnover: Optional[float] = Field(None, description="Payables turnover", alias="payablesTurnover")
    inventory_turnover: Optional[float] = Field(None, description="Inventory turnover", alias="inventoryTurnover")
    
    # Cash flow metrics
    operating_cycle: Optional[float] = Field(None, description="Operating cycle", alias="operatingCycle")
    cash_conversion_cycle: Optional[float] = Field(None, description="Cash conversion cycle", alias="cashConversionCycle")
    gross_profit_margin: Optional[float] = Field(None, description="Gross profit margin", alias="grossProfitMargin")
    operating_profit_margin: Optional[float] = Field(None, description="Operating profit margin", alias="operatingProfitMargin")
    pretax_profit_margin: Optional[float] = Field(None, description="Pretax profit margin", alias="pretaxProfitMargin")
    net_profit_margin: Optional[float] = Field(None, description="Net profit margin", alias="netProfitMargin")
    effective_tax_rate: Optional[float] = Field(None, description="Effective tax rate", alias="effectiveTaxRate")
    
    # Share metrics
    shares_outstanding: Optional[float] = Field(None, description="Shares outstanding", alias="sharesOutstanding")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def list_to_df(cls, metrics: List['KeyMetrics']) -> pd.DataFrame:
        """Convert list of key metrics to DataFrame"""
        data = []
        for m in metrics:
            data.append({
                "date": m.date,
                "period": m.period or "FY",
                "market_cap": m.market_cap,
                "pe_ratio": m.pe_ratio,
                "pb_ratio": m.pb_ratio,
                "roe": m.roe,
                "roic": m.roic,
                "debt_to_equity": m.debt_to_equity,
                "fcf_yield": m.free_cash_flow_yield,
                "dividend_yield": m.dividend_yield
            })
        return pd.DataFrame(data)


class FinancialRatio(BaseModel):
    """Financial ratios for a company"""
    date: str = Field(description="Report date")
    symbol: str = Field(description="Stock ticker symbol")
    period: Optional[str] = Field(None, description="Period (Q1, Q2, Q3, Q4, FY)")
    
    # Liquidity ratios
    current_ratio: Optional[float] = Field(None, description="Current ratio", alias="currentRatio")
    quick_ratio: Optional[float] = Field(None, description="Quick ratio", alias="quickRatio")
    cash_ratio: Optional[float] = Field(None, description="Cash ratio", alias="cashRatio")
    days_of_sales_outstanding: Optional[float] = Field(None, description="DSO", alias="daysOfSalesOutstanding")
    days_of_inventory_outstanding: Optional[float] = Field(None, description="DIO", alias="daysOfInventoryOutstanding")
    operating_cycle: Optional[float] = Field(None, description="Operating cycle", alias="operatingCycle")
    days_of_payables_outstanding: Optional[float] = Field(None, description="DPO", alias="daysOfPayablesOutstanding")
    cash_conversion_cycle: Optional[float] = Field(None, description="Cash conversion cycle", alias="cashConversionCycle")
    
    # Profitability ratios
    gross_profit_margin: Optional[float] = Field(None, description="Gross profit margin", alias="grossProfitMargin")
    operating_profit_margin: Optional[float] = Field(None, description="Operating margin", alias="operatingProfitMargin")
    pretax_profit_margin: Optional[float] = Field(None, description="Pretax margin", alias="pretaxProfitMargin")
    net_profit_margin: Optional[float] = Field(None, description="Net margin", alias="netProfitMargin")
    effective_tax_rate: Optional[float] = Field(None, description="Tax rate", alias="effectiveTaxRate")
    return_on_assets: Optional[float] = Field(None, description="ROA", alias="returnOnAssets")
    return_on_equity: Optional[float] = Field(None, description="ROE", alias="returnOnEquity")
    return_on_capital_employed: Optional[float] = Field(None, description="ROCE", alias="returnOnCapitalEmployed")
    
    # Leverage ratios
    debt_ratio: Optional[float] = Field(None, description="Debt ratio", alias="debtRatio")
    debt_equity_ratio: Optional[float] = Field(None, description="Debt/Equity", alias="debtEquityRatio")
    long_term_debt_to_capitalization: Optional[float] = Field(None, description="LT debt to cap", alias="longTermDebtToCapitalization")
    total_debt_to_capitalization: Optional[float] = Field(None, description="Total debt to cap", alias="totalDebtToCapitalization")
    interest_coverage: Optional[float] = Field(None, description="Interest coverage", alias="interestCoverage")
    cash_flow_to_debt_ratio: Optional[float] = Field(None, description="CF to debt", alias="cashFlowToDebtRatio")
    company_equity_multiplier: Optional[float] = Field(None, description="Equity multiplier", alias="companyEquityMultiplier")
    
    # Efficiency ratios
    receivables_turnover: Optional[float] = Field(None, description="Receivables turnover", alias="receivablesTurnover")
    payables_turnover: Optional[float] = Field(None, description="Payables turnover", alias="payablesTurnover")
    inventory_turnover: Optional[float] = Field(None, description="Inventory turnover", alias="inventoryTurnover")
    fixed_asset_turnover: Optional[float] = Field(None, description="Fixed asset turnover", alias="fixedAssetTurnover")
    asset_turnover: Optional[float] = Field(None, description="Asset turnover", alias="assetTurnover")
    
    # Market ratios
    price_earnings_ratio: Optional[float] = Field(None, description="P/E ratio", alias="priceEarningsRatio")
    price_to_book_ratio: Optional[float] = Field(None, description="P/B ratio", alias="priceToBookRatio")
    price_to_sales_ratio: Optional[float] = Field(None, description="P/S ratio", alias="priceToSalesRatio")
    price_cash_flow_ratio: Optional[float] = Field(None, description="P/CF ratio", alias="priceCashFlowRatio")
    price_earnings_to_growth_ratio: Optional[float] = Field(None, description="PEG ratio", alias="priceEarningsToGrowthRatio")
    price_to_free_cash_flows_ratio: Optional[float] = Field(None, description="P/FCF ratio", alias="priceToFreeCashFlowsRatio")
    dividend_yield: Optional[float] = Field(None, description="Dividend yield", alias="dividendYield")
    payout_ratio: Optional[float] = Field(None, description="Payout ratio", alias="payoutRatio")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def list_to_df(cls, ratios: List['FinancialRatio']) -> pd.DataFrame:
        """Convert list of financial ratios to DataFrame"""
        data = []
        for r in ratios:
            data.append({
                "date": r.date,
                "period": r.period or "FY",
                "current_ratio": r.current_ratio,
                "quick_ratio": r.quick_ratio,
                "gross_margin": r.gross_profit_margin,
                "net_margin": r.net_profit_margin,
                "roe": r.return_on_equity,
                "debt_equity": r.debt_equity_ratio,
                "pe_ratio": r.price_earnings_ratio
            })
        return pd.DataFrame(data)


# ============================================================================
# MARKET DATA
# ============================================================================

class HistoricalPrice(BaseModel):
    """Historical price data"""
    date: str = Field(description="Trading date")
    open: float = Field(description="Opening price")
    high: float = Field(description="High price")
    low: float = Field(description="Low price")
    close: float = Field(description="Closing price")
    adj_close: Optional[float] = Field(None, description="Adjusted close", alias="adjClose")
    volume: int = Field(description="Trading volume")
    unadjusted_volume: Optional[int] = Field(None, description="Unadjusted volume", alias="unadjustedVolume")
    change: Optional[float] = Field(None, description="Price change")
    change_percent: Optional[float] = Field(None, description="Price change percent", alias="changePercent")
    vwap: Optional[float] = Field(None, description="Volume weighted average price")
    label: Optional[str] = Field(None, description="Label")
    change_over_time: Optional[float] = Field(None, description="Change over time", alias="changeOverTime")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def list_to_df(cls, prices: List['HistoricalPrice']) -> pd.DataFrame:
        """Convert list of historical prices to DataFrame"""
        data = []
        for p in prices:
            data.append({
                "date": p.date,
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume
            })
        return pd.DataFrame(data)


class Quote(BaseModel):
    """Real-time quote data"""
    symbol: str = Field(description="Stock ticker symbol")
    name: Optional[str] = Field(None, description="Company name")
    price: Optional[float] = Field(None, description="Current price")
    changes_percentage: Optional[float] = Field(None, description="Percentage change", alias="changesPercentage")
    change: Optional[float] = Field(None, description="Price change")
    day_low: Optional[float] = Field(None, description="Day low", alias="dayLow")
    day_high: Optional[float] = Field(None, description="Day high", alias="dayHigh")
    year_high: Optional[float] = Field(None, description="52-week high", alias="yearHigh")
    year_low: Optional[float] = Field(None, description="52-week low", alias="yearLow")
    market_cap: Optional[float] = Field(None, description="Market cap", alias="marketCap")
    price_avg_50: Optional[float] = Field(None, description="50-day MA", alias="priceAvg50")
    price_avg_200: Optional[float] = Field(None, description="200-day MA", alias="priceAvg200")
    exchange: Optional[str] = Field(None, description="Exchange")
    volume: Optional[float] = Field(None, description="Volume")
    avg_volume: Optional[float] = Field(None, description="Average volume", alias="avgVolume")
    open: Optional[float] = Field(None, description="Opening price")
    previous_close: Optional[float] = Field(None, description="Previous close", alias="previousClose")
    eps: Optional[float] = Field(None, description="EPS")
    pe: Optional[float] = Field(None, description="P/E ratio")
    earnings_announcement: Optional[str] = Field(None, description="Earnings announcement date", alias="earningsAnnouncement")
    shares_outstanding: Optional[float] = Field(None, description="Shares outstanding", alias="sharesOutstanding")
    timestamp: Optional[int] = Field(None, description="Timestamp")
    
    class Config:
        populate_by_name = True


# ============================================================================
# ANALYST RECOMMENDATIONS
# ============================================================================

class AnalystRecommendation(BaseModel):
    """Analyst recommendation data"""
    symbol: str = Field(description="Stock ticker symbol")
    date: str = Field(description="Recommendation date")
    analyst_ratings_buy: Optional[int] = Field(None, description="Buy ratings", alias="analystRatingsbuy")
    analyst_ratings_hold: Optional[int] = Field(None, description="Hold ratings", alias="analystRatingsHold")
    analyst_ratings_sell: Optional[int] = Field(None, description="Sell ratings", alias="analystRatingsSell")
    analyst_ratings_strong_buy: Optional[int] = Field(None, description="Strong buy ratings", alias="analystRatingsStrongBuy")
    analyst_ratings_strong_sell: Optional[int] = Field(None, description="Strong sell ratings", alias="analystRatingsStrongSell")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def list_to_df(cls, recommendations: List['AnalystRecommendation']) -> pd.DataFrame:
        """Convert list of analyst recommendations to DataFrame"""
        data = []
        for r in recommendations:
            data.append({
                "date": r.date,
                "strong_buy": r.analyst_ratings_strong_buy,
                "buy": r.analyst_ratings_buy,
                "hold": r.analyst_ratings_hold,
                "sell": r.analyst_ratings_sell,
                "strong_sell": r.analyst_ratings_strong_sell
            })
        return pd.DataFrame(data)


# ============================================================================
# FINANCIAL GROWTH
# ============================================================================

class FinancialGrowth(BaseModel):
    """Company financial growth metrics"""
    date: str = Field(description="Report date")
    symbol: str = Field(description="Stock ticker symbol")
    period: Optional[str] = Field(None, description="Period (Q1, Q2, Q3, Q4, FY)")
    calendar_year: Optional[str] = Field(None, description="Calendar year", alias="calendarYear")
    
    # Revenue growth
    revenue_growth: Optional[float] = Field(None, description="Revenue growth %", alias="revenueGrowth")
    gross_profit_growth: Optional[float] = Field(None, description="Gross profit growth %", alias="grossProfitGrowth")
    ebit_growth: Optional[float] = Field(None, description="EBIT growth %", alias="ebitgrowth")
    operating_income_growth: Optional[float] = Field(None, description="Operating income growth %", alias="operatingIncomeGrowth")
    net_income_growth: Optional[float] = Field(None, description="Net income growth %", alias="netIncomeGrowth")
    eps_growth: Optional[float] = Field(None, description="EPS growth %", alias="epsgrowth")
    eps_diluted_growth: Optional[float] = Field(None, description="Diluted EPS growth %", alias="epsdilutedGrowth")
    
    # Per share growth
    weighted_average_shares_growth: Optional[float] = Field(None, description="Shares outstanding growth %", alias="weightedAverageSharesGrowth")
    weighted_average_shares_diluted_growth: Optional[float] = Field(None, description="Diluted shares growth %", alias="weightedAverageSharesDilutedGrowth")
    
    # Operating metrics growth
    dividends_per_share_growth: Optional[float] = Field(None, description="DPS growth %", alias="dividendsperShareGrowth")
    operating_cash_flow_growth: Optional[float] = Field(None, description="Operating CF growth %", alias="operatingCashFlowGrowth")
    free_cash_flow_growth: Optional[float] = Field(None, description="FCF growth %", alias="freeCashFlowGrowth")
    
    # Balance sheet growth
    ten_y_revenue_growth_per_share: Optional[float] = Field(None, description="10Y revenue per share growth %", alias="tenYRevenueGrowthPerShare")
    five_y_revenue_growth_per_share: Optional[float] = Field(None, description="5Y revenue per share growth %", alias="fiveYRevenueGrowthPerShare")
    three_y_revenue_growth_per_share: Optional[float] = Field(None, description="3Y revenue per share growth %", alias="threeYRevenueGrowthPerShare")
    ten_y_operating_cf_growth_per_share: Optional[float] = Field(None, description="10Y operating CF per share growth %", alias="tenYOperatingCFGrowthPerShare")
    five_y_operating_cf_growth_per_share: Optional[float] = Field(None, description="5Y operating CF per share growth %", alias="fiveYOperatingCFGrowthPerShare")
    three_y_operating_cf_growth_per_share: Optional[float] = Field(None, description="3Y operating CF per share growth %", alias="threeYOperatingCFGrowthPerShare")
    ten_y_net_income_growth_per_share: Optional[float] = Field(None, description="10Y net income per share growth %", alias="tenYNetIncomeGrowthPerShare")
    five_y_net_income_growth_per_share: Optional[float] = Field(None, description="5Y net income per share growth %", alias="fiveYNetIncomeGrowthPerShare")
    three_y_net_income_growth_per_share: Optional[float] = Field(None, description="3Y net income per share growth %", alias="threeYNetIncomeGrowthPerShare")
    ten_y_shareholders_equity_growth_per_share: Optional[float] = Field(None, description="10Y equity per share growth %", alias="tenYShareholdersEquityGrowthPerShare")
    five_y_shareholders_equity_growth_per_share: Optional[float] = Field(None, description="5Y equity per share growth %", alias="fiveYShareholdersEquityGrowthPerShare")
    three_y_shareholders_equity_growth_per_share: Optional[float] = Field(None, description="3Y equity per share growth %", alias="threeYShareholdersEquityGrowthPerShare")
    ten_y_dividend_per_share_growth_per_share: Optional[float] = Field(None, description="10Y DPS growth %", alias="tenYDividendperShareGrowthPerShare")
    five_y_dividend_per_share_growth_per_share: Optional[float] = Field(None, description="5Y DPS growth %", alias="fiveYDividendperShareGrowthPerShare")
    three_y_dividend_per_share_growth_per_share: Optional[float] = Field(None, description="3Y DPS growth %", alias="threeYDividendperShareGrowthPerShare")
    
    # Asset/Liability growth
    receivables_growth: Optional[float] = Field(None, description="Receivables growth %", alias="receivablesGrowth")
    inventory_growth: Optional[float] = Field(None, description="Inventory growth %", alias="inventoryGrowth")
    asset_growth: Optional[float] = Field(None, description="Asset growth %", alias="assetGrowth")
    book_value_per_share_growth: Optional[float] = Field(None, description="Book value per share growth %", alias="bookValueperShareGrowth")
    debt_growth: Optional[float] = Field(None, description="Debt growth %", alias="debtGrowth")
    rd_expense_growth: Optional[float] = Field(None, description="R&D expense growth %", alias="rdexpenseGrowth")
    sga_expenses_growth: Optional[float] = Field(None, description="SG&A growth %", alias="sgaexpensesGrowth")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def list_to_df(cls, growth: List['FinancialGrowth']) -> pd.DataFrame:
        """Convert list of financial growth to DataFrame"""
        data = []
        for g in growth:
            data.append({
                "date": g.date,
                "period": g.period or "FY",
                "revenue_growth": g.revenue_growth,
                "net_income_growth": g.net_income_growth,
                "eps_growth": g.eps_growth,
                "fcf_growth": g.free_cash_flow_growth
            })
        return pd.DataFrame(data)


# ============================================================================
# STOCK SCREENER
# ============================================================================

class StockScreenerResult(BaseModel):
    """Stock screener result"""
    symbol: str = Field(description="Stock ticker symbol")
    company_name: str = Field(description="Company name", alias="companyName")
    market_cap: Optional[float] = Field(None, description="Market capitalization", alias="marketCap")
    sector: Optional[str] = Field(None, description="Sector")
    industry: Optional[str] = Field(None, description="Industry")
    beta: Optional[float] = Field(None, description="Beta (volatility measure)")
    price: Optional[float] = Field(None, description="Current stock price")
    last_annual_dividend: Optional[float] = Field(None, description="Last annual dividend", alias="lastAnnualDividend")
    volume: Optional[int] = Field(None, description="Trading volume")
    exchange: Optional[str] = Field(None, description="Stock exchange")
    exchange_short_name: Optional[str] = Field(None, description="Exchange short name", alias="exchangeShortName")
    country: Optional[str] = Field(None, description="Country")
    is_etf: Optional[bool] = Field(None, description="Is ETF", alias="isEtf")
    is_fund: Optional[bool] = Field(None, description="Is fund", alias="isFund")
    is_actively_trading: Optional[bool] = Field(None, description="Is actively trading", alias="isActivelyTrading")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def list_to_df(cls, results: List['StockScreenerResult']) -> pd.DataFrame:
        """Convert list of screener results to DataFrame"""
        data = []
        for r in results:
            data.append({
                "symbol": r.symbol,
                "company_name": r.company_name,
                "market_cap": r.market_cap,
                "sector": r.sector,
                "industry": r.industry,
                "beta": r.beta,
                "price": r.price,
                "dividend": r.last_annual_dividend,
                "volume": r.volume,
                "exchange": r.exchange_short_name,
                "country": r.country,
                "is_etf": r.is_etf,
                "is_actively_trading": r.is_actively_trading
            })
        return pd.DataFrame(data)

