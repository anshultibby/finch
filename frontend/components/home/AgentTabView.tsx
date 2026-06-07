'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { robinhoodApi, snaptradeApi, type RobinhoodPortfolioResponse } from '@/lib/api';
import { useCachedResource } from '@/hooks/useCachedResource';
import PriceRangeChart, { getStockRanges, type SeriesPoint } from '@/components/ui/PriceRangeChart';
import MiniSparkline from '@/components/shared/MiniSparkline';
import TickerLogo from '@/components/ui/TickerLogo';
import CountUp from '@/components/ui/CountUp';
import {
  fetchPriceSeries,
  buildEquityCurve,
  reconstructRealizedStats,
  ordersToMarkers,
  periodReturnPct,
  benchmarkReturnPct,
  type RawPoint,
} from '@/lib/agentReturns';

const ROBINHOOD_PORTFOLIO_URL = 'https://robinhood.com/account';

function usd(v?: string | number | null): string {
  if (v == null) return '—';
  const n = Number(v);
  return Number.isNaN(n) ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(n);
}
function signed(n: number): string {
  const s = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Math.abs(n));
  return `${n >= 0 ? '+' : '−'}${s}`;
}
function signedPct(n: number): string {
  return `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(2)}%`;
}
function timeAgo(iso?: string): string {
  if (!iso) return '';
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const h = Math.floor(mins / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}
const pos = (n: number) => (n >= 0 ? 'text-emerald-600' : 'text-red-500');

const RANGES = getStockRanges();
const DEFAULT_DAYS = 30; // 1M

export default function AgentTabView({ userId, onStockClick }: {
  userId: string;
  onStockClick: (symbol: string) => void;
}) {
  // Cached so flipping back to this tab shows the last portfolio instantly and
  // only revalidates in the background, instead of re-fetching from a spinner.
  const { data, error, isLoading, refresh } = useCachedResource<RobinhoodPortfolioResponse>(
    userId ? `rh-portfolio:${userId}` : null,
    () => robinhoodApi.getPortfolio(userId),
    { ttl: 30_000 },
  );

  const [days, setDays] = useState(DEFAULT_DAYS);
  const [rangeLabel, setRangeLabel] = useState(RANGES.find(r => r.days === DEFAULT_DAYS)?.label ?? '1M');
  const [prices, setPrices] = useState<Record<string, RawPoint[]>>({});
  const [pricesLoading, setPricesLoading] = useState(false);
  const [hover, setHover] = useState<{ value: number } | null>(null);
  const [rhLogo, setRhLogo] = useState<string | null>(null);

  const holdings = data?.holdings ?? [];
  const orders = data?.orders ?? [];

  // Stable key of every symbol we need price history for (holdings + traded +
  // SPY benchmark), so the fetch effect only re-runs when the set changes.
  const symbolsKey = useMemo(() => {
    const set = new Set<string>(['SPY']);
    for (const h of holdings) set.add(h.symbol.toUpperCase());
    for (const o of orders) set.add(o.symbol.toUpperCase());
    return Array.from(set).sort().join(',');
  }, [holdings, orders]);

  useEffect(() => {
    if (!symbolsKey) return;
    let cancelled = false;
    setPricesLoading(true);
    fetchPriceSeries(symbolsKey.split(','), days)
      .then(res => { if (!cancelled) setPrices(res); })
      .finally(() => { if (!cancelled) setPricesLoading(false); });
    return () => { cancelled = true; };
  }, [symbolsKey, days]);

  // One-time Robinhood logo from the existing broker-logo feed (for the link).
  useEffect(() => {
    snaptradeApi.getBrokerages()
      .then(res => {
        const rh = (res.brokerages || []).find(b => b.name?.toLowerCase().includes('robinhood'));
        if (rh?.logo) setRhLogo(rh.logo);
      })
      .catch(() => {});
  }, []);

  // Prefer true settled cash; fall back to buying power if the broker omits it.
  const baseCash = Number(data?.cash ?? data?.buying_power ?? 0) || 0;

  const curve: SeriesPoint[] = useMemo(() => {
    if (!holdings.length && !orders.length) return [];
    return buildEquityCurve({ holdings, orders, cash: baseCash, pricesBySymbol: prices });
  }, [holdings, orders, baseCash, prices]);

  const markers = useMemo(() => ordersToMarkers(orders), [orders]);
  const stats = useMemo(() => reconstructRealizedStats(orders), [orders]);
  const agentReturn = useMemo(() => periodReturnPct(curve), [curve]);
  const spyReturn = useMemo(() => benchmarkReturnPct(prices['SPY']), [prices]);

  // ── Loading / error / not-connected states ────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-3 p-4">
        <div className="h-64 animate-pulse rounded-2xl bg-gray-100" />
        <div className="h-40 animate-pulse rounded-2xl bg-gray-100" />
      </div>
    );
  }

  if (error && !data) {
    return <div className="p-6 text-center text-sm text-red-500">Couldn’t load the agent portfolio. <button onClick={() => refresh()} className="ml-1 underline">Retry</button></div>;
  }

  if (!data?.is_connected || !data.agentic_account) {
    return (
      <div className="mx-auto mt-10 max-w-md rounded-2xl border border-gray-200 p-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 text-white">
          <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" /></svg>
        </div>
        <h2 className="text-base font-semibold text-gray-900">Your AI Trading Agent</h2>
        <p className="mx-auto mt-1.5 max-w-xs text-sm text-gray-500">Connect a Robinhood Agentic account to let Finch trade on your behalf — in its own account, with your limits.</p>
        <a href="https://github.com/anshultibby/finch/releases/latest/download/Finch-Connect-macOS.dmg"
          className="mt-5 inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-b from-emerald-500 to-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:brightness-105">
          Download Finch Connect
        </a>
        <button onClick={() => { window.location.href = 'finch-connect://open'; }} className="mt-2 block w-full text-[11px] text-gray-400 hover:text-emerald-600 transition-colors">
          Already installed? Open Finch Connect →
        </button>
        <p className="mt-2 text-[11px] text-gray-400">🔒 Robinhood only allows trading approval from an app on your device.</p>
      </div>
    );
  }

  const { total_value, agentic_account } = data;
  const totalUnrealized = holdings.reduce((s, h) => s + h.unrealized_pl, 0);
  const investedTotal = holdings.reduce((s, h) => s + (h.market_value || 0), 0);

  // Headline value + period change driven by the reconstructed curve, with live
  // scrubbing: hovering the line shows that point's value and its delta vs the
  // period start (Robinhood behavior).
  const liveValue = curve.length ? curve[curve.length - 1].value : Number(total_value ?? 0);
  const baseline = curve.length ? curve[0].value : liveValue;
  const shownValue = hover ? hover.value : liveValue;
  const periodDelta = shownValue - baseline;
  const periodDeltaPct = baseline > 0 ? (periodDelta / baseline) * 100 : 0;
  const haveCurve = curve.length >= 2;

  return (
    <div className="space-y-4 p-1">
      {/* ── Hero: equity curve ────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-gray-200 p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-medium text-emerald-600">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              AI Trading Agent · Agentic ••{agentic_account.account_number.slice(-4)}
            </div>
            <div className="mt-1 text-3xl font-bold tabular-nums tracking-tight text-gray-900">
              <CountUp value={shownValue} format={(n) => usd(n)} />
            </div>
            {haveCurve && (
              <div className={`mt-0.5 text-sm font-semibold tabular-nums ${pos(periodDelta)}`}>
                {signed(periodDelta)} ({signedPct(periodDeltaPct)})
                <span className="ml-1 font-normal text-gray-400">{rangeLabel === '1D' ? 'today' : rangeLabel}</span>
              </div>
            )}
          </div>
          <a
            href={ROBINHOOD_PORTFOLIO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-600 transition hover:border-emerald-200 hover:text-emerald-700"
          >
            {rhLogo && <img src={rhLogo} alt="" className="h-3.5 w-3.5 rounded-sm object-contain" />}
            View on Robinhood
            <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" /></svg>
          </a>
        </div>

        <div className="mt-3">
          <PriceRangeChart
            data={curve}
            format="currency"
            height={220}
            ranges={RANGES}
            selectedDays={days}
            onRangeChange={(d, label) => { setDays(d); setRangeLabel(label); setHover(null); }}
            onHoverChange={(info) => setHover(info ? { value: info.value } : null)}
            markers={markers}
          />
          {pricesLoading && !haveCurve && (
            <div className="py-8 text-center text-xs text-gray-400">Reconstructing returns…</div>
          )}
        </div>

        {/* Quick stats + benchmark */}
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-gray-100 pt-3 text-xs">
          <span className="text-gray-500">
            Unrealized <span className={`font-semibold tabular-nums ${pos(totalUnrealized)}`}>{signed(totalUnrealized)}</span>
          </span>
          <span className="text-gray-500">
            Cash <span className="font-semibold tabular-nums text-gray-700">{usd(data.cash)}</span>
          </span>
          <span className="text-gray-500">
            Buying power <span className="font-semibold tabular-nums text-gray-700">{usd(data.buying_power)}</span>
          </span>
          <span className="text-gray-500">
            <span className="font-semibold text-gray-700">{holdings.length}</span> position{holdings.length === 1 ? '' : 's'}
          </span>
          {agentReturn != null && spyReturn != null && (
            <span className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-gray-50 px-2.5 py-1">
              <span className="text-gray-400">vs S&P</span>
              <span className={`font-semibold tabular-nums ${pos(agentReturn)}`}>{signedPct(agentReturn)}</span>
              <span className="text-gray-300">/</span>
              <span className={`font-semibold tabular-nums ${pos(spyReturn)}`}>{signedPct(spyReturn)}</span>
              {agentReturn >= spyReturn
                ? <span className="rounded bg-emerald-50 px-1 text-[10px] font-bold text-emerald-600">BEATING</span>
                : <span className="rounded bg-red-50 px-1 text-[10px] font-bold text-red-500">TRAILING</span>}
            </span>
          )}
        </div>
      </div>

      {/* ── Performance strip (realized track record) ─────────────────────── */}
      {stats.closedTrades > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="Realized P&L" value={signed(stats.realizedPnl)} valueClass={pos(stats.realizedPnl)} />
          <Stat label="Win rate" value={`${Math.round(stats.winRate * 100)}%`} sub={`${stats.closedTrades} closed`} />
          <Stat label="Best trade" value={stats.bestTrade ? signed(stats.bestTrade.pnl) : '—'} sub={stats.bestTrade?.symbol} valueClass="text-emerald-600" />
          <Stat label="Worst trade" value={stats.worstTrade ? signed(stats.worstTrade.pnl) : '—'} sub={stats.worstTrade?.symbol} valueClass="text-red-500" />
        </div>
      )}

      {/* ── Holdings ──────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-gray-200">
        <div className="border-b border-gray-100 px-4 py-3 text-sm font-semibold text-gray-900">Holdings ({holdings.length})</div>
        {holdings.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-400">No open positions yet.</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {holdings.map((h) => {
              const alloc = investedTotal > 0 ? (h.market_value / investedTotal) * 100 : 0;
              return (
                <button key={h.symbol} onClick={() => onStockClick(h.symbol)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-gray-50">
                  <TickerLogo symbol={h.symbol} size={34} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900">{h.symbol}</span>
                      <span className="text-[11px] text-gray-400">{h.quantity} sh · avg {usd(h.average_buy_price)}</span>
                    </div>
                    {/* Allocation bar — how much of invested capital sits here. */}
                    <div className="mt-1.5 flex items-center gap-2">
                      <div className="h-1 w-20 overflow-hidden rounded-full bg-gray-100">
                        <div className="h-full rounded-full bg-emerald-400" style={{ width: `${Math.min(100, alloc)}%` }} />
                      </div>
                      <span className="text-[10px] text-gray-400">{alloc.toFixed(0)}%</span>
                    </div>
                  </div>
                  <div className="hidden sm:block"><MiniSparkline symbol={h.symbol} width={72} height={28} days={30} /></div>
                  <div className="text-right">
                    <div className="text-sm font-semibold tabular-nums text-gray-900">{usd(h.market_value)}</div>
                    <div className={`text-[11px] font-medium tabular-nums ${pos(h.unrealized_pl)}`}>
                      {signed(h.unrealized_pl)} ({h.unrealized_pct >= 0 ? '+' : ''}{h.unrealized_pct}%)
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Recent agent trades ───────────────────────────────────────────── */}
      <div className="rounded-2xl border border-gray-200">
        <div className="border-b border-gray-100 px-4 py-3 text-sm font-semibold text-gray-900">Recent trades</div>
        {orders.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-400">No trades yet.</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {orders.slice(0, 25).map((o, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span className={`text-xs font-bold ${o.side === 'sell' ? 'text-red-500' : 'text-emerald-600'}`}>{o.side === 'sell' ? '▼' : '▲'}</span>
                <span className="text-gray-700">{o.side === 'sell' ? 'Sold' : 'Bought'} {Number(o.quantity).toLocaleString()} <span className="font-semibold">{o.symbol}</span></span>
                <span className="ml-auto tabular-nums text-gray-500">{usd(o.price)}</span>
                <span className="w-16 text-right text-[11px] text-gray-400">{timeAgo(o.at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="px-2 pb-2 text-center text-[11px] text-gray-400">
        The agent trades only in this Agentic account — never your main accounts. Returns are reconstructed from filled orders and historical prices.
      </p>
    </div>
  );
}

function Stat({ label, value, sub, valueClass = 'text-gray-900' }: {
  label: string; value: string; sub?: string; valueClass?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 px-3 py-2.5">
      <div className="text-[11px] font-medium text-gray-400">{label}</div>
      <div className={`mt-0.5 text-base font-bold tabular-nums ${valueClass}`}>{value}</div>
      {sub && <div className="text-[10px] text-gray-400">{sub}</div>}
    </div>
  );
}
