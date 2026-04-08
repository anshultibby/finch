'use client';

import React from 'react';
import type { TradeLog } from '@/lib/types';
import { tradesApi } from '@/lib/api';
import { ArrowUpRight, ArrowDownRight, Check, X } from 'lucide-react';

interface BotTradesPanelProps {
  userId: string;
  botId: string;
  refreshKey?: number;
  onBack: () => void;
  onTradeAction?: () => void;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

const statusConfig: Record<string, { label: string; color: string }> = {
  executed: { label: 'Executed', color: 'text-emerald-600' },
  partial: { label: 'Partial', color: 'text-amber-500' },
  resting: { label: 'Resting', color: 'text-blue-400' },
  failed: { label: 'Failed', color: 'text-red-500' },
  pending_approval: { label: 'Pending', color: 'text-amber-600' },
  approved: { label: 'Approved', color: 'text-emerald-600' },
  rejected: { label: 'Rejected', color: 'text-red-400' },
  expired: { label: 'Expired', color: 'text-gray-400' },
};

export default function BotTradesPanel({ userId, botId, refreshKey, onBack, onTradeAction }: BotTradesPanelProps) {
  const [trades, setTrades] = React.useState<TradeLog[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [acting, setActing] = React.useState<Record<string, boolean>>({});

  const load = React.useCallback(() => {
    setLoading(true);
    tradesApi.listForBot(userId, botId)
      .then(setTrades)
      .catch(() => setTrades([]))
      .finally(() => setLoading(false));
  }, [userId, botId]);

  React.useEffect(() => { load(); }, [load, refreshKey]);

  async function handleApprove(trade: TradeLog) {
    setActing(a => ({ ...a, [trade.id]: true }));
    try {
      await tradesApi.approve(userId, trade.id);
    } catch {
      // error will show in the updated trade status
    } finally {
      setActing(a => ({ ...a, [trade.id]: false }));
      load();
      onTradeAction?.();
    }
  }

  async function handleReject(trade: TradeLog) {
    setActing(a => ({ ...a, [trade.id]: true }));
    try {
      await tradesApi.reject(userId, trade.id);
    } finally {
      setActing(a => ({ ...a, [trade.id]: false }));
      load();
      onTradeAction?.();
    }
  }

  const pendingTrades = trades.filter(t => t.status === 'pending_approval');
  const otherTrades = trades.filter(t => t.status !== 'pending_approval');

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100 shrink-0">
        <button
          onClick={onBack}
          className="p-1 -ml-1 text-gray-400 hover:text-gray-600 transition-colors rounded-lg hover:bg-gray-50"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
        <div>
          <h2 className="text-sm font-semibold text-gray-900">Trade History</h2>
          <p className="text-[11px] text-gray-400">{loading ? '…' : `${trades.length} orders`}</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center pt-12">
            <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-400 rounded-full animate-spin" />
          </div>
        ) : trades.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <span className="text-3xl mb-3">🔄</span>
            <p className="text-sm font-medium text-gray-500">No trades yet</p>
            <p className="text-xs text-gray-400 mt-1">Orders placed by the bot will appear here.</p>
          </div>
        ) : (
          <>
            {/* Pending approval section */}
            {pendingTrades.length > 0 && (
              <div className="border-b border-amber-100 bg-amber-50/50">
                <div className="px-6 py-2 text-[10px] font-semibold text-amber-700 uppercase tracking-wide">
                  Awaiting your approval ({pendingTrades.length})
                </div>
                {pendingTrades.map((t) => (
                  <PendingTradeRow
                    key={t.id}
                    trade={t}
                    acting={acting[t.id]}
                    onApprove={() => handleApprove(t)}
                    onReject={() => handleReject(t)}
                  />
                ))}
              </div>
            )}

            {/* Trade history */}
            <div className="divide-y divide-gray-100">
              {otherTrades.map((t) => (
                <TradeRow key={t.id} trade={t} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function PendingTradeRow({
  trade: t,
  acting,
  onApprove,
  onReject,
}: {
  trade: TradeLog;
  acting?: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <div className="px-6 py-3 border-b border-amber-100 last:border-0">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {t.action === 'buy' ? (
            <ArrowUpRight size={14} className="text-emerald-500 shrink-0" />
          ) : (
            <ArrowDownRight size={14} className="text-red-500 shrink-0" />
          )}
          <div className="min-w-0">
            <div className="text-[13px] font-medium text-gray-800 truncate">
              {t.market_title || t.market}
            </div>
            <div className="flex items-center flex-wrap gap-2 mt-0.5 text-[11px] text-gray-400">
              <span className="font-semibold uppercase text-[10px]">{t.action}</span>
              {t.side && (
                <span className={`px-1 py-0.5 rounded text-[10px] font-semibold ${t.side === 'yes' ? 'bg-blue-50 text-blue-600' : 'bg-orange-50 text-orange-600'}`}>
                  {t.side}
                </span>
              )}
              {t.quantity != null && t.price != null && <span>×{t.quantity} @ {t.price}¢</span>}
              {t.cost_usd != null && <span className="font-medium text-gray-500">${t.cost_usd.toFixed(2)}</span>}
            </div>
            {t.reason && (
              <div className="mt-1 text-[11px] text-gray-500 italic truncate max-w-[240px]">
                "{t.reason}"
              </div>
            )}
          </div>
        </div>
        <div className="text-[10px] text-gray-400 shrink-0">{formatTime(t.created_at)}</div>
      </div>
      <div className="flex gap-2 mt-2">
        <button
          onClick={onApprove}
          disabled={acting}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-[11px] font-semibold transition-colors disabled:opacity-50"
        >
          <Check size={11} />
          Approve
        </button>
        <button
          onClick={onReject}
          disabled={acting}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 text-[11px] font-semibold transition-colors disabled:opacity-50"
        >
          <X size={11} />
          Reject
        </button>
      </div>
    </div>
  );
}

function TradeRow({ trade: t }: { trade: TradeLog }) {
  const s = statusConfig[t.status] || { label: t.status, color: 'text-gray-400' };
  return (
    <div className="px-6 py-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {t.action === 'buy' ? (
            <ArrowUpRight size={14} className="text-emerald-500 shrink-0" />
          ) : (
            <ArrowDownRight size={14} className="text-red-500 shrink-0" />
          )}
          <div className="min-w-0">
            <div className="text-[13px] font-medium text-gray-800 truncate">
              {t.market_title || t.market}
            </div>
            <div className="flex items-center gap-2 mt-0.5 text-[11px] text-gray-400">
              <span className="font-semibold uppercase text-[10px]">{t.action}</span>
              {t.side && (
                <span className={`px-1 py-0.5 rounded text-[10px] font-semibold ${t.side === 'yes' ? 'bg-blue-50 text-blue-600' : 'bg-orange-50 text-orange-600'}`}>
                  {t.side}
                </span>
              )}
              {t.quantity != null && t.price != null && <span>×{t.quantity} @ {t.price}¢</span>}
              {t.cost_usd != null && <span className="font-medium text-gray-500">${t.cost_usd.toFixed(2)}</span>}
              {t.realized_pnl_usd != null && (
                <span className={`font-medium ${t.realized_pnl_usd >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {t.realized_pnl_usd >= 0 ? '+' : ''}${t.realized_pnl_usd.toFixed(2)}
                </span>
              )}
            </div>
            {t.reason && (
              <div className="mt-0.5 text-[10px] text-gray-400 italic truncate max-w-[240px]">
                "{t.reason}"
              </div>
            )}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className={`text-[11px] font-medium ${s.color}`}>{s.label}</div>
          <div className="text-[10px] text-gray-400 mt-0.5">{formatTime(t.created_at)}</div>
        </div>
      </div>
      {t.error && (
        <div className="mt-1 text-[10px] text-red-500 truncate">{t.error}</div>
      )}
    </div>
  );
}
