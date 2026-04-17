'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { snaptradeApi } from '@/lib/api';
import type { PortfolioResponse, PortfolioPerformance } from '@/lib/types';
import PriceRangeChart, { getStockRanges, ytdDays, type RangeOption } from '@/components/ui/PriceRangeChart';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface HoldingInfo {
  symbol: string;
  quantity: number;
  price: number;
  value: number;
  average_purchase_price?: number;
  total_cost?: number;
  gain_loss?: number;
  gain_loss_percent?: number;
}

type TimeRange = '1D' | '1W' | '1M' | '3M' | 'YTD' | '1Y' | 'ALL';

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function formatPct(n: number) {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

function localDateStr(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getStartDate(range: TimeRange): string {
  const now = new Date();
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  switch (range) {
    case '1D': d.setDate(d.getDate() - 1); break;
    case '1W': d.setDate(d.getDate() - 7); break;
    case '1M': d.setMonth(d.getMonth() - 1); break;
    case '3M': d.setMonth(d.getMonth() - 3); break;
    case 'YTD': return `${d.getFullYear()}-01-01`;
    case '1Y': d.setFullYear(d.getFullYear() - 1); break;
    case 'ALL': return '';
  }
  return localDateStr(d);
}

// ─────────────────────────────────────────────────────────────────────────────
// Holdings List
// ─────────────────────────────────────────────────────────────────────────────

function HoldingRow({ holding, onClick }: { holding: HoldingInfo; onClick: () => void }) {
  const pctChange = holding.gain_loss_percent ?? 0;
  const isUp = pctChange >= 0;

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-4 px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
    >
      <div className="text-left min-w-[80px]">
        <div className="text-sm font-semibold text-gray-900">{holding.symbol}</div>
        <div className="text-xs text-gray-400">
          {holding.quantity % 1 === 0 ? holding.quantity : holding.quantity.toFixed(2)} share{holding.quantity !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center">
        <div className="w-full max-w-[80px] flex items-center gap-0.5">
          <div className={`flex-1 border-t-2 border-dotted ${isUp ? 'border-emerald-300' : 'border-red-300'}`} />
          <div className={`w-2 h-2 rounded-full ${isUp ? 'bg-emerald-500' : 'bg-red-500'}`} />
        </div>
      </div>

      <div className="text-right min-w-[80px]">
        <div className="text-sm font-medium text-gray-900 tabular-nums">{formatCurrency(holding.price)}</div>
        <div className={`text-xs font-medium tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
          {formatPct(pctChange)}
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function parseHoldingsCSV(csv: string): HoldingInfo[] {
  const lines = csv.split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',');
  const holdings: HoldingInfo[] = [];
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',');
    if (values.length < headers.length) continue;
    const row: Record<string, string> = {};
    headers.forEach((h, idx) => { row[h] = values[idx]; });
    if (!row.symbol) continue;
    holdings.push({
      symbol: row.symbol,
      quantity: parseFloat(row.quantity) || 0,
      price: parseFloat(row.price) || 0,
      value: parseFloat(row.value) || 0,
      average_purchase_price: row.avg_cost && row.avg_cost !== 'None' ? parseFloat(row.avg_cost) : undefined,
      total_cost: row.total_cost && row.total_cost !== 'None' ? parseFloat(row.total_cost) : undefined,
      gain_loss: row.gain_loss && row.gain_loss !== 'None' ? parseFloat(row.gain_loss) : undefined,
      gain_loss_percent: row.gain_loss_pct && row.gain_loss_pct !== 'None' ? parseFloat(row.gain_loss_pct) : undefined,
    });
  }
  return holdings;
}

interface AccountCard {
  id: string;
  name: string;
  institution: string;
  type: string;
  balance: number;
}

function AccountSelector({ accounts, totalValue, totalGainLoss, totalGainLossPct, onSelect }: {
  accounts: AccountCard[];
  totalValue: number;
  totalGainLoss: number;
  totalGainLossPct: number;
  onSelect: (id: string | null, name: string) => void;
}) {
  const accountTypeLabel = (type: string) => type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-4 pt-3 pb-2 shrink-0">
        <div className="flex items-center gap-2">
          <div className="text-sm font-semibold text-gray-900">Connections</div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-4">
        <button
          onClick={() => onSelect(null, 'All Accounts')}
          className="w-full text-left mb-3 p-4 rounded-xl border border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm transition-all"
        >
          <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-0.5">All Accounts</div>
          <div className="text-xl font-bold text-gray-900 tabular-nums">{formatCurrency(totalValue)}</div>
          {totalGainLoss !== 0 && (
            <div className={`text-xs font-medium tabular-nums mt-0.5 ${totalGainLoss >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {totalGainLoss >= 0 ? '+' : ''}{formatCurrency(totalGainLoss)} ({formatPct(totalGainLossPct)})
            </div>
          )}
          <div className="text-[11px] text-gray-400 mt-1">{accounts.length} account{accounts.length !== 1 ? 's' : ''}</div>
        </button>

        <div className="grid grid-cols-2 gap-2">
          {accounts.map(acct => (
            <button
              key={acct.id}
              onClick={() => onSelect(acct.id, acct.name)}
              className="text-left p-3 rounded-xl border border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm transition-all"
            >
              <div className="text-xs font-semibold text-gray-900 truncate">{acct.name}</div>
              <div className="text-[10px] text-gray-400 mb-1">{acct.institution} · {accountTypeLabel(acct.type)}</div>
              <div className="text-sm font-bold text-gray-900 tabular-nums">{formatCurrency(acct.balance)}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Panel
// ─────────────────────────────────────────────────────────────────────────────

export default function ConnectionsPanel() {
  const { user } = useAuth();
  const [holdings, setHoldings] = useState<HoldingInfo[]>([]);
  const [portfolioSummary, setPortfolioSummary] = useState<{ totalValue: number; totalGainLoss: number; totalGainLossPct: number } | null>(null);
  const [equitySeries, setEquitySeries] = useState<Array<{ date: string; value: number }>>([]);
  const [timeRange, setTimeRange] = useState<TimeRange>('1D');
  const [loading, setLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<AccountCard[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | undefined>();
  const [selectedAccountName, setSelectedAccountName] = useState<string | undefined>();
  const [showAccountPicker, setShowAccountPicker] = useState(true);
  const initializedRef = useRef(false);

  // Fetch portfolio + accounts data
  useEffect(() => {
    if (!user || initializedRef.current) return;
    initializedRef.current = true;

    (async () => {
      try {
        const [portfolio, performance, acctRes] = await Promise.all([
          snaptradeApi.getPortfolio(user.id),
          snaptradeApi.getPortfolioPerformance(user.id).catch(() => null),
          snaptradeApi.getAccounts(user.id).catch(() => null),
        ]);

        if (acctRes?.success && acctRes.accounts) {
          setAccounts(acctRes.accounts.map((a: any) => ({
            id: a.id || a.account_id,
            name: a.name,
            institution: a.institution || a.broker_name || '',
            type: a.type || '',
            balance: a.balance || 0,
          })));
        }

        if (portfolio.success && portfolio.holdings_csv) {
          setIsConnected(true);
          const parsed = parseHoldingsCSV(portfolio.holdings_csv);
          setHoldings(parsed);

          let totalGainLoss = performance?.total_gain_loss || 0;
          let totalCost = performance?.total_cost || 0;
          if (!totalGainLoss && parsed.length > 0) {
            parsed.forEach(h => {
              if (h.gain_loss) totalGainLoss += h.gain_loss;
              if (h.total_cost) totalCost += h.total_cost;
            });
          }
          const totalGainLossPct = totalCost > 0 ? (totalGainLoss / totalCost) * 100 : (performance?.total_gain_loss_percent || 0);
          setPortfolioSummary({
            totalValue: portfolio.total_value || 0,
            totalGainLoss,
            totalGainLossPct,
          });
        } else {
          setIsConnected(false);
        }
      } catch (e) {
        console.error('Failed to fetch portfolio:', e);
        setIsConnected(false);
      } finally {
        setLoading(false);
      }
    })();
  }, [user]);

  const [buildingHistory, setBuildingHistory] = useState(false);
  const [intradayCache, setIntradayCache] = useState<Record<string, Array<{ date: string; value: number }>>>({});
  const [intradayLoading, setIntradayLoading] = useState(false);
  const [hoverValue, setHoverValue] = useState<{ date: string; value: number } | null>(null);
  const intradayCacheRef = useRef(intradayCache);
  intradayCacheRef.current = intradayCache;

  const intradaySeries = (timeRange === '1D' || timeRange === '1W') ? (intradayCache[timeRange] || []) : [];

  useEffect(() => {
    if (!loading && isConnected && user && !showAccountPicker) {
      snaptradeApi.getPortfolioHistory(user.id, undefined, undefined, selectedAccountId).then(result => {
        if (result.success && result.equity_series?.length > 1) {
          setEquitySeries(result.equity_series);
        } else {
          setBuildingHistory(true);
          snaptradeApi.buildPortfolioHistory(user.id, selectedAccountId).then(buildResult => {
            if (buildResult.success && buildResult.equity_series && buildResult.equity_series.length > 1) {
              setEquitySeries(buildResult.equity_series);
            }
          }).catch(() => {}).finally(() => setBuildingHistory(false));
        }
      }).catch(() => {});
    }
  }, [loading, isConnected, user, showAccountPicker, selectedAccountId]);

  useEffect(() => {
    if (!user || !isConnected || showAccountPicker) return;
    if (timeRange !== '1D' && timeRange !== '1W') return;
    if (intradayCacheRef.current[timeRange]?.length >= 1) return;
    setIntradayLoading(true);
    const days = timeRange === '1D' ? 1 : 7;
    snaptradeApi.getPortfolioIntraday(user.id, selectedAccountId, days).then(result => {
      if (result.success && result.equity_series?.length > 1) {
        setIntradayCache(prev => ({ ...prev, [timeRange]: result.equity_series }));
      }
    }).catch(() => {}).finally(() => setIntradayLoading(false));
  }, [user, isConnected, showAccountPicker, selectedAccountId, timeRange]);

  useEffect(() => {
    if (!user || !isConnected || showAccountPicker || buildingHistory) return;

    const isMarketOpen = () => {
      const now = new Date();
      const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
      const day = et.getDay();
      const h = et.getHours();
      const m = et.getMinutes();
      const mins = h * 60 + m;
      return day >= 1 && day <= 5 && mins >= 570 && mins <= 960;
    };

    if (!isMarketOpen()) return;

    const interval = setInterval(() => {
      if (!isMarketOpen()) return;

      if (timeRange === '1D' || timeRange === '1W') {
        const days = timeRange === '1D' ? 1 : 7;
        snaptradeApi.getPortfolioIntraday(user.id, selectedAccountId, days).then(result => {
          if (result.success && result.equity_series?.length > 1) {
            setIntradayCache(prev => ({ ...prev, [timeRange]: result.equity_series }));
          }
        }).catch(() => {});
      }

      snaptradeApi.getPortfolioHistory(user.id, undefined, undefined, selectedAccountId).then(result => {
        if (result.success && result.equity_series?.length > 1) {
          setEquitySeries(result.equity_series);
        }
      }).catch(() => {});
    }, 60_000);

    return () => clearInterval(interval);
  }, [user, isConnected, showAccountPicker, buildingHistory, timeRange, selectedAccountId]);

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  // No connected accounts
  if (!isConnected) {
    return (
      <div className="flex flex-col h-full bg-white">
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <div className="w-16 h-16 rounded-full bg-gray-50 border border-gray-200 flex items-center justify-center mb-5">
            <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
            </svg>
          </div>
          <div className="font-bold text-gray-900 text-lg mb-2">No connected accounts</div>
          <div className="text-sm text-gray-500 max-w-xs leading-relaxed">
            Connect an external brokerage account to view your holdings and enable your agent to analyze your portfolio for tax-loss harvesting opportunities.
          </div>
        </div>
      </div>
    );
  }

  // Account picker view
  if (showAccountPicker && accounts.length > 0) {
    return (
      <AccountSelector
        accounts={accounts}
        totalValue={portfolioSummary?.totalValue || 0}
        totalGainLoss={portfolioSummary?.totalGainLoss || 0}
        totalGainLossPct={portfolioSummary?.totalGainLossPct || 0}
        onSelect={(id, name) => {
          setSelectedAccountId(id || undefined);
          setSelectedAccountName(name);
          setShowAccountPicker(false);
          setEquitySeries([]);
          setIntradayCache({});
        }}
      />
    );
  }

  // Drill-down into a single holding
  if (selectedSymbol) {
    const h = holdings.find(x => x.symbol === selectedSymbol);
    return (
      <div className="flex flex-col h-full bg-white">
        <div className="flex items-center gap-3 px-3 py-2 border-b border-gray-100 shrink-0">
          <button onClick={() => setSelectedSymbol(null)} className="p-1 -ml-1 text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
          </button>
          <span className="text-sm font-semibold text-gray-900">{selectedSymbol}</span>
          {h && (
            <>
              <span className="text-xs text-gray-400 tabular-nums">{formatCurrency(h.value)}</span>
              <span className="text-xs text-gray-400 tabular-nums">{h.quantity % 1 === 0 ? h.quantity : h.quantity.toFixed(2)} shares</span>
              {h.gain_loss != null && h.gain_loss !== 0 && (
                <span className={`text-xs font-medium tabular-nums ${h.gain_loss >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {h.gain_loss >= 0 ? '+' : ''}{formatCurrency(h.gain_loss)} ({formatPct(h.gain_loss_percent || 0)})
                </span>
              )}
            </>
          )}
        </div>
        <div className="flex-1 min-h-0 px-3 py-3 overflow-y-auto">
          <PriceRangeChart
            key={selectedSymbol}
            series={[{ symbol: selectedSymbol, color: (h?.gain_loss ?? 0) >= 0 ? '#10b981' : '#ef4444' }]}
            defaultDays={365}
            ranges={getStockRanges()}
            height={260}
          />
        </div>
      </div>
    );
  }

  if (buildingHistory) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center gap-3">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
        <div className="text-sm text-gray-500">Rebuilding portfolio history...</div>
        <div className="text-xs text-gray-400">Fetching prices for all holdings</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Portfolio header + chart */}
      <div className="shrink-0">
        <div className="px-4 pt-3 pb-1">
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (accounts.length > 0) {
                  setShowAccountPicker(true);
                  setSelectedSymbol(null);
                }
              }}
              className="p-1 -ml-2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            <div>
              {selectedAccountName && <div className="text-xs text-gray-400 font-medium">{selectedAccountName}</div>}
              <div className="text-2xl font-bold text-gray-900 tabular-nums">
                {formatCurrency(
                  hoverValue?.value
                  ?? (selectedAccountId ? accounts.find(a => a.id === selectedAccountId)?.balance : null)
                  ?? portfolioSummary?.totalValue
                  ?? 0
                )}
              </div>
            </div>
            <button
              onClick={() => {
                if (!user || buildingHistory) return;
                setBuildingHistory(true);
                setEquitySeries([]);
                snaptradeApi.buildPortfolioHistory(user.id, selectedAccountId, true).then(result => {
                  if (result.success && result.equity_series && result.equity_series.length > 1) {
                    setEquitySeries(result.equity_series);
                  }
                }).catch(() => {}).finally(() => setBuildingHistory(false));
              }}
              disabled={buildingHistory}
              className="p-1 text-gray-300 hover:text-gray-500 transition-colors disabled:opacity-30"
              title="Rebuild chart"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
              </svg>
            </button>
          </div>
        </div>

        {/* Portfolio equity chart */}
        {(() => {
          const useIntraday = (timeRange === '1D' || timeRange === '1W') && intradaySeries.length >= 2;
          let chartData: Array<{ date: string; value: number }>;

          if (useIntraday) {
            chartData = intradaySeries;
          } else if (timeRange === 'ALL') {
            chartData = equitySeries;
          } else if (timeRange === '1D') {
            chartData = equitySeries.length >= 2 ? equitySeries.slice(-2) : equitySeries;
          } else {
            const cutoff = getStartDate(timeRange);
            const filtered = equitySeries.filter(p => p.date >= cutoff);
            chartData = filtered.length >= 2 ? filtered : equitySeries;
          }

          const change = chartData.length >= 2
            ? { value: chartData[chartData.length - 1].value - chartData[0].value, pct: ((chartData[chartData.length - 1].value - chartData[0].value) / chartData[0].value) * 100 }
            : null;

          const isChartLoading = (timeRange === '1D' || timeRange === '1W') && intradayLoading && !useIntraday;

          const rangeOptions: RangeOption[] = [
            { label: '1D', days: 1 },
            { label: '1W', days: 7 },
            { label: '1M', days: 30 },
            { label: '3M', days: 90 },
            { label: 'YTD', days: ytdDays() },
            { label: '1Y', days: 365 },
            { label: 'ALL', days: 3650 },
          ];
          const selectedDays = rangeOptions.find(r => r.label === timeRange)?.days ?? 30;
          const labelToTimeRange = (label: string): TimeRange | null =>
            rangeOptions.some(r => r.label === label) ? (label as TimeRange) : null;

          return chartData.length >= 2 || isChartLoading ? (
            <>
              {change && (
                <div className="px-4 pb-1">
                  <span className={`text-sm font-medium tabular-nums ${change.value >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {change.value >= 0 ? '+' : ''}{formatCurrency(change.value)} ({formatPct(change.pct)})
                  </span>
                  <span className="text-xs text-gray-400 ml-1.5">
                    {timeRange === '1D' ? 'Today' : timeRange === 'YTD' ? 'Year to date' : timeRange === 'ALL' ? 'All time' : `Past ${timeRange === '1W' ? 'week' : timeRange === '1M' ? 'month' : timeRange === '3M' ? '3 months' : 'year'}`}
                  </span>
                </div>
              )}
              <div className="px-2">
                {isChartLoading ? (
                  <div className="flex items-center justify-center h-[160px] gap-2">
                    <div className="w-4 h-4 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
                    <span className="text-xs text-gray-400">Loading hourly data...</span>
                  </div>
                ) : (
                  <PriceRangeChart
                    data={chartData}
                    format="currency"
                    height={160}
                    ranges={rangeOptions}
                    selectedDays={selectedDays}
                    onRangeChange={(_d, label) => {
                      const next = labelToTimeRange(label);
                      if (next) setTimeRange(next);
                    }}
                    onHoverChange={setHoverValue}
                  />
                )}
              </div>
            </>
          ) : buildingHistory ? (
            <div className="h-[80px] flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
              <span className="text-xs text-gray-400">Building portfolio history...</span>
            </div>
          ) : null;
        })()}
      </div>

      {/* Holdings list */}
      <div className="flex-1 overflow-y-auto border-t border-gray-200">
        <div className="px-4 py-2.5">
          <span className="text-sm font-semibold text-gray-900">Stocks</span>
        </div>
        {holdings.length > 0 ? (
          holdings.map(h => (
            <HoldingRow
              key={h.symbol}
              holding={h}
              onClick={() => setSelectedSymbol(h.symbol)}
            />
          ))
        ) : (
          <div className="px-4 py-8 text-center text-sm text-gray-400">No holdings found</div>
        )}
      </div>
    </div>
  );
}
