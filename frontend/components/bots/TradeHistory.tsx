'use client';

import React, { useEffect, useState } from 'react';
import { ArrowUpRight, ArrowDownRight, AlertCircle, Clock, CheckCircle, XCircle } from 'lucide-react';
import type { TradeLog } from '@/lib/types';
import { tradesApi } from '@/lib/api';

interface TradeHistoryProps {
  userId: string;
  botId?: string;
  refreshKey?: number;
}

function StatusBadge({ status }: { status: TradeLog['status'] }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    executed: { bg: 'bg-green-100', text: 'text-green-700', icon: <CheckCircle size={10} /> },
    dry_run: { bg: 'bg-amber-100', text: 'text-amber-700', icon: <Clock size={10} /> },
    failed: { bg: 'bg-red-100', text: 'text-red-700', icon: <XCircle size={10} /> },
    pending_approval: { bg: 'bg-blue-100', text: 'text-blue-700', icon: <Clock size={10} /> },
    approved: { bg: 'bg-green-100', text: 'text-green-700', icon: <CheckCircle size={10} /> },
    rejected: { bg: 'bg-red-100', text: 'text-red-700', icon: <XCircle size={10} /> },
    expired: { bg: 'bg-gray-100', text: 'text-gray-500', icon: <AlertCircle size={10} /> },
  };
  const c = config[status] || config.failed;
  return (
    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium uppercase ${c.bg} ${c.text}`}>
      {c.icon}
      {status.replace('_', ' ')}
    </span>
  );
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
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

export default function TradeHistory({ userId, botId, refreshKey }: TradeHistoryProps) {
  const [trades, setTrades] = useState<TradeLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = botId
          ? await tradesApi.listForBot(userId, botId)
          : await tradesApi.listAll(userId);
        setTrades(data);
      } catch {
        setTrades([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [userId, botId, refreshKey]);

  if (loading) {
    return (
      <div className="px-4 py-3">
        <div className="text-xs text-gray-400 animate-pulse">Loading trades...</div>
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className="px-4 py-3">
        <div className="text-xs text-gray-400">No trades yet</div>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {trades.map((t) => (
        <div
          key={t.id}
          className="px-3 py-2 rounded-lg border border-gray-100 bg-white"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-1.5 min-w-0">
              {t.action === 'buy' ? (
                <ArrowUpRight size={14} className="text-green-500 shrink-0" />
              ) : (
                <ArrowDownRight size={14} className="text-red-500 shrink-0" />
              )}
              <div className="min-w-0">
                <div className="text-xs font-medium text-gray-700 truncate">
                  {t.market_title || t.market}
                </div>
                {!botId && t.bot_name && (
                  <div className="text-[10px] text-gray-400 truncate">
                    {t.bot_icon} {t.bot_name}
                  </div>
                )}
              </div>
            </div>
            <StatusBadge status={t.status} />
          </div>
          <div className="flex items-center gap-3 mt-1.5 text-[11px] text-gray-400">
            <span className="uppercase font-medium">{t.action}</span>
            {t.side && <span>{t.side}</span>}
            {t.quantity != null && t.price != null && (
              <span>x{t.quantity} @ {t.price}c</span>
            )}
            {t.cost_usd != null && (
              <span className="font-medium text-gray-500">${t.cost_usd.toFixed(2)}</span>
            )}
            <span className="ml-auto">{formatTime(t.created_at)}</span>
          </div>
          {t.error && (
            <div className="mt-1 text-[10px] text-red-500 truncate">{t.error}</div>
          )}
        </div>
      ))}
    </div>
  );
}
