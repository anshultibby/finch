'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Minus, Clock, X, DollarSign, TrendingUp, Search, BarChart3, Pencil, Check } from 'lucide-react';
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

function formatUsd(value: number): string {
  return `$${value.toFixed(2)}`;
}

function getPlatformInfo(platform: string): { label: string; icon: React.ReactNode } {
  switch (platform) {
    case 'kalshi':
      return { label: 'Kalshi', icon: <TrendingUp className="w-3.5 h-3.5" /> };
    case 'alpaca':
      return { label: 'Brokerage', icon: <BarChart3 className="w-3.5 h-3.5" /> };
    case 'research':
      return { label: 'Research', icon: <Search className="w-3.5 h-3.5" /> };
    default:
      return { label: platform, icon: <TrendingUp className="w-3.5 h-3.5" /> };
  }
}

function PositionCard({ position, onClose }: { position: BotPosition; onClose?: () => void }) {
  const pnl = position.unrealized_pnl_usd ?? 0;
  const pnlColor = pnl >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="p-3 rounded-xl border border-gray-100 bg-white">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {position.market_title && (
            <div className="text-[13px] text-gray-800 leading-snug line-clamp-2">{position.market_title}</div>
          )}
          {!position.market_title && (
            <div className="text-xs font-mono text-gray-500 truncate">{position.market}</div>
          )}
        </div>
        <span className={`text-sm font-semibold ${pnlColor} whitespace-nowrap tabular-nums`}>
          {formatPnl(pnl)}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-2 text-[11px] text-gray-400">
        {position.paper && (
          <span className="px-1.5 py-0.5 rounded-md bg-amber-50 text-amber-600 font-semibold text-[10px] uppercase">Paper</span>
        )}
        <span className="font-medium text-gray-500">{position.side.toUpperCase()}</span>
        <span className="text-gray-300">&middot;</span>
        <span className="tabular-nums">{position.entry_price}c &rarr; {position.current_price ?? '?'}c</span>
        <span className="text-gray-300">&middot;</span>
        <span className="tabular-nums">x{position.quantity}</span>
      </div>
      {position.monitor_note && (
        <div className="mt-1.5 text-[11px] text-gray-400 italic">{position.monitor_note}</div>
      )}
      {onClose && (
        <button
          onClick={onClose}
          className="mt-2 text-[11px] font-medium text-red-500 hover:text-red-700 transition-colors"
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
  const [showCapitalInput, setShowCapitalInput] = useState(false);
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
  const initialCapital = bot.capital?.amount_usd;
  const platformInfo = getPlatformInfo(bot.platform);
  const isResearch = bot.platform === 'research';

  // Compute capital deployed in open positions
  const deployedCapital = positions.reduce((sum, p) => sum + (p.cost_usd || 0), 0);

  const handleCapitalAdjust = async (direction: 'add' | 'withdraw') => {
    const amount = parseFloat(capitalInput);
    if (!amount || amount <= 0) return;
    setAdjusting(true);
    try {
      await botsApi.adjustCapital(userId, bot.id, direction === 'add' ? amount : -amount);
      setCapitalInput('');
      setShowCapitalInput(false);
      onCapitalChanged?.();
    } catch (e: any) {
      alert(e.message || 'Failed to adjust capital');
    } finally {
      setAdjusting(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50/80 border-l border-gray-200 overflow-y-auto">
      <div className="p-4 space-y-4">
        {/* Bot info header */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white border border-gray-100 text-gray-500">
            {platformInfo.icon}
            <span className="text-[11px] font-semibold uppercase tracking-wide">{platformInfo.label}</span>
          </div>
          {bot.paper_mode && (
            <span className="px-2 py-1 rounded-lg bg-amber-50 border border-amber-100 text-[11px] font-semibold text-amber-600 uppercase tracking-wide">
              Paper
            </span>
          )}
        </div>

        {/* Capital section */}
        {!isResearch && (
          <section className="rounded-xl bg-white border border-gray-100 overflow-hidden">
            <div className="p-3.5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Capital</h3>
                <button
                  onClick={() => setShowCapitalInput(!showCapitalInput)}
                  className="text-gray-300 hover:text-gray-500 transition-colors"
                  title="Adjust capital"
                >
                  {showCapitalInput ? <X className="w-3.5 h-3.5" /> : <Pencil className="w-3.5 h-3.5" />}
                </button>
              </div>

              {/* Balance */}
              <div className="text-2xl font-bold text-gray-900 tabular-nums tracking-tight">
                {balance != null ? formatUsd(balance) : '$0.00'}
              </div>
              <div className="text-[11px] text-gray-400 mt-0.5">Available balance</div>

              {/* Breakdown */}
              {(deployedCapital > 0 || (initialCapital != null && initialCapital > 0)) && (
                <div className="mt-3 pt-3 border-t border-gray-100 space-y-1.5">
                  {deployedCapital > 0 && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">In positions</span>
                      <span className="font-medium text-gray-600 tabular-nums">{formatUsd(deployedCapital)}</span>
                    </div>
                  )}
                  {initialCapital != null && initialCapital > 0 && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">Total allocated</span>
                      <span className="font-medium text-gray-600 tabular-nums">{formatUsd((balance ?? 0) + deployedCapital)}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Adjust input */}
              {showCapitalInput && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <div className="flex items-center gap-1.5">
                    <div className="relative flex-1 min-w-0">
                      <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">$</span>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="0.00"
                        value={capitalInput}
                        onChange={(e) => setCapitalInput(e.target.value)}
                        autoFocus
                        className="w-full pl-6 pr-2 py-1.5 text-xs bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 tabular-nums"
                      />
                    </div>
                    <button
                      onClick={() => handleCapitalAdjust('add')}
                      disabled={adjusting || !capitalInput}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-100 disabled:opacity-40 transition-colors"
                      title="Deposit"
                    >
                      <Plus size={14} />
                    </button>
                    <button
                      onClick={() => handleCapitalAdjust('withdraw')}
                      disabled={adjusting || !capitalInput}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 border border-red-100 disabled:opacity-40 transition-colors"
                      title="Withdraw"
                    >
                      <Minus size={14} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* P&L */}
        <section className="rounded-xl bg-white border border-gray-100 p-3.5">
          <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2.5">Performance</h3>
          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <div className="text-[11px] text-gray-400 mb-0.5">Live P&L</div>
              <div className={`text-lg font-bold tabular-nums ${totalPnl > 0 ? 'text-emerald-600' : totalPnl < 0 ? 'text-red-500' : 'text-gray-300'}`}>
                {formatPnl(totalPnl)}
              </div>
            </div>
            <div>
              <div className="text-[11px] text-gray-400 mb-0.5">Runs</div>
              <div className="text-lg font-bold text-gray-700 tabular-nums">{stats.total_runs ?? 0}</div>
            </div>
            {(hasPaper || paperPnl !== 0) && (
              <div className="col-span-2 p-2 rounded-lg bg-amber-50/60 border border-amber-100">
                <div className="text-[11px] text-amber-600 mb-0.5">Paper P&L</div>
                <div className={`text-sm font-bold tabular-nums ${paperPnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {formatPnl(paperPnl)}
                </div>
              </div>
            )}
          </div>
          {stats.last_run_summary && (
            <div className="mt-2.5 pt-2.5 border-t border-gray-100 text-[11px] text-gray-500 leading-relaxed">
              <span className="font-medium text-gray-600">Last run:</span> {stats.last_run_summary}
            </div>
          )}
        </section>

        {/* Open Positions */}
        {positions.length > 0 && (
          <section>
            <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Open Positions ({positions.length})
            </h3>
            <div className="space-y-2">
              {positions.map((p) => (
                <PositionCard
                  key={p.id}
                  position={p}
                  onClose={onClosePosition ? () => onClosePosition(p.id) : undefined}
                />
              ))}
            </div>
          </section>
        )}

        {/* Closed Positions */}
        {closedPositions.length > 0 && (
          <section>
            <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Recent Closes ({closedPositions.length})
            </h3>
            <div className="space-y-1.5">
              {closedPositions.slice(0, 5).map((p) => {
                const pnl = p.realized_pnl_usd ?? 0;
                return (
                  <div key={p.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-white border border-gray-100">
                    <div className="min-w-0 flex-1">
                      <div className="text-[12px] text-gray-600 truncate">{p.market_title || p.market}</div>
                    </div>
                    <span className={`text-xs font-semibold tabular-nums ml-2 ${pnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      {formatPnl(pnl)}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Wakeups */}
        {wakeups.length > 0 && (
          <section>
            <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Scheduled ({wakeups.length})
            </h3>
            <div className="space-y-1.5">
              {wakeups.map((w) => (
                <div
                  key={w.id}
                  className="flex items-start gap-2 px-3 py-2 rounded-xl bg-white border border-gray-100 text-xs"
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

        {/* Context Files */}
        {files.length > 0 && (
          <section>
            <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Context ({files.length})
            </h3>
            <div className="space-y-1">
              {files.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-gray-600 bg-white border border-gray-100"
                >
                  <span className="text-gray-400 text-[11px]">
                    {f.file_type === 'context' ? '📄' : f.file_type === 'memory' ? '🧠' : '📝'}
                  </span>
                  <span className="truncate">{f.filename}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Trade History */}
        <section>
          <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Trade History
          </h3>
          <TradeHistory userId={userId} botId={bot.id} />
        </section>
      </div>
    </div>
  );
}
