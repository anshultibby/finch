"""Mapping from FMP camelCase field names to XBRL US-GAAP concept names.

Each key maps to a list of candidates (most common first) since companies
may use different concept names for the same line item.
"""

FMP_TO_XBRL: dict[str, list[str]] = {
    # ── Income Statement ──────────────────────────────────────────────
    "revenue": [
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:Revenues",
        "us-gaap:SalesRevenueNet",
        "us-gaap:SalesRevenueGoodsNet",
    ],
    "costOfRevenue": [
        "us-gaap:CostOfRevenue",
        "us-gaap:CostOfGoodsAndServicesSold",
        "us-gaap:CostOfGoodsSold",
    ],
    "grossProfit": ["us-gaap:GrossProfit"],
    "sellingGeneralAndAdministrativeExpenses": [
        "us-gaap:SellingGeneralAndAdministrativeExpense",
    ],
    "researchAndDevelopmentExpenses": [
        "us-gaap:ResearchAndDevelopmentExpense",
    ],
    "otherExpenses": [
        "us-gaap:OtherOperatingIncomeExpenseNet",
        "us-gaap:OtherExpenses",
    ],
    "operatingIncome": [
        "us-gaap:OperatingIncomeLoss",
    ],
    "interestIncome": [
        "us-gaap:InvestmentIncomeInterest",
        "us-gaap:InterestIncomeOther",
    ],
    "interestExpense": [
        "us-gaap:InterestExpense",
        "us-gaap:InterestExpenseDebt",
    ],
    "totalOtherIncomeExpensesNet": [
        "us-gaap:NonoperatingIncomeExpense",
        "us-gaap:OtherNonoperatingIncomeExpense",
    ],
    "incomeBeforeTax": [
        "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "incomeTaxExpense": [
        "us-gaap:IncomeTaxExpenseBenefit",
    ],
    "netIncome": [
        "us-gaap:NetIncomeLoss",
        "us-gaap:ProfitLoss",
    ],
    "eps": [
        "us-gaap:EarningsPerShareBasic",
    ],
    "epsdiluted": [
        "us-gaap:EarningsPerShareDiluted",
    ],
    "weightedAverageShsOut": [
        "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
    ],
    "weightedAverageShsOutDil": [
        "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
    ],
    "ebitda": [
        "us-gaap:EBITDA",
    ],

    # ── Balance Sheet ─────────────────────────────────────────────────
    "cashAndCashEquivalents": [
        "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "us-gaap:CashCashEquivalentsAndShortTermInvestments",
    ],
    "shortTermInvestments": [
        "us-gaap:ShortTermInvestments",
        "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
    ],
    "cashAndShortTermInvestments": [
        "us-gaap:CashCashEquivalentsAndShortTermInvestments",
    ],
    "netReceivables": [
        "us-gaap:AccountsReceivableNetCurrent",
        "us-gaap:ReceivablesNetCurrent",
    ],
    "inventory": [
        "us-gaap:InventoryNet",
    ],
    "otherCurrentAssets": [
        "us-gaap:OtherAssetsCurrent",
        "us-gaap:PrepaidExpenseAndOtherAssetsCurrent",
    ],
    "totalCurrentAssets": [
        "us-gaap:AssetsCurrent",
    ],
    "propertyPlantEquipmentNet": [
        "us-gaap:PropertyPlantAndEquipmentNet",
    ],
    "intangibleAssets": [
        "us-gaap:IntangibleAssetsNetExcludingGoodwill",
        "us-gaap:FiniteLivedIntangibleAssetsNet",
    ],
    "goodwill": [
        "us-gaap:Goodwill",
    ],
    "longTermInvestments": [
        "us-gaap:LongTermInvestments",
        "us-gaap:InvestmentsAndAdvances",
    ],
    "otherNonCurrentAssets": [
        "us-gaap:OtherAssetsNoncurrent",
    ],
    "totalAssets": [
        "us-gaap:Assets",
    ],
    "accountPayables": [
        "us-gaap:AccountsPayableCurrent",
    ],
    "shortTermDebt": [
        "us-gaap:ShortTermBorrowings",
        "us-gaap:DebtCurrent",
    ],
    "otherCurrentLiabilities": [
        "us-gaap:OtherLiabilitiesCurrent",
        "us-gaap:AccruedLiabilitiesCurrent",
    ],
    "totalCurrentLiabilities": [
        "us-gaap:LiabilitiesCurrent",
    ],
    "longTermDebt": [
        "us-gaap:LongTermDebtNoncurrent",
        "us-gaap:LongTermDebt",
    ],
    "otherNonCurrentLiabilities": [
        "us-gaap:OtherLiabilitiesNoncurrent",
    ],
    "totalLiabilities": [
        "us-gaap:Liabilities",
    ],
    "commonStock": [
        "us-gaap:CommonStockValue",
        "us-gaap:CommonStocksIncludingAdditionalPaidInCapital",
    ],
    "retainedEarnings": [
        "us-gaap:RetainedEarningsAccumulatedDeficit",
    ],
    "accumulatedOtherComprehensiveIncomeLoss": [
        "us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",
    ],
    "totalStockholdersEquity": [
        "us-gaap:StockholdersEquity",
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "totalLiabilitiesAndStockholdersEquity": [
        "us-gaap:LiabilitiesAndStockholdersEquity",
    ],
    "totalDebt": [
        "us-gaap:DebtAndCapitalLeaseObligations",
        "us-gaap:LongTermDebtAndCapitalLeaseObligations",
    ],

    # ── Cash Flow ─────────────────────────────────────────────────────
    "depreciationAndAmortization": [
        "us-gaap:DepreciationDepletionAndAmortization",
        "us-gaap:DepreciationAndAmortization",
    ],
    "stockBasedCompensation": [
        "us-gaap:ShareBasedCompensation",
        "us-gaap:AllocatedShareBasedCompensationExpense",
    ],
    "otherNonCashItems": [
        "us-gaap:OtherNoncashIncomeExpense",
    ],
    "accountsReceivables": [
        "us-gaap:IncreaseDecreaseInAccountsReceivable",
    ],
    "accountsPayables": [
        "us-gaap:IncreaseDecreaseInAccountsPayable",
    ],
    "otherWorkingCapital": [
        "us-gaap:IncreaseDecreaseInOtherOperatingCapitalNet",
    ],
    "netCashProvidedByOperatingActivities": [
        "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    ],
    "investmentsInPropertyPlantAndEquipment": [
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
    ],
    "capitalExpenditure": [
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
    ],
    "purchasesOfInvestments": [
        "us-gaap:PaymentsToAcquireInvestments",
        "us-gaap:PaymentsToAcquireAvailableForSaleSecuritiesDebt",
    ],
    "salesMaturitiesOfInvestments": [
        "us-gaap:ProceedsFromSaleAndMaturityOfMarketableSecurities",
        "us-gaap:ProceedsFromMaturitiesPrepaymentsAndCallsOfAvailableForSaleSecurities",
    ],
    "acquisitionsNet": [
        "us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired",
    ],
    "otherInvestingActivites": [
        "us-gaap:PaymentsForProceedsFromOtherInvestingActivities",
    ],
    "netCashUsedForInvestingActivites": [
        "us-gaap:NetCashProvidedByUsedInInvestingActivities",
    ],
    "debtRepayment": [
        "us-gaap:RepaymentsOfDebt",
        "us-gaap:RepaymentsOfLongTermDebt",
    ],
    "commonStockRepurchased": [
        "us-gaap:PaymentsForRepurchaseOfCommonStock",
    ],
    "dividendsPaid": [
        "us-gaap:PaymentsOfDividends",
        "us-gaap:PaymentsOfDividendsCommonStock",
    ],
    "otherFinancingActivites": [
        "us-gaap:ProceedsFromPaymentsForOtherFinancingActivities",
    ],
    "netCashUsedProvidedByFinancingActivities": [
        "us-gaap:NetCashProvidedByUsedInFinancingActivities",
    ],
    "netChangeInCash": [
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
        "us-gaap:CashAndCashEquivalentsPeriodIncreaseDecrease",
    ],
    "freeCashFlow": [
        "us-gaap:FreeCashFlow",
    ],
    "operatingCashFlow": [
        "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    ],

    # ── Key Stats (some overlap with above) ───────────────────────────
    "marketCap": [],
    "enterpriseValue": [],
}


def get_xbrl_concepts(fmp_key: str) -> list[str]:
    return FMP_TO_XBRL.get(fmp_key, [])
