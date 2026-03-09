'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Minus, Clock, X } from 'lucide-react';
import type { BotDetail, BotPosition, BotWakeup } from '@/lib/types';
import { botsApi } from '@/lib/api';
import TradeHistory from './TradeHistory';

interface BotSidebarProps {
  bot: BotDetail;
  userId: string;
  onClosePosition?: (positionId: string) => void;
  onCapitalChanged?: () => void;
}

function formatPnl(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function PositionCard({ position, onClose }: { position: BotPosition; onClose?: () => void }) {
  const pnl = position.unrealized_pnl_usd ?? 0;
  const pnlColor = pnl >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="p-3 rounded-lg border border-gray-200 bg-white">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-xs font-mono text-gray-500 truncate">{position.market}</div>
          {position.market_title && (
            <div className="text-sm text-gray-800 mt-0.5 line-clamp-2">{position.market_title}</div>
          )}
        </div>
        <span className={`text-sm font-semibold ${pnlColor} whitespace-nowrap`}>
          {formatPnl(pnl)}
        </span>
      </div>
      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
        {position.paper && (
          <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium text-[10px] uppercase">Paper</span>
        )}
        <span>{position.side.toUpperCase()}</span>
        <span>{position.entry_price}c &rarr; {position.current_price ?? '?'}c</span>
        <span>x{position.quantity}</span>
      </div>
      {position.monitor_note && (
        <div className="mt-1.5 text-xs text-gray-500 italic">{position.monitor_note}</div>
      )}
      {onClose && (
        <button
          onClick={onClose}
          className="mt-2 text-xs text-red-500 hover:text-red-700 transition-colors"
        >
          Close position
        </button>
      )}
    </div>
  );
}

export default function BotSidebar({ bot, userId, onClosePosition, onCapitalChanged }: BotSidebarProps) {
  const positions = bot.positions || [];
  const closedPositions = bot.closed_positions || [];
  const files = bot.files || [];
  const stats = bot.stats || {};
  const [capitalInput, setCapitalInput] = useState('');
  const [adjusting, setAdjusting] = useState(false);
  const [wakeups, setWakeups] = useState<BotWakeup[]>([]);

  useEffect(() => {
    botsApi.listWakeups(userId, bot.id).then(setWakeups).catch(() => {});
  }, [userId, bot.id]);

  const totalPnl = (bot.total_profit_usd || 0) + (bot.open_unrealized_pnl || 0);
  const paperPnl = (stats.paper_profit_usd || 0) + (stats.paper_unrealized_pnl || 0);
  const hasPaper = positions.some((p) => p.paper);
  const balance = bot.capital_balance;

  const handleCapitalAdjust = async (direction: 'add' | 'withdraw') => {
    const amount = parseFloat(capitalInput);
    if (!amount || amount <= 0) return;
    setAdjusting(true);
    try {
      await botsApi.adjustCapital(userId, bot.id, direction === 'add' ? amount : -amount);
      setCapitalInput('');
      onCapitalChanged?.();
    } catch (e: any) {
      alert(e.message || 'Failed to adjust capital');
    } finally {
      setAdjusting(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 border-l border-gray-200 overflow-y-auto">
      <div className="p-4 space-y-5">
        {/* Capital */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Capital
          </h3>
          <div className="px-3 py-2 rounded-lg bg-white border border-gray-200">
            <div className="text-xs text-gray-400">Balance</div>
            <div className="text-lg font-semibold text-gray-800 tabular-nums">
              {balance != null ? `$${balance.toFixed(2)}` : 'Not set'}
            </div>
            <div className="flex items-center gap-1.5 mt-2">
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="$0.00"
                value={capitalInput}
                onChange={(e) => setCapitalInput(e.target.value)}
                className="flex-1 min-w-0 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-gray-300"
              />
              <button
                onClick={() => handleCapitalAdjust('add')}
                disabled={adjusting || !capitalInput}
                className="p-1 rounded border border-gray-200 text-green-600 hover:bg-green-50 disabled:opacity-40 transition-colors"
                title="Deposit"
              >
                <Plus size={14} />
              </button>
              <button
                onClick={() => handleCapitalAdjust('withdraw')}
                disabled={adjusting || !capitalInput}
                className="p-1 rounded border border-gray-200 text-red-500 hover:bg-red-50 disabled:opacity-40 transition-colors"
                title="Withdraw"
              >
                <Minus size={14} />
              </button>
            </div>
          </div>
        </section>

        {/* Positions */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Positions ({positions.length})
          </h3>
          {positions.length === 0 ? (
            <p className="text-xs text-gray-400">No open positions</p>
          ) : (
            <div className="space-y-2">
              {positions.map((p) => (
                <PositionCard
                  key={p.id}
                  position={p}
                  onClose={onClosePosition ? () => onClosePosition(p.id) : undefined}
                />
              ))}
            </div>
          )}
        </section>

        {/* Context Files */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Context
          </h3>
          {files.length === 0 ? (
            <p className="text-xs text-gray-400">No context files</p>
          ) : (
            <div className="space-y-1">
              {files.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 px-2 py-1.5 rounded text-xs text-gray-600 bg-white border border-gray-100"
                >
                  <span className="text-gray-400">
                    {f.file_type === 'context' ? '📄' : f.file_type === 'memory' ? '🧠' : '📝'}
                  </span>
                  <span className="truncate">{f.filename}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Stats */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Stats
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <div className="px-2 py-1.5 rounded bg-white border border-gray-100">
              <div className="text-xs text-gray-400">Live P&L</div>
              <div className={`text-sm font-semibold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPnl(totalPnl)}
              </div>
            </div>
            <div className="px-2 py-1.5 rounded bg-white border border-gray-100">
              <div className="text-xs text-gray-400">Ticks</div>
              <div className="text-sm font-semibold text-gray-700">{stats.total_runs ?? 0}</div>
            </div>
            {(hasPaper || paperPnl !== 0) && (
              <div className="px-2 py-1.5 rounded bg-amber-50 border border-amber-100">
                <div className="text-xs text-amber-600">Paper P&L</div>
                <div className={`text-sm font-semibold ${paperPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatPnl(paperPnl)}
                </div>
              </div>
            )}
          </div>
          {stats.last_run_summary && (
            <div className="mt-2 text-xs text-gray-500">
              <span className="font-medium">Last:</span> {stats.last_run_summary}
            </div>
          )}
        </section>

        {/* Wakeups */}
        {wakeups.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Scheduled Wakeups ({wakeups.length})
            </h3>
            <div className="space-y-1.5">
              {wakeups.map((w) => (
                <div
                  key={w.id}
                  className="flex items-start gap-2 px-2.5 py-2 rounded-lg bg-white border border-gray-100 text-xs"
                >
                  <Clock size={12} className="text-gray-400 mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-gray-700 line-clamp-2">{w.reason}</div>
                    <div className="text-gray-400 mt-0.5">
                      {new Date(w.trigger_at).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                      })}
                      <span className="ml-1.5 text-gray-300">{w.trigger_type}</span>
                    </div>
                  </div>
                  <button
                    onClick={async () => {
                      try {
                        await botsApi.cancelWakeup(userId, bot.id, w.id);
                        setWakeups((prev) => prev.filter((x) => x.id !== w.id));
                      } catch {}
                    }}
                    className="p-0.5 rounded text-gray-300 hover:text-red-500 transition-colors shrink-0"
                    title="Cancel wakeup"
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Trade History */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Trade History
          </h3>
          <TradeHistory userId={userId} botId={bot.id} />
        </section>
      </div>
    </div>
  );
}
