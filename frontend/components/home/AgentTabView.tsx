'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { robinhoodApi, type RobinhoodPortfolioResponse } from '@/lib/api';

function usd(v?: string | number | null): string {
  if (v == null) return '—';
  const n = Number(v);
  return Number.isNaN(n) ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(n);
}
function signed(n: number): string {
  const s = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Math.abs(n));
  return `${n >= 0 ? '+' : '−'}${s}`;
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

export default function AgentTabView({ userId, onStockClick }: {
  userId: string;
  onStockClick: (symbol: string) => void;
}) {
  const [data, setData] = useState<RobinhoodPortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await robinhoodApi.getPortfolio(userId)); setError(null); }
    catch { setError('Couldn’t load the agent portfolio.'); }
    finally { setLoading(false); }
  }, [userId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="space-y-3 p-4">
        <div className="h-24 animate-pulse rounded-2xl bg-gray-100" />
        <div className="h-40 animate-pulse rounded-2xl bg-gray-100" />
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-center text-sm text-red-500">{error} <button onClick={load} className="ml-1 underline">Retry</button></div>;
  }

  // Not connected → point to the desktop app (Robinhood agent is desktop-only).
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

  const { holdings, orders, total_value, buying_power, agentic_account } = data;
  const totalUnrealized = holdings.reduce((s, h) => s + h.unrealized_pl, 0);

  return (
    <div className="space-y-4 p-1">
      {/* Headline */}
      <div className="rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50 to-white p-5">
        <div className="flex items-center gap-2 text-[11px] font-medium text-emerald-600">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          AI Trading Agent · Agentic ••{agentic_account.account_number.slice(-4)}
        </div>
        <div className="mt-1 flex items-end justify-between">
          <div>
            <div className="text-3xl font-bold tabular-nums tracking-tight text-gray-900">{usd(total_value)}</div>
            <div className={`mt-0.5 text-sm font-semibold tabular-nums ${pos(totalUnrealized)}`}>{signed(totalUnrealized)} unrealized</div>
          </div>
          <div className="text-right text-xs text-gray-400">
            <div>Buying power</div>
            <div className="font-semibold tabular-nums text-gray-700">{usd(buying_power)}</div>
          </div>
        </div>
      </div>

      {/* Holdings */}
      <div className="rounded-2xl border border-gray-200">
        <div className="border-b border-gray-100 px-4 py-3 text-sm font-semibold text-gray-900">Holdings ({holdings.length})</div>
        {holdings.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-400">No open positions yet.</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {holdings.map((h) => (
              <button key={h.symbol} onClick={() => onStockClick(h.symbol)}
                className="flex w-full items-center justify-between px-4 py-3 text-left transition hover:bg-gray-50">
                <div>
                  <div className="text-sm font-semibold text-gray-900">{h.symbol}</div>
                  <div className="text-[11px] text-gray-400">{h.quantity} sh · avg {usd(h.average_buy_price)}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold tabular-nums text-gray-900">{usd(h.market_value)}</div>
                  <div className={`text-[11px] font-medium tabular-nums ${pos(h.unrealized_pl)}`}>
                    {signed(h.unrealized_pl)} ({h.unrealized_pct >= 0 ? '+' : ''}{h.unrealized_pct}%)
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Recent agent trades */}
      <div className="rounded-2xl border border-gray-200">
        <div className="border-b border-gray-100 px-4 py-3 text-sm font-semibold text-gray-900">Recent trades</div>
        {orders.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-400">No trades yet.</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {orders.map((o, i) => (
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

      <p className="px-2 pb-2 text-center text-[11px] text-gray-400">The agent trades only in this Agentic account — never your main accounts.</p>
    </div>
  );
}
