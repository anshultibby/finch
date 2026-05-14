'use client';

import React, { useEffect, useState, useMemo, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { analyticsApi } from '@/lib/api';
import type { StockTransaction } from '@/lib/types';
import PriceRangeChart, { getStockRanges, type ChartMarker, type SeriesPoint } from '@/components/ui/PriceRangeChart';
import { createChart, ColorType, LineStyle, LineSeries } from 'lightweight-charts';
import type { IChartApi, Time } from 'lightweight-charts';

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function toUTC(dateStr: string): number {
  const d = new Date(dateStr.includes('T') || dateStr.includes(' ') ? dateStr.replace(' ', 'T') : dateStr + 'T12:00:00');
  return Math.floor(d.getTime() / 1000);
}

type ChartMode = 'price' | 'returns';

function ReturnsChart({ buyHold, yourReturns, height = 240 }: {
  buyHold: SeriesPoint[];
  yourReturns: SeriesPoint[];
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || buyHold.length < 2) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: 11,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: '#f3f4f6', style: LineStyle.Solid },
      },
      rightPriceScale: { visible: false },
      leftPriceScale: {
        visible: true,
        borderVisible: false,
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: { visible: true, borderVisible: false },
      handleScroll: false,
      handleScale: false,
    });

    chartRef.current = chart;

    const bhSeries = chart.addSeries(LineSeries, {
      color: '#9ca3af',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      priceScaleId: 'left',
    });
    bhSeries.setData(buyHold.map(p => ({ time: toUTC(p.date) as Time, value: p.value })));

    const lastYour = yourReturns[yourReturns.length - 1]?.value ?? 0;
    const yrSeries = chart.addSeries(LineSeries, {
      color: lastYour >= 0 ? '#10b981' : '#ef4444',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      priceScaleId: 'left',
    });
    yrSeries.setData(yourReturns.map(p => ({ time: toUTC(p.date) as Time, value: p.value })));

    bhSeries.createPriceLine({
      price: 0,
      color: '#d1d5db',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: false,
    });

    chart.timeScale().fitContent();

    const ro = new ResizeObserver(([entry]) => {
      chart.applyOptions({ width: entry.contentRect.width });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [buyHold, yourReturns, height]);

  return (
    <div>
      <div className="flex items-center gap-4 mb-2 px-1">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-0.5 bg-gray-400 rounded" />
          <span className="text-[11px] text-gray-400 font-medium">Buy & Hold</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-0.5 bg-emerald-500 rounded" />
          <span className="text-[11px] text-gray-400 font-medium">Your Returns</span>
        </div>
      </div>
      <div ref={containerRef} className="relative select-none [&_a[href*='tradingview']]:hidden" style={{ height }}>
        {buyHold.length < 2 && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-400">
            Not enough data for comparison
          </div>
        )}
      </div>
    </div>
  );
}

export default function TradesTab({ symbol, currentPrice }: { symbol: string; currentPrice?: number }) {
  const { user } = useAuth();
  const { openChatAbout } = useNavigation();
  const [trades, setTrades] = useState<StockTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [mode, setMode] = useState<ChartMode>('price');
  const [priceHistory, setPriceHistory] = useState<{ date: string; pct: number }[]>([]);
  const didSync = useRef(false);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      const data = await analyticsApi.getTransactions(user.id, symbol);
      if (cancelled) return;
      if (data.count === 0 && !didSync.current) {
        didSync.current = true;
        setSyncing(true);
        await analyticsApi.syncTransactions(user.id);
        if (cancelled) return;
        const retry = await analyticsApi.getTransactions(user.id, symbol);
        if (cancelled) return;
        setTrades(retry.transactions);
        setSyncing(false);
      } else {
        setTrades(data.transactions);
      }
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [user, symbol]);

  const sortedTrades = useMemo(() =>
    [...trades]
      .filter(t => t.type === 'BUY' || t.type === 'SELL')
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()),
    [trades]
  );

  const firstTradeDate = sortedTrades[0]?.date;
  const daysSinceFirst = firstTradeDate
    ? Math.ceil((Date.now() - new Date(firstTradeDate).getTime()) / 86400000)
    : 365;

  useEffect(() => {
    if (sortedTrades.length === 0 || !firstTradeDate) return;
    const days = daysSinceFirst + 10;
    fetch(`/api/market-prices?symbols=${symbol}&days=${days}`)
      .then(r => r.json())
      .then((d: Record<string, Array<{ date: string; pct: number }>>) => {
        setPriceHistory(d[symbol] ?? []);
      })
      .catch(() => {});
  }, [symbol, sortedTrades.length, firstTradeDate, daysSinceFirst]);

  const markers: ChartMarker[] = useMemo(() =>
    sortedTrades.map(t => ({
      time: t.date.split('T')[0],
      position: t.type === 'BUY' ? 'belowBar' as const : 'aboveBar' as const,
      color: t.type === 'BUY' ? '#10b981' : '#ef4444',
      shape: t.type === 'BUY' ? 'arrowUp' as const : 'arrowDown' as const,
      text: `${t.type} ${t.data?.quantity ?? ''}`,
    })),
    [sortedTrades]
  );

  const { buyHoldSeries, yourReturnsSeries } = useMemo(() => {
    if (sortedTrades.length === 0 || priceHistory.length < 2 || !currentPrice) {
      return { buyHoldSeries: [] as SeriesPoint[], yourReturnsSeries: [] as SeriesPoint[] };
    }

    const firstBuy = sortedTrades.find(t => t.type === 'BUY');
    if (!firstBuy) return { buyHoldSeries: [] as SeriesPoint[], yourReturnsSeries: [] as SeriesPoint[] };

    const firstPrice = firstBuy.data?.price ?? 0;
    if (firstPrice <= 0) return { buyHoldSeries: [] as SeriesPoint[], yourReturnsSeries: [] as SeriesPoint[] };

    const buyHold: SeriesPoint[] = priceHistory.map(p => {
      const priceAtDate = firstPrice * (1 + p.pct / 100);
      return { date: p.date, value: ((priceAtDate - firstPrice) / firstPrice) * 100 };
    });

    const tradesByDate = new Map<string, StockTransaction[]>();
    for (const t of sortedTrades) {
      const d = t.date.split('T')[0];
      if (!tradesByDate.has(d)) tradesByDate.set(d, []);
      tradesByDate.get(d)!.push(t);
    }

    let sharesHeld = 0;
    let totalCost = 0;
    let realizedPnl = 0;
    const yourReturns: SeriesPoint[] = [];

    for (const p of priceHistory) {
      const dateKey = p.date.split('T')[0];
      const dayTrades = tradesByDate.get(dateKey);
      if (dayTrades) {
        for (const t of dayTrades) {
          const qty = t.data?.quantity ?? t.data?.units ?? 0;
          const price = t.data?.price ?? 0;
          if (t.type === 'BUY') {
            totalCost += qty * price;
            sharesHeld += qty;
          } else if (t.type === 'SELL') {
            const avgCost = sharesHeld > 0 ? totalCost / sharesHeld : 0;
            realizedPnl += (price - avgCost) * qty;
            totalCost -= avgCost * qty;
            sharesHeld -= qty;
          }
        }
      }

      const priceNow = firstPrice * (1 + p.pct / 100);
      const unrealizedPnl = sharesHeld * priceNow - totalCost;
      const totalInvested = totalCost + realizedPnl;
      const returnPct = totalInvested > 0 ? ((realizedPnl + unrealizedPnl) / totalInvested) * 100 : 0;
      yourReturns.push({ date: p.date, value: returnPct });
    }

    return { buyHoldSeries: buyHold, yourReturnsSeries: yourReturns };
  }, [sortedTrades, priceHistory, currentPrice]);

  const chatAboutTrade = (trade: StockTransaction) => {
    const qty = trade.data?.quantity ?? trade.data?.units ?? '?';
    const price = trade.data?.price ? fmt(trade.data.price) : '?';
    const date = fmtDate(trade.date);
    const action = trade.type === 'BUY' ? 'bought' : 'sold';
    openChatAbout(
      symbol,
      `I ${action} ${qty} shares of ${symbol} at ${price} on ${date}. Analyze this trade — was the timing good? What was happening in the market around that time?`
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
        {syncing && <span className="ml-3 text-sm text-gray-400">Syncing trades...</span>}
      </div>
    );
  }

  if (sortedTrades.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="text-sm text-gray-400">No trades found for {symbol}</div>
        <div className="text-xs text-gray-300 mt-1">Connect a brokerage to see your trade history</div>
      </div>
    );
  }

  const totalBought = sortedTrades.filter(t => t.type === 'BUY').reduce((s, t) => s + (t.data?.amount ?? 0), 0);
  const totalSold = sortedTrades.filter(t => t.type === 'SELL').reduce((s, t) => s + (t.data?.amount ?? 0), 0);
  const sharesHeld = sortedTrades.reduce((s, t) => {
    const qty = t.data?.quantity ?? t.data?.units ?? 0;
    return t.type === 'BUY' ? s + qty : s - qty;
  }, 0);
  const unrealized = sharesHeld > 0 && currentPrice ? sharesHeld * currentPrice : 0;
  const netPnl = totalSold + unrealized - totalBought;

  return (
    <div className="pb-8">
      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-5">
        <div>
          <div className="text-xs text-gray-400">Invested</div>
          <div className="text-sm font-bold text-gray-900 tabular-nums">{fmt(totalBought)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-400">Returned</div>
          <div className="text-sm font-bold text-gray-900 tabular-nums">{fmt(totalSold)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-400">Net P&L</div>
          <div className={`text-sm font-bold tabular-nums ${netPnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {netPnl >= 0 ? '+' : ''}{fmt(netPnl)}
          </div>
        </div>
      </div>

      {/* Chart mode toggle */}
      <div className="flex items-center gap-1 mb-3">
        {(['price', 'returns'] as const).map(m => (
          <button key={m} onClick={() => setMode(m)}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
              mode === m ? 'bg-gray-900 text-white' : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
            }`}>
            {m === 'price' ? 'Price' : 'Returns'}
          </button>
        ))}
      </div>

      {/* Chart */}
      {mode === 'price' ? (
        <PriceRangeChart
          series={[{ symbol, color: '' }]}
          currentPrice={currentPrice}
          defaultDays={Math.min(daysSinceFirst + 30, 3650)}
          ranges={getStockRanges().filter(r => r.days >= Math.min(daysSinceFirst, 30))}
          height={240}
          hideHeader
          markers={markers}
        />
      ) : (
        <ReturnsChart buyHold={buyHoldSeries} yourReturns={yourReturnsSeries} />
      )}

      {/* Trade list */}
      <div className="mt-6">
        <div className="text-sm font-bold text-gray-900 mb-3">Trade History</div>
        <div className="space-y-0">
          {[...sortedTrades].reverse().map(trade => {
            const isBuy = trade.type === 'BUY';
            const qty = trade.data?.quantity ?? trade.data?.units ?? 0;
            const price = trade.data?.price ?? 0;
            const total = trade.data?.amount ?? (qty * price);
            return (
              <div key={trade.id} className="flex items-center gap-3 py-3 border-b border-gray-100 last:border-b-0">
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                  isBuy ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'
                }`}>
                  <span className={`text-[10px] font-black ${isBuy ? 'text-emerald-600' : 'text-red-600'}`}>
                    {isBuy ? 'BUY' : 'SELL'}
                  </span>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-900">
                    {qty} {qty === 1 ? 'share' : 'shares'} @ {fmt(price)}
                  </div>
                  <div className="text-xs text-gray-400">{fmtDate(trade.date)}</div>
                </div>

                <div className="text-right mr-2">
                  <div className={`text-sm font-bold tabular-nums ${isBuy ? 'text-gray-900' : 'text-emerald-600'}`}>
                    {isBuy ? '-' : '+'}{fmt(Math.abs(total))}
                  </div>
                </div>

                <button
                  onClick={() => chatAboutTrade(trade)}
                  className="shrink-0 px-2.5 py-1.5 text-[11px] font-semibold text-gray-500 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors"
                >
                  Ask AI
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
