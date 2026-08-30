'use client';

import React, { useEffect, useState } from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import { tradesApi, type RecentTrade } from '@/lib/api';
import { formatCurrency } from '@/lib/currency';

function fmtDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// The review prompt seeded into a new chat when a trade is tapped. The agent
// already gets the user's goal injected, so "against my goal" reinforces framing.
function reviewPrompt(t: RecentTrade): string {
  const action = t.side === 'BUY' ? 'bought' : 'sold';
  const price = formatCurrency(t.price, t.symbol);
  const amount = formatCurrency(t.amount, t.symbol);
  return `I ${action} ${t.quantity} shares of ${t.symbol} at ${price} on ${fmtDate(t.date)} (~${amount}). `
    + `Review this trade against my goal — was the entry, timing, and sizing sound? `
    + `Then suggest 2-3 concrete alternatives I could act on now, with the reasoning.`;
}

export default function RecentTradesFeedback({ onConnect }: { onConnect?: () => void }) {
  const { openChatAbout } = useNavigation();
  const [trades, setTrades] = useState<RecentTrade[] | null>(null);
  const [connected, setConnected] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    tradesApi.getRecent(10)
      .then((r) => {
        if (!alive) return;
        setConnected(r.connected);
        setTrades(r.trades || []);
      })
      .catch(() => { if (alive) setTrades([]); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  if (loading) return null;  // keep home snappy; no skeleton for the MVP

  if (!connected) {
    return (
      <div className="p-4">
        <h2 className="text-sm font-semibold text-gray-900 mb-2">Trade feedback</h2>
        <div className="rounded-xl border border-gray-100 p-4 text-sm text-gray-600">
          Connect your brokerage and Finch will review your recent trades and suggest
          better alternatives.
          {onConnect && (
            <button
              onClick={onConnect}
              className="mt-3 block w-full px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 transition-colors"
            >
              Connect brokerage
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!trades || trades.length === 0) return null;

  return (
    <div className="p-4">
      <h2 className="text-sm font-semibold text-gray-900 mb-1">Review a recent trade</h2>
      <p className="text-xs text-gray-400 mb-3">
        Tap a trade — Finch critiques it and suggests alternatives.
      </p>
      <div className="space-y-2">
        {trades.map((t) => (
          <button
            key={t.id}
            onClick={() => openChatAbout(t.symbol, reviewPrompt(t), {
              source: 'trade_feedback', symbol: t.symbol, trade: t,
            })}
            className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl border border-gray-100 hover:border-gray-200 hover:bg-gray-50 transition-all text-left"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                t.side === 'BUY' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
              }`}>
                {t.side}
              </span>
              <span className="text-sm font-semibold text-gray-900">{t.symbol}</span>
              <span className="text-xs text-gray-400 truncate">
                {t.quantity} sh · {fmtDate(t.date)}
              </span>
            </div>
            <span className="text-sm font-medium text-gray-600 flex-shrink-0">
              {formatCurrency(t.amount, t.symbol)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
