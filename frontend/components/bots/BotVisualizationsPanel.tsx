'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { snaptradeApi } from '@/lib/api';
import type { PortfolioResponse, PortfolioPerformance } from '@/lib/types';

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

interface BotVisualizationsPanelProps {
  onBack?: () => void;
  accountId?: string;       // filter to a specific account
  accountName?: string;     // display name for the account
}

type TimeRange = '1W' | '1M' | '3M' | 'YTD' | '1Y' | 'ALL';

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function formatPct(n: number) {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

function getStartDate(range: TimeRange): string {
  const d = new Date();
  switch (range) {
    case '1W': d.setDate(d.getDate() - 7); break;
    case '1M': d.setMonth(d.getMonth() - 1); break;
    case '3M': d.setMonth(d.getMonth() - 3); break;
    case 'YTD': return `${d.getFullYear()}-01-01`;
    case '1Y': d.setFullYear(d.getFullYear() - 1); break;
    case 'ALL': d.setFullYear(d.getFullYear() - 5); break;
  }
  return d.toISOString().split('T')[0];
}

// ─────────────────────────────────────────────────────────────────────────────
// Portfolio Line Chart (canvas-based, Robinhood-style)
// ─────────────────────────────────────────────────────────────────────────────

function PortfolioChart({ data, loading, onHover }: {
  data: Array<{ date: string; value: number }>;
  loading: boolean;
  onHover?: (info: { date: string; value: number } | null) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const pointsRef = useRef<Array<{ x: number; y: number }>>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || data.length < 2) return;

    const rect = container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = rect.width;
    const h = rect.height;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const values = data.map(d => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const pad = { top: 12, bottom: 12, left: 0, right: 0 };
    const chartW = w - pad.left - pad.right;
    const chartH = h - pad.top - pad.bottom;

    const isUp = values[values.length - 1] >= values[0];
    const color = isUp ? '#10b981' : '#ef4444';

    // Compute points
    const pts: Array<{ x: number; y: number }> = [];
    for (let i = 0; i < data.length; i++) {
      pts.push({
        x: pad.left + (i / (data.length - 1)) * chartW,
        y: pad.top + (1 - (values[i] - min) / range) * chartH,
      });
    }
    pointsRef.current = pts;

    // Draw reference line (from first value, like Robinhood's "previous close")
    const refY = pts[0].y;
    ctx.setLineDash([3, 4]);
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, refY);
    ctx.lineTo(w, refY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw gradient fill
    const grad = ctx.createLinearGradient(0, pad.top, 0, h - pad.bottom);
    grad.addColorStop(0, isUp ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');

    ctx.beginPath();
    pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.lineTo(pts[pts.length - 1].x, h - pad.bottom);
    ctx.lineTo(pts[0].x, h - pad.bottom);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Draw line
    ctx.beginPath();
    pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Draw hover elements
    if (hoverIdx !== null && hoverIdx >= 0 && hoverIdx < pts.length) {
      const hp = pts[hoverIdx];

      // Vertical line
      ctx.beginPath();
      ctx.moveTo(hp.x, pad.top);
      ctx.lineTo(hp.x, h - pad.bottom);
      ctx.strokeStyle = '#9ca3af';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Dot
      ctx.beginPath();
      ctx.arc(hp.x, hp.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(hp.x, hp.y, 2, 0, Math.PI * 2);
      ctx.fillStyle = '#fff';
      ctx.fill();
    }
  }, [data, hoverIdx]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (data.length < 2 || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const idx = Math.round((x / rect.width) * (data.length - 1));
    const clamped = Math.max(0, Math.min(data.length - 1, idx));
    setHoverIdx(clamped);
    onHover?.({ date: data[clamped].date, value: data[clamped].value });
  }, [data, onHover]);

  const handleMouseLeave = useCallback(() => {
    setHoverIdx(null);
    onHover?.(null);
  }, [onHover]);

  if (loading || data.length < 2) return null;

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full cursor-crosshair"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <canvas ref={canvasRef} className="absolute inset-0" />
      {/* Date label above dot */}
      {hoverIdx !== null && pointsRef.current[hoverIdx] && (
        <div
          className="absolute text-[11px] text-gray-500 font-medium pointer-events-none whitespace-nowrap tabular-nums"
          style={{
            left: Math.min(Math.max(pointsRef.current[hoverIdx].x - 30, 4), (containerRef.current?.offsetWidth || 300) - 80),
            top: Math.max(pointsRef.current[hoverIdx].y - 22, 0),
          }}
        >
          {new Date(data[hoverIdx].date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TradingView Advanced Chart (for drill-down)
// ─────────────────────────────────────────────────────────────────────────────

function TradingViewAdvancedChart({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef(`tradingview_${Math.random().toString(36).slice(2)}`);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.innerHTML = '';

    const containerId = widgetIdRef.current;
    const wrapper = document.createElement('div');
    wrapper.id = containerId;
    wrapper.style.height = '100%';
    wrapper.style.width = '100%';
    el.appendChild(wrapper);

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/tv.js';
    script.async = true;
    script.onload = () => {
      if (typeof (window as any).TradingView !== 'undefined') {
        new (window as any).TradingView.widget({
          autosize: true,
          symbol,
          interval: 'D',
          timezone: 'Etc/UTC',
          theme: 'light',
          style: '1',
          locale: 'en',
          toolbar_bg: '#f8f9fa',
          enable_publishing: false,
          allow_symbol_change: true,
          hide_top_toolbar: false,
          hide_legend: false,
          save_image: false,
          container_id: containerId,
          studies: ['Volume@tv-basicstudies'],
        });
      }
    };
    el.appendChild(script);

    return () => { el.innerHTML = ''; };
  }, [symbol]);

  return <div ref={containerRef} className="w-full h-full" />;
}

// ─────────────────────────────────────────────────────────────────────────────
// Holdings List (Robinhood-style)
// ─────────────────────────────────────────────────────────────────────────────

function HoldingRow({ holding, onClick }: { holding: HoldingInfo; onClick: () => void }) {
  const pctChange = holding.gain_loss_percent ?? 0;
  const isUp = pctChange >= 0;

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-4 px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
    >
      {/* Left: symbol + shares */}
      <div className="text-left min-w-[80px]">
        <div className="text-sm font-semibold text-gray-900">{holding.symbol}</div>
        <div className="text-xs text-gray-400">
          {holding.quantity % 1 === 0 ? holding.quantity : holding.quantity.toFixed(2)} share{holding.quantity !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Center: mini sparkline placeholder (dotted line + dot like Robinhood) */}
      <div className="flex-1 flex items-center justify-center">
        <div className="w-full max-w-[80px] flex items-center gap-0.5">
          <div className={`flex-1 border-t-2 border-dotted ${isUp ? 'border-emerald-300' : 'border-red-300'}`} />
          <div className={`w-2 h-2 rounded-full ${isUp ? 'bg-emerald-500' : 'bg-red-500'}`} />
        </div>
      </div>

      {/* Right: price + % change */}
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
// Main Panel
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

function AccountSelector({ accounts, totalValue, totalGainLoss, totalGainLossPct, onSelect, onBack }: {
  accounts: AccountCard[];
  totalValue: number;
  totalGainLoss: number;
  totalGainLossPct: number;
  onSelect: (id: string | null, name: string) => void;
  onBack?: () => void;
}) {
  const accountTypeLabel = (type: string) => type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-4 pt-3 pb-2 shrink-0">
        <div className="flex items-center gap-2">
          {onBack && (
            <button onClick={onBack} className="p-1 -ml-2 text-gray-400 hover:text-gray-600 transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
          )}
          <div className="text-sm font-semibold text-gray-900">Portfolio</div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {/* All accounts card */}
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

        {/* Individual account cards */}
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

export default function BotVisualizationsPanel({ onBack, accountId: propAccountId, accountName: propAccountName }: BotVisualizationsPanelProps) {
  const { user } = useAuth();
  const [holdings, setHoldings] = useState<HoldingInfo[]>([]);
  const [portfolioSummary, setPortfolioSummary] = useState<{ totalValue: number; totalGainLoss: number; totalGainLossPct: number } | null>(null);
  const [equitySeries, setEquitySeries] = useState<Array<{ date: string; value: number }>>([]);
  const [timeRange, setTimeRange] = useState<TimeRange>('ALL');
  const [loading, setLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<AccountCard[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | undefined>(propAccountId);
  const [selectedAccountName, setSelectedAccountName] = useState<string | undefined>(propAccountName);
  const [showAccountPicker, setShowAccountPicker] = useState(!propAccountId && !propAccountName);
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

        // Load accounts for the picker
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
  const [hoverValue, setHoverValue] = useState<{ date: string; value: number } | null>(null);

  // Fetch portfolio history, trigger backfill if empty
  useEffect(() => {
    if (!loading && isConnected && user && !showAccountPicker) {
      snaptradeApi.getPortfolioHistory(user.id, undefined, undefined, selectedAccountId).then(result => {
        if (result.success && result.equity_series?.length > 1) {
          setEquitySeries(result.equity_series);
        } else {
          // No snapshots yet - trigger backfill in background
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

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
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
          setEquitySeries([]); // Reset chart for new account
        }}
        onBack={onBack}
      />
    );
  }

  // Drill-down into a single holding
  if (selectedSymbol) {
    const h = holdings.find(x => x.symbol === selectedSymbol);
    return (
      <div className="flex flex-col h-full bg-white">
        {/* Header */}
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
        <div className="flex-1 min-h-0">
          <TradingViewAdvancedChart key={selectedSymbol} symbol={selectedSymbol} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Portfolio header + chart */}
      <div className="shrink-0">
        {/* Back + value */}
        <div className="px-4 pt-3 pb-1">
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (accounts.length > 0 && !propAccountId) {
                  setShowAccountPicker(true);
                  setSelectedSymbol(null);
                } else if (onBack) {
                  onBack();
                }
              }}
              className="p-1 -ml-2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            {portfolioSummary && isConnected ? (
              <div>
                {selectedAccountName && <div className="text-xs text-gray-400 font-medium">{selectedAccountName}</div>}
                <div className="text-2xl font-bold text-gray-900 tabular-nums">
                  {formatCurrency(hoverValue?.value ?? portfolioSummary.totalValue)}
                </div>
              </div>
            ) : (
              <div>
                <div className="text-lg font-semibold text-gray-900">Portfolio</div>
                <div className="text-xs text-gray-400">Connect a brokerage to see your portfolio</div>
              </div>
            )}
          </div>
        </div>

        {/* Portfolio equity chart */}
        {(() => {
          const cutoff = getStartDate(timeRange);
          const filtered = equitySeries.filter(p => p.date >= cutoff);
          const chartData = filtered.length >= 2 ? filtered : equitySeries;
          const change = chartData.length >= 2
            ? { value: chartData[chartData.length - 1].value - chartData[0].value, pct: ((chartData[chartData.length - 1].value - chartData[0].value) / chartData[0].value) * 100 }
            : null;

          return isConnected && chartData.length >= 2 ? (
            <>
              {/* Period change */}
              {change && (
                <div className="px-4 pb-1">
                  <span className={`text-sm font-medium tabular-nums ${change.value >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {change.value >= 0 ? '+' : ''}{formatCurrency(change.value)} ({formatPct(change.pct)})
                  </span>
                  <span className="text-xs text-gray-400 ml-1.5">
                    {timeRange === 'YTD' ? 'Year to date' : timeRange === 'ALL' ? 'All time' : `Past ${timeRange === '1W' ? 'week' : timeRange === '1M' ? 'month' : timeRange === '3M' ? '3 months' : 'year'}`}
                  </span>
                </div>
              )}
              <div className="h-[160px] px-2">
                <PortfolioChart data={chartData} loading={false} onHover={setHoverValue} />
              </div>
              {/* Time range buttons */}
              <div className="flex items-center gap-1 px-4 py-2">
                {(['1W', '1M', '3M', 'YTD', '1Y', 'ALL'] as TimeRange[]).map(r => (
                  <button
                    key={r}
                    onClick={() => setTimeRange(r)}
                    className={`px-3 py-1 text-xs font-semibold rounded-full transition-colors ${
                      timeRange === r
                        ? 'bg-gray-900 text-white'
                        : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </>
          ) : isConnected && buildingHistory ? (
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
        ) : !isConnected ? (
          <div className="px-4 py-8 text-center text-sm text-gray-400">
            Connect your brokerage in Connections to see your holdings
          </div>
        ) : (
          <div className="px-4 py-8 text-center text-sm text-gray-400">No holdings found</div>
        )}
      </div>
    </div>
  );
}
