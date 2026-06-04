'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import { marketApi, snaptradeApi, watchlistApi, analysisApi } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '@/contexts/AuthContext';
import PriceRangeChart, { getStockRanges } from '@/components/ui/PriceRangeChart';
import TickerLogo from '@/components/ui/TickerLogo';
import EarningsTab from '@/components/stock/EarningsTab';
import TradesTab from '@/components/stock/TradesTab';
import ChatInput from '@/components/chat/ChatInput';
import type { Position } from '@/lib/types';
import { formatCurrency as fmt, formatCurrencyCompact as fmtB } from '@/lib/currency';

// ─── Helpers ─────────────────────────────────────────────────────────────────
function fmtN(n: number) {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString();
}
function pct(n: number) { return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`; }

// ─── Stat cell ───────────────────────────────────────────────────────────────

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="py-3 border-b border-gray-100">
      <div className="text-xs text-gray-400 mb-0.5">{label}</div>
      <div className="text-[15px] font-semibold text-gray-900 font-numeric">{value}</div>
    </div>
  );
}

// ─── Expandable text ────────────────────────────────────────────────────────

function ExpandableText({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const truncated = text.length > 200;
  return (
    <div className="mt-3">
      <div className={`text-xs text-gray-500 leading-relaxed ${!expanded && truncated ? 'line-clamp-4' : ''}`}>
        {text}
      </div>
      {truncated && (
        <button onClick={() => setExpanded(!expanded)} className="text-xs text-gray-400 hover:text-gray-600 mt-1 font-medium">
          {expanded ? 'Show less' : 'View More'}
        </button>
      )}
    </div>
  );
}

// ─── News card ───────────────────────────────────────────────────────────────

function NewsCard({ item }: { item: any }) {
  const title = item.title || '';
  const url = item.url || '#';
  const site = item.site || item.source || '';
  const date = item.publishedDate || item.date || '';
  const snippet = item.text || '';
  if (!title) return null;

  const timeAgo = (() => {
    if (!date) return '';
    const diff = Date.now() - new Date(date).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
  })();

  return (
    <a href={url} target="_blank" rel="noopener noreferrer"
      className="flex gap-4 px-4 sm:px-0 py-4 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 text-xs text-gray-400 mb-1.5">
          {site && <span className="font-medium">{site}</span>}
          {timeAgo && <span>{timeAgo}</span>}
        </div>
        <div className="text-sm font-semibold text-gray-900 leading-snug mb-1.5 line-clamp-2">{title}</div>
        {snippet && <div className="text-xs text-gray-400 line-clamp-2 leading-relaxed">{snippet}</div>}
      </div>
      {item.image && (
        <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-xl bg-gray-100 overflow-hidden flex-shrink-0">
          <img src={item.image} alt="" className="w-full h-full object-cover" onError={e => (e.currentTarget.style.display = 'none')} />
        </div>
      )}
    </a>
  );
}

// ─── Main ────────────────────────────────────────────────────────────────────

type StockTab = 'overview' | 'earnings' | 'financials' | 'news' | 'related' | 'analysis' | 'trades';
const STOCK_TABS: { key: StockTab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'earnings', label: 'Earnings' },
  { key: 'financials', label: 'Financials' },
  { key: 'news', label: 'News' },
  { key: 'related', label: 'Related' },
  { key: 'analysis', label: 'Analysis' },
  { key: 'trades', label: 'Trades' },
];

type FinancialStatement = 'key-stats' | 'income-statement' | 'balance-sheet' | 'cash-flow' | 'ratios';
type FinancialPeriod = 'annual' | 'quarter' | 'ttm';

const FINANCIAL_STATEMENTS: { key: FinancialStatement; label: string }[] = [
  { key: 'key-stats', label: 'Key Stats' },
  { key: 'income-statement', label: 'Income Statement' },
  { key: 'balance-sheet', label: 'Balance Sheet' },
  { key: 'cash-flow', label: 'Cash Flow' },
  { key: 'ratios', label: 'Ratios' },
];

type FRow =
  | { t: 's'; label: string }
  | { t: 'd'; key: string; label: string; fmt?: 'c' | 'p' | 'r' | 'n'; indent?: boolean }
  | { t: 'g'; of: string; label: string }
  | { t: 'm'; num: string; den: string; label: string };

const STATEMENT_ROWS: Record<FinancialStatement, FRow[]> = {
  'key-stats': [
    { t: 'd', key: 'marketCap', label: 'Market Cap', fmt: 'c' },
    { t: 'd', key: 'cashAndCashEquivalents', label: '- Cash', fmt: 'c', indent: true },
    { t: 'd', key: 'totalDebt', label: '+ Debt', fmt: 'c', indent: true },
    { t: 'd', key: 'enterpriseValue', label: 'Enterprise Value', fmt: 'c' },
    { t: 'd', key: 'revenue', label: 'Revenue', fmt: 'c' },
    { t: 'g', of: 'revenue', label: '% Growth' },
    { t: 'd', key: 'grossProfit', label: 'Gross Profit', fmt: 'c' },
    { t: 'm', num: 'grossProfit', den: 'revenue', label: '% Margin' },
    { t: 'd', key: 'ebitda', label: 'EBITDA', fmt: 'c' },
    { t: 'm', num: 'ebitda', den: 'revenue', label: '% Margin' },
    { t: 'd', key: 'netIncome', label: 'Net Income', fmt: 'c' },
    { t: 'm', num: 'netIncome', den: 'revenue', label: '% Margin' },
    { t: 'd', key: 'epsdiluted', label: 'Diluted EPS', fmt: 'r' },
    { t: 'g', of: 'epsdiluted', label: '% Growth' },
    { t: 'd', key: 'operatingCashFlow', label: 'Operating Cash Flow', fmt: 'c' },
    { t: 'd', key: 'capitalExpenditure', label: 'CapEx', fmt: 'c', indent: true },
    { t: 'd', key: 'freeCashFlow', label: 'Free Cash Flow', fmt: 'c' },
  ],
  'income-statement': [
    { t: 'd', key: 'revenue', label: 'Total Revenues', fmt: 'c' },
    { t: 'd', key: 'costOfRevenue', label: 'Cost of Sales', fmt: 'c', indent: true },
    { t: 'd', key: 'grossProfit', label: 'Gross Profit', fmt: 'c' },
    { t: 'd', key: 'sellingGeneralAndAdministrativeExpenses', label: 'SG&A Expenses', fmt: 'c', indent: true },
    { t: 'd', key: 'researchAndDevelopmentExpenses', label: 'R&D Expenses', fmt: 'c', indent: true },
    { t: 'd', key: 'otherExpenses', label: 'Other Operating Expenses', fmt: 'c', indent: true },
    { t: 'd', key: 'operatingIncome', label: 'Operating Income', fmt: 'c' },
    { t: 'd', key: 'interestIncome', label: 'Interest & Investment Income', fmt: 'c', indent: true },
    { t: 'd', key: 'interestExpense', label: 'Interest Expense', fmt: 'c', indent: true },
    { t: 'd', key: 'totalOtherIncomeExpensesNet', label: 'Non-Operating Income', fmt: 'c', indent: true },
    { t: 'd', key: 'incomeBeforeTax', label: 'Income Before Taxes', fmt: 'c' },
    { t: 'd', key: 'incomeTaxExpense', label: 'Income Tax Expense', fmt: 'c', indent: true },
    { t: 'd', key: 'netIncome', label: 'Net Income', fmt: 'c' },
    { t: 'd', key: 'eps', label: 'Basic EPS', fmt: 'r' },
    { t: 'd', key: 'epsdiluted', label: 'Diluted EPS', fmt: 'r' },
    { t: 'd', key: 'weightedAverageShsOut', label: 'Basic Shares Outstanding', fmt: 'n' },
    { t: 'd', key: 'weightedAverageShsOutDil', label: 'Diluted Shares Outstanding', fmt: 'n' },
    { t: 's', label: 'Margins' },
    { t: 'd', key: 'grossProfitRatio', label: 'Gross Margin', fmt: 'p' },
    { t: 'd', key: 'operatingIncomeRatio', label: 'Operating Margin', fmt: 'p' },
    { t: 'd', key: 'ebitdaratio', label: 'EBITDA Margin', fmt: 'p' },
    { t: 'd', key: 'netIncomeRatio', label: 'Net Profit Margin', fmt: 'p' },
    { t: 'd', key: 'incomeBeforeTaxRatio', label: 'Pre-Tax Profit Margin', fmt: 'p' },
  ],
  'balance-sheet': [
    { t: 's', label: 'Assets' },
    { t: 'd', key: 'cashAndCashEquivalents', label: 'Cash & Cash Equivalents', fmt: 'c', indent: true },
    { t: 'd', key: 'shortTermInvestments', label: 'Short-Term Investments', fmt: 'c', indent: true },
    { t: 'd', key: 'cashAndShortTermInvestments', label: 'Total Cash', fmt: 'c' },
    { t: 'd', key: 'netReceivables', label: 'Accounts Receivable', fmt: 'c', indent: true },
    { t: 'd', key: 'inventory', label: 'Inventories', fmt: 'c', indent: true },
    { t: 'd', key: 'otherCurrentAssets', label: 'Other Current Assets', fmt: 'c', indent: true },
    { t: 'd', key: 'totalCurrentAssets', label: 'Total Current Assets', fmt: 'c' },
    { t: 'd', key: 'propertyPlantEquipmentNet', label: 'Net PP&E', fmt: 'c', indent: true },
    { t: 'd', key: 'intangibleAssets', label: 'Net Intangible Assets', fmt: 'c', indent: true },
    { t: 'd', key: 'goodwill', label: 'Goodwill', fmt: 'c', indent: true },
    { t: 'd', key: 'longTermInvestments', label: 'Long-Term Investments', fmt: 'c', indent: true },
    { t: 'd', key: 'otherNonCurrentAssets', label: 'Other Long-Term Assets', fmt: 'c', indent: true },
    { t: 'd', key: 'totalAssets', label: 'Total Assets', fmt: 'c' },
    { t: 's', label: 'Liabilities' },
    { t: 'd', key: 'accountPayables', label: 'Accounts Payable', fmt: 'c', indent: true },
    { t: 'd', key: 'shortTermDebt', label: 'Short-Term Debt', fmt: 'c', indent: true },
    { t: 'd', key: 'otherCurrentLiabilities', label: 'Other Current Liabilities', fmt: 'c', indent: true },
    { t: 'd', key: 'totalCurrentLiabilities', label: 'Total Current Liabilities', fmt: 'c' },
    { t: 'd', key: 'longTermDebt', label: 'Long-Term Debt', fmt: 'c', indent: true },
    { t: 'd', key: 'otherNonCurrentLiabilities', label: 'Other Long-Term Liabilities', fmt: 'c', indent: true },
    { t: 'd', key: 'totalLiabilities', label: 'Total Liabilities', fmt: 'c' },
    { t: 's', label: 'Equity' },
    { t: 'd', key: 'commonStock', label: 'Common Stock', fmt: 'c', indent: true },
    { t: 'd', key: 'retainedEarnings', label: 'Retained Earnings', fmt: 'c', indent: true },
    { t: 'd', key: 'accumulatedOtherComprehensiveIncomeLoss', label: 'Other Comprehensive Income', fmt: 'c', indent: true },
    { t: 'd', key: 'totalStockholdersEquity', label: 'Total Shareholders\' Equity', fmt: 'c' },
    { t: 'd', key: 'totalLiabilitiesAndStockholdersEquity', label: 'Total Liabilities & Equity', fmt: 'c' },
  ],
  'cash-flow': [
    { t: 's', label: 'Operating Activities' },
    { t: 'd', key: 'netIncome', label: 'Net Income', fmt: 'c', indent: true },
    { t: 'd', key: 'depreciationAndAmortization', label: 'Depreciation & Amortization', fmt: 'c', indent: true },
    { t: 'd', key: 'stockBasedCompensation', label: 'Stock-Based Compensation', fmt: 'c', indent: true },
    { t: 'd', key: 'otherNonCashItems', label: 'Other Adjustments', fmt: 'c', indent: true },
    { t: 'd', key: 'accountsReceivables', label: 'Changes in Receivables', fmt: 'c', indent: true },
    { t: 'd', key: 'inventory', label: 'Changes in Inventories', fmt: 'c', indent: true },
    { t: 'd', key: 'accountsPayables', label: 'Changes in Accounts Payable', fmt: 'c', indent: true },
    { t: 'd', key: 'otherWorkingCapital', label: 'Other Operating Activities', fmt: 'c', indent: true },
    { t: 'd', key: 'netCashProvidedByOperatingActivities', label: 'Cash from Operating Activities', fmt: 'c' },
    { t: 's', label: 'Investing Activities' },
    { t: 'd', key: 'investmentsInPropertyPlantAndEquipment', label: 'Capital Expenditure', fmt: 'c', indent: true },
    { t: 'd', key: 'purchasesOfInvestments', label: 'Purchases of Investments', fmt: 'c', indent: true },
    { t: 'd', key: 'salesMaturitiesOfInvestments', label: 'Proceeds from Investments', fmt: 'c', indent: true },
    { t: 'd', key: 'acquisitionsNet', label: 'Acquisitions', fmt: 'c', indent: true },
    { t: 'd', key: 'otherInvestingActivites', label: 'Other Investing Activities', fmt: 'c', indent: true },
    { t: 'd', key: 'netCashUsedForInvestingActivites', label: 'Cash from Investing Activities', fmt: 'c' },
    { t: 's', label: 'Financing Activities' },
    { t: 'd', key: 'debtRepayment', label: 'Debt Repayment', fmt: 'c', indent: true },
    { t: 'd', key: 'commonStockRepurchased', label: 'Share Repurchases', fmt: 'c', indent: true },
    { t: 'd', key: 'dividendsPaid', label: 'Dividends Paid', fmt: 'c', indent: true },
    { t: 'd', key: 'otherFinancingActivites', label: 'Other Financing Activities', fmt: 'c', indent: true },
    { t: 'd', key: 'netCashUsedProvidedByFinancingActivities', label: 'Cash from Financing Activities', fmt: 'c' },
    { t: 'd', key: 'netChangeInCash', label: 'Net Change in Cash', fmt: 'c' },
  ],
  'ratios': [
    { t: 's', label: 'Valuation' },
    { t: 'd', key: 'priceEarningsRatio', label: 'P/E Ratio', fmt: 'r' },
    { t: 'd', key: 'priceToSalesRatio', label: 'P/S Ratio', fmt: 'r' },
    { t: 'd', key: 'priceToBookRatio', label: 'P/B Ratio', fmt: 'r' },
    { t: 'd', key: 'priceEarningsToGrowthRatio', label: 'PEG Ratio', fmt: 'r' },
    { t: 'd', key: 'enterpriseValueMultiple', label: 'EV/EBITDA', fmt: 'r' },
    { t: 'd', key: 'priceCashFlowRatio', label: 'P/OCF', fmt: 'r' },
    { t: 'd', key: 'priceToFreeCashFlowsRatio', label: 'P/FCF', fmt: 'r' },
    { t: 'd', key: 'dividendYield', label: 'Dividend Yield', fmt: 'p' },
    { t: 's', label: 'Profitability' },
    { t: 'd', key: 'grossProfitMargin', label: 'Gross Margin', fmt: 'p' },
    { t: 'd', key: 'operatingProfitMargin', label: 'Operating Margin', fmt: 'p' },
    { t: 'd', key: 'netProfitMargin', label: 'Net Margin', fmt: 'p' },
    { t: 'd', key: 'effectiveTaxRate', label: 'Effective Tax Rate', fmt: 'p' },
    { t: 's', label: 'Returns' },
    { t: 'd', key: 'returnOnEquity', label: 'Return on Equity', fmt: 'p' },
    { t: 'd', key: 'returnOnAssets', label: 'Return on Assets', fmt: 'p' },
    { t: 'd', key: 'returnOnCapitalEmployed', label: 'ROCE', fmt: 'p' },
    { t: 's', label: 'Liquidity & Leverage' },
    { t: 'd', key: 'currentRatio', label: 'Current Ratio', fmt: 'r' },
    { t: 'd', key: 'quickRatio', label: 'Quick Ratio', fmt: 'r' },
    { t: 'd', key: 'cashRatio', label: 'Cash Ratio', fmt: 'r' },
    { t: 'd', key: 'debtEquityRatio', label: 'Debt/Equity', fmt: 'r' },
    { t: 'd', key: 'debtRatio', label: 'Debt Ratio', fmt: 'r' },
    { t: 'd', key: 'interestCoverage', label: 'Interest Coverage', fmt: 'r' },
    { t: 's', label: 'Efficiency' },
    { t: 'd', key: 'assetTurnover', label: 'Asset Turnover', fmt: 'r' },
    { t: 'd', key: 'inventoryTurnover', label: 'Inventory Turnover', fmt: 'r' },
    { t: 'd', key: 'receivablesTurnover', label: 'Receivables Turnover', fmt: 'r' },
    { t: 'd', key: 'daysOfSalesOutstanding', label: 'Days Sales Outstanding', fmt: 'r' },
    { t: 'd', key: 'daysOfInventoryOutstanding', label: 'Days Inventory Outstanding', fmt: 'r' },
    { t: 's', label: 'Per Share' },
    { t: 'd', key: 'operatingCashFlowPerShare', label: 'OCF/Share', fmt: 'r' },
    { t: 'd', key: 'freeCashFlowPerShare', label: 'FCF/Share', fmt: 'r' },
    { t: 'd', key: 'cashPerShare', label: 'Cash/Share', fmt: 'r' },
    { t: 'd', key: 'payoutRatio', label: 'Payout Ratio', fmt: 'p' },
  ],
};

type DisplayUnit = 'auto' | 'thousands' | 'millions' | 'billions';

function fmtCell(value: any, format?: 'c' | 'p' | 'r' | 'n', unit?: DisplayUnit): string {
  if (value == null || value === '') return '-';
  const n = typeof value === 'number' ? value : parseFloat(value);
  if (isNaN(n)) return '-';
  if (format === 'p') return `${(n * 100).toFixed(1)}%`;
  if (format === 'r') return n.toFixed(2);
  if (format === 'n') return fmtN(n);
  if (unit && unit !== 'auto') {
    const divisor = unit === 'billions' ? 1e9 : unit === 'millions' ? 1e6 : 1e3;
    const v = n / divisor;
    return v.toLocaleString('en-US', { maximumFractionDigits: v >= 100 ? 0 : v >= 1 ? 1 : 2 });
  }
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(0)}M`;
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(0)}K`;
  return `${sign}${abs.toFixed(0)}`;
}

function fmtGrowth(curr: number | null, prev: number | null): string {
  if (curr == null || prev == null || prev === 0) return '-';
  return `${((curr - prev) / Math.abs(prev) * 100).toFixed(1)}%`;
}

function fmtMargin(num: number | null, den: number | null): string {
  if (num == null || den == null || den === 0) return '-';
  return `${(num / den * 100).toFixed(1)}%`;
}

const NO_SEC_SOURCE = new Set([
  'marketCap', 'enterpriseValue', 'ebitda', 'freeCashFlow',
  'grossProfitRatio', 'operatingIncomeRatio', 'ebitdaratio',
  'netIncomeRatio', 'incomeBeforeTaxRatio',
]);

function fmtRawValue(value: number, currency?: string): string {
  const c = currency || 'USD';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: c, minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);
}

function getFilingType(period?: string): string {
  if (!period) return '';
  return period === 'FY' ? '10-K' : '10-Q';
}

type CitationInfo = {
  label: string;
  rawVal: string | null;
  currency: string;
  periodStr: string;
  dateStr: string;
  filingType: string;
  filingDate: string;
  filingLink: string;
  fieldKey: string;
  section: string;
};

function CitationCell({ value, displayValue, col, row, section, onHover, linkCache }: {
  value: any; displayValue: string; col: any; row: { label: string; fmt?: string; key?: string };
  section: string; onHover: (info: CitationInfo | null, rect: DOMRect | null) => void;
  linkCache: React.RefObject<Map<string, string>>;
}) {
  const cellRef = useRef<HTMLSpanElement>(null);

  if (displayValue === '-' || value == null) {
    return <>{displayValue}</>;
  }

  const filingLink = col.finalLink || col.link;

  const handleEnter = () => {
    const rect = cellRef.current?.getBoundingClientRect() ?? null;
    const currency = col.reportedCurrency || 'USD';
    const rawVal = typeof value === 'number' && row.fmt === 'c' ? fmtRawValue(value, currency) : null;
    const fy = col.calendarYear ? `FY ${col.calendarYear}` : '';
    const periodLabel = col.period && col.period !== 'FY' ? `${col.period} ` : '';
    if (row.key && NO_SEC_SOURCE.has(row.key)) return;
    onHover({
      label: row.label, rawVal, currency,
      periodStr: `${periodLabel}${fy}`,
      dateStr: col.date || '',
      filingType: getFilingType(col.period),
      filingDate: col.fillingDate || '',
      filingLink: filingLink || '',
      fieldKey: row.key || '',
      section,
    }, rect);
  };

  const hasSource = row.key && !NO_SEC_SOURCE.has(row.key);

  const getHref = () => {
    if (!filingLink || !row.key || !hasSource) return undefined;
    const cached = linkCache.current?.get(`${filingLink}|${row.key}`);
    return cached || filingLink;
  };

  const href = getHref();

  return (
    <span ref={cellRef} className="inline-block"
      onMouseEnter={handleEnter} onMouseLeave={() => onHover(null, null)}>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer"
          className="hover:text-blue-600 transition-colors">
          {displayValue}
        </a>
      ) : displayValue}
    </span>
  );
}

function FinancialsTab({ symbol, statement, setStatement, period, setPeriod }: {
  symbol: string;
  statement: FinancialStatement; setStatement: (s: FinancialStatement) => void;
  period: FinancialPeriod; setPeriod: (p: FinancialPeriod) => void;
}) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [unit, setUnit] = useState<DisplayUnit>('auto');
  const [showSettings, setShowSettings] = useState(false);
  const [citation, setCitation] = useState<{ info: CitationInfo; anchorRect: DOMRect } | null>(null);
  const [resolvedLink, setResolvedLink] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const citationTimeout = useRef<ReturnType<typeof setTimeout>>();
  const citationCache = useRef<Map<string, string>>(new Map());

  const handleCitationHover = useCallback((info: CitationInfo | null, rect: DOMRect | null) => {
    clearTimeout(citationTimeout.current);
    if (info && rect) {
      setCitation({ info, anchorRect: rect });
    } else {
      citationTimeout.current = setTimeout(() => setCitation(null), 200);
    }
  }, []);

  const keepCitation = useCallback(() => {
    clearTimeout(citationTimeout.current);
  }, []);

  const dismissCitation = useCallback(() => {
    citationTimeout.current = setTimeout(() => setCitation(null), 200);
  }, []);

  useEffect(() => {
    if (!citation?.info.filingLink || !citation?.info.fieldKey) {
      setResolvedLink(null);
      return;
    }
    const { filingLink, fieldKey } = citation.info;
    const cacheKey = `${filingLink}|${fieldKey}`;
    const cached = citationCache.current.get(cacheKey);
    if (cached) { setResolvedLink(cached); return; }
    setResolvedLink(null);
    let cancelled = false;
    marketApi.getSecCitation(filingLink, fieldKey)
      .then(r => {
        if (!cancelled) {
          citationCache.current.set(cacheKey, r.url);
          setResolvedLink(r.url);
        }
      })
      .catch(() => { if (!cancelled) setResolvedLink(filingLink); });
    return () => { cancelled = true; };
  }, [citation?.info.filingLink, citation?.info.fieldKey]);

  useEffect(() => {
    setLoading(true);
    marketApi.getFinancials(symbol, statement, period, 4)
      .then(d => setData(Array.isArray(d) ? d : []))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [symbol, statement, period]);

  const rows = STATEMENT_ROWS[statement];
  const columns = data.slice().sort((a, b) => (b.date || '').localeCompare(a.date || ''));

  const downloadCsv = () => {
    if (!columns.length) return;
    const dates = columns.map(c => c.date || '');
    const csvRows: string[] = [['', ...dates].join(',')];
    for (const row of rows) {
      if (row.t === 's') { csvRows.push(''); csvRows.push(row.label); continue; }
      if (row.t === 'g') {
        const vals = columns.map((col, i) => {
          const curr = col[row.of]; const prev = columns[i + 1]?.[row.of];
          return curr != null && prev != null && prev !== 0 ? `${((curr - prev) / Math.abs(prev) * 100).toFixed(1)}%` : '';
        });
        csvRows.push([`"${row.label}"`, ...vals].join(','));
        continue;
      }
      if (row.t === 'm') {
        const vals = columns.map(col => {
          const n = col[row.num]; const d = col[row.den];
          return n != null && d != null && d !== 0 ? `${(n / d * 100).toFixed(1)}%` : '';
        });
        csvRows.push([`"${row.label}"`, ...vals].join(','));
        continue;
      }
      const vals = columns.map(col => col[row.key] ?? '');
      csvRows.push([`"${row.label}"`, ...vals].join(','));
    }
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${symbol}_${statement}_${period}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  let dataRowIdx = 0;

  return (
    <div ref={containerRef} className="mb-5 rounded-xl border border-gray-200 bg-white overflow-hidden relative">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3 px-4 py-3 border-b border-gray-100">
        <div className="flex gap-1 overflow-x-auto scrollbar-hide -mx-4 px-4 sm:mx-0 sm:px-0">
          {FINANCIAL_STATEMENTS.map(s => (
            <button key={s.key} onClick={() => setStatement(s.key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                statement === s.key
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-500 hover:bg-gray-100'
              }`}>
              {s.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-0.5 bg-gray-100 rounded-lg p-0.5">
            {(['annual', 'quarter', 'ttm'] as const).map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  period === p
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-400 hover:text-gray-600'
                }`}>
                {p === 'annual' ? 'Annual' : p === 'quarter' ? 'Quarterly' : 'TTM'}
              </button>
            ))}
          </div>
          {/* Settings */}
          <div className="relative">
            <button onClick={() => setShowSettings(!showSettings)}
              className="p-1.5 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 12.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 18.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Z" />
              </svg>
            </button>
            {showSettings && (
              <>
                <div className="fixed inset-0 z-20" onClick={() => setShowSettings(false)} />
                <div className="absolute right-0 top-full mt-1 z-30 bg-white rounded-xl shadow-lg border border-gray-200 p-4 w-56">
                  <div className="text-sm font-semibold text-gray-900 mb-3">Display Units</div>
                  <div className="flex gap-0.5 bg-gray-100 rounded-lg p-0.5">
                    {([['auto', 'Auto'], ['thousands', 'K'], ['millions', 'M'], ['billions', 'B']] as const).map(([key, label]) => (
                      <button key={key} onClick={() => setUnit(key as DisplayUnit)}
                        className={`flex-1 px-2 py-1 text-xs font-medium rounded-md transition-colors ${
                          unit === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-400 hover:text-gray-600'
                        }`}>
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
          {/* Download */}
          <button onClick={downloadCsv}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 transition-colors"
            title="Download CSV">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
        </div>
      ) : columns.length === 0 ? (
        <div className="text-sm text-gray-400 py-8 text-center">No financial data available</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[360px] sm:min-w-[600px]">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2.5 px-2 sm:px-4 text-xs font-medium text-gray-400 sm:sticky sm:left-0 bg-white w-[80px] sm:min-w-[180px]" />
                {columns.map((col, i) => {
                  const d = col.date ? new Date(col.date) : null;
                  const label = d
                    ? d.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: 'numeric' })
                    : '';
                  return (
                    <th key={i} className="text-right py-2.5 px-2 sm:px-4 text-xs font-medium text-gray-400 whitespace-nowrap">
                      {label}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => {
                if (row.t === 's') {
                  dataRowIdx = 0;
                  return (
                    <tr key={ri}>
                      <td colSpan={columns.length + 1} className="pt-4 sm:pt-5 pb-1.5 px-2 sm:px-4 text-[11px] sm:text-[13px] font-semibold text-gray-900 border-b border-gray-200">
                        {row.label}
                      </td>
                    </tr>
                  );
                }
                const isEven = dataRowIdx % 2 === 0;
                const stripe = isEven ? 'bg-gray-50/70' : 'bg-white';
                const stickyBg = isEven ? 'bg-[#f8f8f9]' : 'bg-white';
                const isIndent = (row.t === 'g' || row.t === 'm' || (row.t === 'd' && row.indent));
                if (row.t === 'g') {
                  const hasAny = columns.some((_, i) => i < columns.length - 1 && columns[i]?.[row.of] != null && columns[i + 1]?.[row.of] != null);
                  if (!hasAny) return null;
                  dataRowIdx++;
                  return (
                    <tr key={ri} className={stripe}>
                      <td className={`py-2 sm:py-2.5 px-2 sm:px-4 pl-5 sm:pl-8 text-[11px] sm:text-[13px] text-gray-500 sm:sticky sm:left-0 ${stickyBg} max-w-[80px] sm:max-w-none truncate sm:overflow-visible sm:text-clip whitespace-nowrap`} title={row.label}>{row.label}</td>
                      {columns.map((col, i) => (
                        <td key={i} className="text-right py-2 sm:py-2.5 px-2 sm:px-4 tabular-nums text-[12px] sm:text-[13px] text-gray-600 whitespace-nowrap">
                          {fmtGrowth(col[row.of], columns[i + 1]?.[row.of] ?? null)}
                        </td>
                      ))}
                    </tr>
                  );
                }
                if (row.t === 'm') {
                  const hasAny = columns.some(col => col[row.num] != null && col[row.den] != null);
                  if (!hasAny) return null;
                  dataRowIdx++;
                  return (
                    <tr key={ri} className={stripe}>
                      <td className={`py-2 sm:py-2.5 px-2 sm:px-4 pl-5 sm:pl-8 text-[11px] sm:text-[13px] text-gray-500 sm:sticky sm:left-0 ${stickyBg} max-w-[80px] sm:max-w-none truncate sm:overflow-visible sm:text-clip whitespace-nowrap`} title={row.label}>{row.label}</td>
                      {columns.map((col, i) => (
                        <td key={i} className="text-right py-2 sm:py-2.5 px-2 sm:px-4 tabular-nums text-[12px] sm:text-[13px] text-gray-600 whitespace-nowrap">
                          {fmtMargin(col[row.num], col[row.den])}
                        </td>
                      ))}
                    </tr>
                  );
                }
                const hasAnyValue = columns.some(col => col[row.key] != null && col[row.key] !== 0);
                if (!hasAnyValue) return null;
                dataRowIdx++;
                return (
                  <tr key={ri} className={`${stripe} hover:bg-gray-100/50 transition-colors`}>
                    <td className={`py-2 sm:py-2.5 px-2 sm:px-4 sm:sticky sm:left-0 ${stickyBg} max-w-[80px] sm:max-w-none truncate sm:overflow-visible sm:text-clip whitespace-nowrap ${
                      isIndent ? 'pl-5 sm:pl-8 text-gray-500 text-[11px] sm:text-[13px]' : 'text-gray-800 font-medium text-[11px] sm:text-[13px]'
                    }`} title={row.label}>
                      {row.label}
                    </td>
                    {columns.map((col, i) => (
                      <td key={i} className={`group/cell text-right py-2 sm:py-2.5 px-2 sm:px-4 tabular-nums whitespace-nowrap ${
                        isIndent ? 'text-[12px] sm:text-[13px] text-gray-600' : 'text-[12px] sm:text-[13px] text-gray-900'
                      }`}>
                        <CitationCell
                          value={col[row.key]}
                          displayValue={fmtCell(col[row.key], row.fmt, row.fmt === 'c' ? unit : undefined)}
                          col={col}
                          row={{ label: row.label, fmt: row.fmt, key: row.key }}
                          section={FINANCIAL_STATEMENTS.find(s => s.key === statement)?.label || statement}
                          onHover={handleCitationHover}
                          linkCache={citationCache}
                        />
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {citation && containerRef.current && (() => {
        const cRect = containerRef.current!.getBoundingClientRect();
        const aRect = citation.anchorRect;
        const tooltipW = 240;
        const gap = 12;
        const left = aRect.left - cRect.left - tooltipW - gap;
        const top = aRect.top - cRect.top + aRect.height / 2 - 60;
        const info = citation.info;
        return (
          <div
            className="absolute z-50 w-60 bg-gray-900 text-white rounded-lg shadow-xl border border-gray-700 p-3 text-left"
            style={{ left: Math.max(8, left), top: Math.max(8, top) }}
            onMouseEnter={keepCitation} onMouseLeave={dismissCitation}
          >
            <div className="text-xs font-medium text-gray-300 mb-2">{info.label}</div>
            {info.rawVal && (
              <div className="text-xs mb-1.5">
                <span className="text-gray-500">As Reported</span>
                <div className="text-white font-medium">{info.currency} {info.rawVal}</div>
              </div>
            )}
            {info.periodStr && (
              <div className="text-xs mb-1.5">
                <span className="text-gray-500">Period</span>
                {info.dateStr && <div className="text-gray-300">ended {info.dateStr}</div>}
                <div className="text-gray-300">{info.periodStr}</div>
              </div>
            )}
            {(resolvedLink || info.filingLink) && (
              <a href={resolvedLink || info.filingLink} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-700 text-blue-400 hover:text-blue-300 transition-colors"
                onClick={e => e.stopPropagation()}>
                {info.filingType && (
                  <span className="text-[10px] font-bold bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded shrink-0">{info.filingType}</span>
                )}
                <span className="text-[11px]">
                  {info.section} → {info.label}
                </span>
                <svg className="w-3 h-3 ml-auto shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            )}
            {info.filingDate && (
              <div className="text-[10px] text-gray-500 mt-1">Filed {info.filingDate}</div>
            )}
          </div>
        );
      })()}
    </div>
  );
}

export default function StockPage({ symbol, initialTab }: { symbol: string; initialTab?: string }) {
  const { goBack, canGoBack, openChatAbout, openStock } = useNavigation();
  const { user } = useAuth();
  const [quote, setQuote] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [news, setNews] = useState<any[]>([]);
  const [newsLimit, setNewsLimit] = useState(12);
  const [newsLoadingMore, setNewsLoadingMore] = useState(false);
  const [newsExhausted, setNewsExhausted] = useState(false);
  const [peers, setPeers] = useState<any[]>([]);
  const [position, setPosition] = useState<Position | null>(null);
  const [loading, setLoading] = useState(true);
  const [watchlisted, setWatchlisted] = useState(false);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [hoverPct, setHoverPct] = useState<number | null>(null);
  const [periodPct, setPeriodPct] = useState<number | null>(null);
  const [chartDays, setChartDays] = useState(1);
  const [activeTab, setActiveTab] = useState<StockTab>(
    (initialTab && STOCK_TABS.some(t => t.key === initialTab) ? initialTab : 'overview') as StockTab
  );
  const [analyst, setAnalyst] = useState<any>(null);
  const [earningsHistory, setEarningsHistory] = useState<any[]>([]);
  const [finStatement, setFinStatement] = useState<FinancialStatement>('key-stats');
  const [finPeriod, setFinPeriod] = useState<FinancialPeriod>('annual');
  const [aiNotes, setAiNotes] = useState<{ id: string; title: string | null; content: string; created_at: string | null; updated_at: string | null; chat_id: string | null }[]>([]);
  const [expandedNote, setExpandedNote] = useState<string | null>(null);

  useEffect(() => {
    if (initialTab && STOCK_TABS.some(t => t.key === initialTab)) {
      setActiveTab(initialTab as StockTab);
    }
  }, [initialTab, symbol]);

  const fetchData = useCallback(() => {
    setLoading(true);
    setPosition(null);
    setNews([]);
    setNewsLimit(12);
    setNewsExhausted(false);
    setPeers([]);

    marketApi.getQuote(symbol).catch(() => null).then(q => {
      setQuote(q);
      setLoading(false);
    });
    marketApi.getProfile(symbol).catch(() => null).then(p => setProfile(p));

    marketApi.getNews(symbol, 12).catch(() => []).then(n => setNews(Array.isArray(n) ? n : []));
    marketApi.getPeers(symbol, 6).catch(() => []).then(pe => setPeers(Array.isArray(pe) ? pe : []));
    marketApi.getAnalyst(symbol).catch(() => null).then(a => setAnalyst(a));
    marketApi.getEarningsHistory(symbol, 12).catch(() => []).then(e => setEarningsHistory(Array.isArray(e) ? e : []));
    analysisApi.get(symbol).catch(() => ({ notes: [] })).then(a => {
      const notes = a?.notes || [];
      setAiNotes(notes);
      if (notes.length > 0) setExpandedNote(notes[0].id);
    });

    if (user) {
      snaptradeApi.getPortfolio(user.id).catch(() => null).then(portfolio => {
        const positions = portfolio?.accounts?.flatMap(a => a.positions) || [];
        const pos = positions.find((x) => x.symbol === symbol);
        if (pos) setPosition(pos);
      });
      watchlistApi.getWatchlist(user.id).catch(() => ({ symbols: [] })).then(wl => {
        if (wl?.symbols) setWatchlisted(wl.symbols.some((s: any) => s.symbol === symbol));
      });
    }
  }, [symbol, user]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const loadMoreNews = useCallback(async () => {
    setNewsLoadingMore(true);
    const next = newsLimit + 12;
    try {
      const n = await marketApi.getNews(symbol, next);
      const arr = Array.isArray(n) ? n : [];
      // If the API returned no additional items, we've hit the end.
      if (arr.length <= news.length) setNewsExhausted(true);
      setNews(arr);
      setNewsLimit(next);
    } catch {
      setNewsExhausted(true);
    } finally {
      setNewsLoadingMore(false);
    }
  }, [symbol, newsLimit, news.length]);


  const price = quote?.price || profile?.price || 0;
  const change = quote?.change || profile?.changes || 0;
  const changePct = quote?.changesPercentage || 0;
  const previousClose = quote?.previousClose || 0;
  const marketSession = quote?.marketSession as string | undefined;
  const name = profile?.companyName || quote?.name || symbol;

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header — spans full width above the two-column layout */}
      <div className="px-4 sm:px-6 pt-4 pb-0 shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {canGoBack && (
              <button onClick={goBack} className="p-1 -ml-1 text-gray-400 hover:text-gray-600 transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                </svg>
              </button>
            )}
            <TickerLogo symbol={symbol} size={40} rounded="rounded-xl" />
            <div>
              <div className="text-lg sm:text-xl font-bold text-gray-900">{name}</div>
              <div className="text-xs text-gray-400">{symbol}{profile?.exchange ? ` · ${profile.exchange}` : ''}</div>
            </div>
          </div>
          <button onClick={async () => {
            if (!user || watchlistLoading) return;
            setWatchlistLoading(true);
            try {
              if (watchlisted) { await watchlistApi.removeSymbol(user.id, symbol); setWatchlisted(false); }
              else { await watchlistApi.addSymbol(user.id, symbol); setWatchlisted(true); }
            } catch {} finally { setWatchlistLoading(false); }
          }}
            className={`p-2 rounded-lg transition-colors ${watchlisted ? 'text-amber-500' : 'text-gray-300 hover:text-gray-500'}`}>
            <svg className="w-5 h-5" fill={watchlisted ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
            </svg>
          </button>
        </div>

        {/* Tab bar — below name, spans full width */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-6 -mb-px overflow-x-auto scrollbar-hide">
            {STOCK_TABS.map(tab => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`whitespace-nowrap py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? 'border-gray-900 text-gray-900'
                    : 'border-transparent text-gray-400 hover:text-gray-600'
                }`}>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Two-column layout below tabs */}
      <div className="flex flex-1 min-h-0">
        {/* Main content (scrollable) */}
        <div className="flex-1 overflow-y-auto">

        {/* Chart + Price — only on Overview */}
        {activeTab === 'overview' && (
          <>
            <div className="px-4 sm:px-6 pt-4 pb-2">
              {(() => {
                const endPct = periodPct ?? changePct;
                const periodStart = price / (1 + endPct / 100 || 1);
                const activePct = hoverPct ?? endPct;
                const displayPrice = hoverPct !== null
                  ? periodStart * (1 + hoverPct / 100)
                  : price;
                const displayDollar = periodStart * (activePct / 100);
                const up = displayDollar >= 0;

                const isExtended = marketSession === 'pre' || marketSession === 'after';
                const is1D = chartDays === 1;
                const showExtended = isExtended && is1D && previousClose > 0 && hoverPct === null;

                const closeChange = change;
                const closePct = changePct;
                const closeUp = closeChange >= 0;

                return (
                  <>
                    <div className="mb-1">
                      <span className="text-3xl sm:text-4xl font-bold text-gray-900 font-numeric">{fmt(displayPrice, symbol)}</span>
                    </div>
                    <div className={`text-sm font-medium font-numeric ${up ? 'text-emerald-600' : 'text-red-500'}`}>
                      {up ? '+' : '-'}{fmt(Math.abs(displayDollar), symbol)} ({pct(activePct)})
                    </div>
                    {showExtended && (
                      <div className="flex items-center gap-1.5 mt-1">
                        <span className={`text-xs font-medium tabular-nums ${closeUp ? 'text-emerald-500' : 'text-red-400'}`}>
                          {closeUp ? '+' : ''}{fmt(closeChange, symbol)} ({pct(closePct)})
                        </span>
                        <span className="text-xs text-gray-400">
                          from prev close · {marketSession === 'pre' ? 'Pre-market' : 'After hours'}
                        </span>
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
            <div className="px-2 sm:px-4">
              <PriceRangeChart
                series={[{ symbol, color: '' }]}
                currentPrice={price}
                previousClose={previousClose}
                defaultDays={1}
                ranges={getStockRanges()}
                height={280}
                hideHeader
                onHoverChange={info => {
                  setHoverPct(info?.value ?? null);
                }}
                onPeriodChange={setPeriodPct}
                onRangeChange={(d) => setChartDays(d)}
              />
            </div>

            {/* Mobile action */}
            <div className="lg:hidden px-4 py-3 flex gap-2">
              <button onClick={() => openChatAbout(symbol)}
                className="flex-1 py-3 text-sm font-bold text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors">
                Ask AI
              </button>
            </div>
          </>
        )}

        {/* Tab content */}
        <div className="px-4 sm:px-6 pt-5">
          {activeTab === 'overview' && (
            <>
              {/* Your position */}
              {position && (
                <div className="mb-5 rounded-xl border border-emerald-100 bg-emerald-50/30 p-4">
                  <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Your Position</div>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-lg font-bold text-gray-900 tabular-nums">{fmt(position.value || 0, symbol)}</div>
                      <div className="text-xs text-gray-400">
                        {position.quantity} shares @ {fmt(position.average_purchase_price || 0, symbol)}
                      </div>
                    </div>
                    {position.gain_loss != null && (
                      <div className="text-right">
                        <div className={`text-sm font-bold tabular-nums ${position.gain_loss >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                          {position.gain_loss >= 0 ? '+' : ''}{fmt(position.gain_loss, symbol)}
                        </div>
                        {position.gain_loss_percent != null && (
                          <div className={`text-xs tabular-nums ${position.gain_loss_percent >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                            {pct(position.gain_loss_percent)}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Key Statistics */}
              {quote && (
                <div className="mb-5">
                  <div className="text-base font-bold text-gray-900 mb-3">Key Statistics</div>
                  <div className="border-t border-gray-100" />
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6">
                    <Stat label="Market Cap" value={fmtB(quote.marketCap || profile?.mktCap || 0, symbol)} />
                    <Stat label="P/E Ratio" value={quote.pe ? quote.pe.toFixed(2) : '--'} />
                    {(quote.dividendYielPercentageTTM || profile?.lastDiv) && (
                      <Stat label="Dividend Yield" value={quote.dividendYielPercentageTTM ? `${quote.dividendYielPercentageTTM.toFixed(2)}%` : profile?.lastDiv ? `$${profile.lastDiv.toFixed(2)}` : '--'} />
                    )}
                    <Stat label="Avg Volume" value={fmtN(quote.avgVolume || 0)} />
                    <Stat label="High Today" value={fmt(quote.dayHigh || 0, symbol)} />
                    <Stat label="Low Today" value={fmt(quote.dayLow || 0, symbol)} />
                    <Stat label="Open" value={fmt(quote.open || 0, symbol)} />
                    <Stat label="Volume" value={fmtN(quote.volume || 0)} />
                    <Stat label="52 Week High" value={fmt(quote.yearHigh || 0, symbol)} />
                    <Stat label="52 Week Low" value={fmt(quote.yearLow || 0, symbol)} />
                    <Stat label="EPS" value={quote.eps ? fmt(quote.eps, symbol) : '--'} />
                    {profile?.beta && <Stat label="Beta" value={profile.beta.toFixed(2)} />}
                  </div>
                </div>
              )}

            </>
          )}

          {activeTab === 'earnings' && (
            <EarningsTab symbol={symbol} earningsHistory={earningsHistory} />
          )}

          {activeTab === 'financials' && (
            <FinancialsTab symbol={symbol} statement={finStatement} setStatement={setFinStatement} period={finPeriod} setPeriod={setFinPeriod} />
          )}

          {activeTab === 'news' && (
            <div className="mb-5">
              {news.length > 0 ? (
                <>
                  {news.map((item, i) => <NewsCard key={i} item={item} />)}
                  {!newsExhausted && (
                    <button
                      onClick={loadMoreNews}
                      disabled={newsLoadingMore}
                      className="mt-3 w-full py-2.5 text-sm font-semibold text-gray-600 hover:text-gray-900 border border-gray-200 hover:border-gray-300 hover:bg-gray-50 rounded-xl transition-colors disabled:opacity-50"
                    >
                      {newsLoadingMore ? 'Loading…' : 'Load more news'}
                    </button>
                  )}
                </>
              ) : (
                <div className="text-sm text-gray-400 py-8 text-center">No recent news</div>
              )}
            </div>
          )}

          {activeTab === 'related' && (
            <div className="mb-5">
              {peers.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {peers.map(p => (
                    <button key={p.symbol} onClick={() => openStock(p.symbol)}
                      className="text-left rounded-xl border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/30 p-3 hover-lift">
                      <div className="flex items-center gap-2 mb-1.5">
                        <TickerLogo symbol={p.symbol} size={28} />
                        <div className="min-w-0">
                          <div className="text-sm font-bold text-gray-900">{p.symbol}</div>
                          {p.name && <div className="text-xs text-gray-400 truncate">{p.name}</div>}
                        </div>
                      </div>
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="text-sm font-semibold text-gray-900 tabular-nums">{p.price != null ? fmt(p.price, symbol) : '--'}</span>
                        {p.marketCap != null && (
                          <span className="text-xs font-medium text-gray-400 tabular-nums">{fmtB(p.marketCap, symbol)}</span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-gray-400 py-8 text-center">No related stocks found</div>
              )}
            </div>
          )}

          {activeTab === 'analysis' && (
            <div className="mb-5">
              {/* AI research notes */}
              {aiNotes.length > 0 && (
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-6 h-6 rounded-lg flex items-center justify-center"
                      style={{ background: '#ecfdf5' }}>
                      <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
                      </svg>
                    </div>
                    <span className="text-sm font-bold text-gray-900">AI Research Notes</span>
                    <span className="text-[11px] text-gray-400">{aiNotes.length} note{aiNotes.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="space-y-2">
                    {aiNotes.map(note => {
                      const isExpanded = expandedNote === note.id;
                      return (
                        <div key={note.id} className="rounded-xl border border-gray-200 overflow-hidden">
                          <button
                            onClick={() => setExpandedNote(isExpanded ? null : note.id)}
                            className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors text-left"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <svg className={`w-3.5 h-3.5 text-gray-400 shrink-0 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                                fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                              </svg>
                              <span className="text-sm font-medium text-gray-900 truncate">
                                {note.title || `Research Note`}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 shrink-0 ml-2">
                              {note.created_at && (
                                <span className="text-[11px] text-gray-400">
                                  {new Date(note.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                </span>
                              )}
                              {note.chat_id && (
                                <span
                                  onClick={e => { e.stopPropagation(); openChatAbout(symbol, undefined, { page: 'stock', symbol, name }); }}
                                  className="text-[11px] text-emerald-600 hover:text-emerald-700 font-medium cursor-pointer"
                                >
                                  Chat
                                </span>
                              )}
                            </div>
                          </button>
                          {isExpanded && (
                            <div className="px-5 pb-5 prose prose-sm prose-gray max-w-none
                              prose-headings:text-gray-900 prose-headings:font-bold prose-headings:mt-4 prose-headings:mb-2
                              prose-p:text-gray-600 prose-p:leading-relaxed
                              prose-li:text-gray-600
                              prose-strong:text-gray-900
                              prose-a:text-emerald-600 prose-a:no-underline hover:prose-a:underline">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{note.content}</ReactMarkdown>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Analyst Consensus + Price Targets */}
              {analyst?.grades && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                  {/* Consensus */}
                  <div className="rounded-xl border border-gray-200 p-4">
                    <div className="text-sm font-bold text-gray-900 mb-3">Analyst Consensus</div>
                    <div className="flex items-center gap-4 mb-3">
                      <div className="text-center">
                        <div className="text-xs text-gray-400 uppercase tracking-wide">Consensus</div>
                        <div className={`text-lg font-bold ${
                          analyst.grades.consensus === 'Buy' ? 'text-emerald-600' :
                          analyst.grades.consensus === 'Sell' ? 'text-red-500' : 'text-gray-600'
                        }`}>{analyst.grades.consensus === 'Buy' ? 'Strong Buy' : analyst.grades.consensus}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-400 uppercase tracking-wide">Bullish</div>
                        <div className="text-lg font-bold text-emerald-600">{analyst.grades.buy}</div>
                        <div className="text-[11px] text-gray-400">{analyst.grades.total > 0 ? ((analyst.grades.buy / analyst.grades.total) * 100).toFixed(1) : 0}%</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-400 uppercase tracking-wide">Neutral</div>
                        <div className="text-lg font-bold text-gray-600">{analyst.grades.neutral}</div>
                        <div className="text-[11px] text-gray-400">{analyst.grades.total > 0 ? ((analyst.grades.neutral / analyst.grades.total) * 100).toFixed(1) : 0}%</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-400 uppercase tracking-wide">Bearish</div>
                        <div className="text-lg font-bold text-red-500">{analyst.grades.sell}</div>
                        <div className="text-[11px] text-gray-400">{analyst.grades.total > 0 ? ((analyst.grades.sell / analyst.grades.total) * 100).toFixed(1) : 0}%</div>
                      </div>
                    </div>
                  </div>

                  {/* Price Targets */}
                  {analyst.consensus && (
                    <div className="rounded-xl border border-gray-200 p-4">
                      <div className="text-sm font-bold text-gray-900 mb-3">Analyst 52W Price Targets</div>
                      <div className="flex justify-between text-xs mb-3">
                        <div><span className="text-base font-bold text-gray-900">{fmt(analyst.consensus.targetLow || 0, symbol)}</span><br/><span className="text-red-400">Low</span></div>
                        <div className="text-center"><span className="text-base font-bold text-gray-900">{fmt(price, symbol)}</span><br/><span className="text-gray-400">Current</span></div>
                        <div className="text-center"><span className="text-base font-bold text-gray-900">{fmt(analyst.consensus.targetMedian || analyst.consensus.targetConsensus || 0, symbol)}</span><br/><span className="text-emerald-500">Average</span></div>
                        <div className="text-right"><span className="text-base font-bold text-gray-900">{fmt(analyst.consensus.targetHigh || 0, symbol)}</span><br/><span className="text-blue-500">High</span></div>
                      </div>
                      {(() => {
                        const low = analyst.consensus.targetLow || 0;
                        const high = analyst.consensus.targetHigh || 0;
                        const range = high - low || 1;
                        const currentPos = Math.max(0, Math.min(100, ((price - low) / range) * 100));
                        const avgTarget = analyst.consensus.targetMedian || analyst.consensus.targetConsensus || 0;
                        const avgPos = Math.max(0, Math.min(100, ((avgTarget - low) / range) * 100));
                        return (
                          <div className="relative h-2.5 bg-gray-100 rounded-full">
                            <div className="absolute top-0 h-full bg-gradient-to-r from-red-300 via-gray-200 to-emerald-300 rounded-full" style={{ left: 0, right: 0 }} />
                            <div className="absolute top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full border-2 border-white bg-gray-900 shadow" style={{ left: `${currentPos}%`, marginLeft: -7 }} />
                            <div className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-emerald-500 shadow" style={{ left: `${avgPos}%`, marginLeft: -5 }} />
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              )}

              {/* Individual Analyst Grades Table */}
              {analyst?.rawGrades && analyst.rawGrades.length > 0 && (
                <div className="mb-6">
                  <div className="overflow-x-auto -mx-4 sm:mx-0">
                    <table className="w-full text-sm min-w-[400px]">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-2.5 px-3 text-xs font-medium text-gray-400">Firm</th>
                          <th className="text-left py-2.5 px-3 text-xs font-medium text-gray-400">Rating</th>
                          <th className="text-right py-2.5 px-3 text-xs font-medium text-gray-400">Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analyst.rawGrades.map((g: any, i: number) => {
                          const rating = g.rating || '';
                          const previous = g.previous || '';
                          const isPositive = /buy|overweight|outperform|strong buy/i.test(rating);
                          const isNegative = /sell|underweight|underperform/i.test(rating);
                          const changed = previous && previous !== rating;
                          return (
                            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                              <td className="py-2.5 px-3 font-medium text-gray-900">{g.firm}</td>
                              <td className="py-2.5 px-3">
                                <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                                  isPositive ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                                  isNegative ? 'bg-red-50 text-red-600 border border-red-200' :
                                  'bg-gray-50 text-gray-600 border border-gray-200'
                                }`}>
                                  {rating}
                                </span>
                                {changed && (
                                  <span className="text-[11px] text-gray-400 ml-1.5">from {previous}</span>
                                )}
                              </td>
                              <td className="py-2.5 px-3 text-right text-gray-500 tabular-nums whitespace-nowrap">
                                {g.date ? new Date(g.date).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: 'numeric' }) : ''}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* AI Analyst */}
              <div className="max-w-lg">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                    style={{ background: '#ecfdf5' }}>
                    <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
                    </svg>
                  </div>
                  <div className="text-sm font-bold text-gray-900 tracking-tight">AI Analyst</div>
                </div>
                <p className="text-xs text-gray-500 leading-relaxed mb-4">
                  Ask anything about {symbol} — fundamentals, price action, news, or peers.
                </p>
                <div className="space-y-1.5 mb-4">
                  {[
                    `What's moving ${symbol} today?`,
                    `Summarize the latest news on ${symbol}`,
                    `How does ${symbol} compare to its peers?`,
                    `What are the key risks for ${symbol}?`,
                  ].map(prompt => (
                    <button key={prompt} onClick={() => openChatAbout(symbol, prompt)}
                      className="group w-full text-left text-[13px] text-gray-600 hover:text-gray-900 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-between gap-2">
                      <span className="line-clamp-1">{prompt}</span>
                      <svg className="w-3.5 h-3.5 text-gray-300 group-hover:text-emerald-500 shrink-0 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                      </svg>
                    </button>
                  ))}
                </div>
                <button onClick={() => openChatAbout(symbol)}
                  className="w-full py-2.5 text-sm font-semibold text-white rounded-xl transition-all hover:shadow-md flex items-center justify-center gap-2"
                  style={{ background: '#0f172a' }}>
                  Start analysis
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {activeTab === 'trades' && (
            <TradesTab symbol={symbol} currentPrice={price} />
          )}
        </div>

        {/* Sticky chat bar — full-width fade so wide tables scroll under it
            cleanly instead of peeking out beside a narrow floating box. */}
        <div className="sticky bottom-0 px-3 sm:px-4 pt-8 pb-2 bg-gradient-to-t from-white via-white/95 to-transparent pointer-events-none">
          <div className="max-w-3xl pointer-events-auto">
          <ChatInput
            onSimpleSend={(msg) => openChatAbout(symbol, msg, {
              page: 'stock',
              symbol,
              name,
              tab: activeTab,
              price,
              change,
              changePct,
              ...(profile && { sector: profile.sector, industry: profile.industry, marketCap: profile.mktCap }),
              ...(analyst?.grades && { analystConsensus: analyst.grades.consensus, analystCount: analyst.grades.total }),
              ...(analyst?.consensus && { priceTarget: analyst.consensus.targetConsensus }),
              ...(position && { userPosition: { shares: position.quantity, avgCost: position.average_purchase_price || 0, unrealizedPL: position.gain_loss || 0 } }),
            })}
            placeholder={`Ask about ${symbol}...`}
          />
          </div>
        </div>
      </div>

      {/* Desktop right sidebar — company info, analyst, earnings */}
      <aside className={`${activeTab === 'financials' ? 'hidden' : 'hidden lg:flex'} flex-col w-[340px] shrink-0 border-l border-gray-100 overflow-y-auto`}>
        {/* Company Info Table */}
        {profile && (
          <div className="p-5 border-b border-gray-100">
            <div className="rounded-xl border border-gray-200 overflow-hidden">
              {[
                ['Symbol', symbol],
                profile.ipoDate && ['IPO Date', profile.ipoDate],
                profile.ceo && ['CEO', profile.ceo],
                profile.fullTimeEmployees && ['Employees', fmtN(profile.fullTimeEmployees)],
                profile.sector && ['Sector', profile.sector],
                profile.industry && ['Industry', profile.industry],
                profile.country && ['Country', profile.country],
                profile.exchange && ['Exchange', profile.exchange],
              ].filter(Boolean).map(([label, value], i) => (
                <div key={i} className={`flex items-center justify-between px-3.5 py-2.5 text-sm ${i > 0 ? 'border-t border-gray-100' : ''}`}>
                  <span className="text-gray-500">{label as string}</span>
                  <span className="font-medium text-gray-900 text-right max-w-[180px] truncate">{value as string}</span>
                </div>
              ))}
            </div>
            {profile.description && (
              <ExpandableText text={profile.description} />
            )}
          </div>
        )}

        {/* Analyst Consensus — hidden on the analysis tab, where it's the main content */}
        {analyst?.grades && activeTab !== 'analysis' && (
          <div className="p-5 border-b border-gray-100 cursor-pointer hover:bg-gray-50/50 transition-colors" onClick={() => setActiveTab('analysis')}>
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-bold text-gray-900">Analyst Consensus</div>
              <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                analyst.grades.consensus === 'Buy' ? 'bg-emerald-100 text-emerald-700' :
                analyst.grades.consensus === 'Sell' ? 'bg-red-100 text-red-600' :
                'bg-gray-100 text-gray-600'
              }`}>
                {analyst.grades.consensus}
              </span>
              <span className="text-xs text-gray-400">{analyst.grades.total} analysts</span>
            </div>
            {/* Grade bar */}
            <div className="flex gap-0.5 mb-2 h-2 rounded-full overflow-hidden">
              {analyst.grades.sell > 0 && (
                <div className="bg-red-400 rounded-l-full" style={{ flex: analyst.grades.sell }} />
              )}
              {analyst.grades.neutral > 0 && (
                <div className="bg-gray-300" style={{ flex: analyst.grades.neutral }} />
              )}
              {analyst.grades.buy > 0 && (
                <div className="bg-emerald-500 rounded-r-full" style={{ flex: analyst.grades.buy }} />
              )}
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-red-500 font-medium">{analyst.grades.sell} Bearish</span>
              <span className="text-gray-400 font-medium">{analyst.grades.neutral} Neutral</span>
              <span className="text-emerald-600 font-medium">{analyst.grades.buy} Bullish</span>
            </div>

            {/* Price targets */}
            {analyst.consensus && (
              <div className="mt-4">
                <div className="flex justify-between text-xs mb-1">
                  <div><span className="font-bold text-gray-900">{fmt(analyst.consensus.targetLow || 0, symbol)}</span><br/><span className="text-red-400">Low</span></div>
                  <div className="text-center"><span className="font-bold text-gray-900">{fmt(price, symbol)}</span><br/><span className="text-gray-400">Current</span></div>
                  <div className="text-center"><span className="font-bold text-gray-900">{fmt(analyst.consensus.targetMedian || analyst.consensus.targetConsensus || 0, symbol)}</span><br/><span className="text-emerald-500">Average</span></div>
                  <div className="text-right"><span className="font-bold text-gray-900">{fmt(analyst.consensus.targetHigh || 0, symbol)}</span><br/><span className="text-blue-500">High</span></div>
                </div>
                {/* Range visualization */}
                {(() => {
                  const low = analyst.consensus.targetLow || 0;
                  const high = analyst.consensus.targetHigh || 0;
                  const range = high - low || 1;
                  const currentPos = Math.max(0, Math.min(100, ((price - low) / range) * 100));
                  const avgTarget = analyst.consensus.targetMedian || analyst.consensus.targetConsensus || 0;
                  const avgPos = Math.max(0, Math.min(100, ((avgTarget - low) / range) * 100));
                  return (
                    <div className="relative h-2 bg-gray-100 rounded-full mt-2">
                      <div className="absolute top-0 h-full bg-gradient-to-r from-red-300 via-gray-200 to-emerald-300 rounded-full" style={{ left: 0, right: 0 }} />
                      <div className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-white bg-gray-900 shadow" style={{ left: `${currentPos}%`, marginLeft: -6 }} />
                      <div className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-emerald-500 shadow" style={{ left: `${avgPos}%`, marginLeft: -4 }} />
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {/* Earnings History */}
        {earningsHistory.length > 0 && (
          <div className="p-5 border-b border-gray-100">
            <div className="text-sm font-bold text-gray-900 mb-3">Earnings History</div>
            <div className="space-y-2">
              {earningsHistory.slice(-6).map((e, i) => {
                const beat = e.eps != null && e.epsEstimated != null && e.eps > e.epsEstimated;
                const miss = e.eps != null && e.epsEstimated != null && e.eps < e.epsEstimated;
                const quarter = e.date ? new Date(e.date).toLocaleDateString('en-US', { month: 'short', year: '2-digit' }) : '';
                return (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-gray-500 w-16">{quarter}</span>
                    <div className="flex items-center gap-3 flex-1 justify-end">
                      <span className="text-gray-400">Est: ${e.epsEstimated?.toFixed(2) ?? '--'}</span>
                      <span className={`font-bold ${beat ? 'text-emerald-600' : miss ? 'text-red-500' : 'text-gray-600'}`}>
                        ${e.eps?.toFixed(2) ?? '--'}
                      </span>
                      {beat && <span className="w-2 h-2 rounded-full bg-emerald-500" />}
                      {miss && <span className="w-2 h-2 rounded-full bg-red-400" />}
                      {!beat && !miss && <span className="w-2 h-2 rounded-full bg-gray-300" />}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-3 mt-3 text-[10px] text-gray-400">
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Beat</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-400" /> Miss</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-gray-300" /> Match</span>
            </div>
          </div>
        )}

      </aside>
      </div>
    </div>
  );
}
