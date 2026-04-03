'use client';

import React, { useState } from 'react';
import type { Bot } from '@/lib/types';
import { Plus, Loader2, MoreHorizontal, Trash2 } from 'lucide-react';

interface BotCardProps {
  bot: Bot;
  onClick: () => void;
  onDelete?: (id: string) => void;
}

function getPlatformLabel(platform: string): string | null {
  switch (platform) {
    case 'kalshi': return 'Kalshi';
    case 'alpaca': return 'Brokerage';
    case 'research': return 'Research';
    default: return null;
  }
}

function getPlatformAccent(platform: string) {
  switch (platform) {
    case 'kalshi': return {
      gradient: 'from-violet-500 to-purple-600',
      bg: 'bg-violet-50',
      text: 'text-violet-600',
      ring: 'ring-violet-200',
      dot: 'bg-violet-400',
    };
    case 'alpaca': return {
      gradient: 'from-emerald-400 to-teal-600',
      bg: 'bg-emerald-50',
      text: 'text-emerald-600',
      ring: 'ring-emerald-200',
      dot: 'bg-emerald-400',
    };
    case 'research': return {
      gradient: 'from-blue-400 to-indigo-600',
      bg: 'bg-blue-50',
      text: 'text-blue-600',
      ring: 'ring-blue-200',
      dot: 'bg-blue-400',
    };
    default: return {
      gradient: 'from-gray-400 to-slate-600',
      bg: 'bg-gray-50',
      text: 'text-gray-600',
      ring: 'ring-gray-200',
      dot: 'bg-gray-400',
    };
  }
}

function formatPnl(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function BotCard({ bot, onClick, onDelete }: BotCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const totalPnl = (bot.total_profit_usd || 0) + (bot.open_unrealized_pnl || 0);
  const accent = getPlatformAccent(bot.platform);

  return (
    <button
      onClick={onClick}
      className="group relative flex flex-col items-start p-5 rounded-2xl bg-white border border-gray-100/80 hover:border-gray-200/80 transition-all duration-300 text-left w-full finch-surface-hover overflow-hidden"
    >
      {/* Platform accent strip at top */}
      <div className={`absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r ${accent.gradient} opacity-60 group-hover:opacity-100 transition-opacity duration-300`} />

      {/* Top row: icon + menu */}
      <div className="flex items-start justify-between w-full mb-3">
        <div className={`w-11 h-11 rounded-xl ${accent.bg} flex items-center justify-center text-2xl group-hover:scale-105 transition-transform duration-300 relative`}>
          {bot.icon || '🤖'}
        </div>
        <div className="flex items-center gap-2">
          {/* Active indicator */}
          {bot.enabled && (
            <span className="flex items-center gap-1.5 text-[10px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 live-pulse" />
              Live
            </span>
          )}
          {onDelete && (
            <div className="relative">
              <span
                role="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setMenuOpen(!menuOpen);
                  setConfirming(false);
                }}
                className="p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-gray-100 transition-all cursor-pointer"
              >
                <MoreHorizontal className="w-3.5 h-3.5 text-gray-400" />
              </span>
              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={(e) => { e.stopPropagation(); setMenuOpen(false); }} />
                  <div className="absolute right-0 top-7 z-50 w-36 bg-white rounded-xl border border-gray-100 shadow-lg shadow-gray-200/60 py-1">
                    {confirming ? (
                      <div className="px-3 py-2">
                        <p className="text-xs text-gray-500 mb-2">Delete this bot?</p>
                        <div className="flex gap-1.5">
                          <span
                            role="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setMenuOpen(false);
                              setConfirming(false);
                              onDelete(bot.id);
                            }}
                            className="flex-1 text-center text-xs font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg py-1.5 transition-colors cursor-pointer"
                          >
                            Delete
                          </span>
                          <span
                            role="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirming(false);
                              setMenuOpen(false);
                            }}
                            className="flex-1 text-center text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg py-1.5 transition-colors cursor-pointer"
                          >
                            Cancel
                          </span>
                        </div>
                      </div>
                    ) : (
                      <span
                        role="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirming(true);
                        }}
                        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete bot
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Name */}
      <h3 className="text-[15px] font-semibold text-gray-900 truncate w-full leading-tight">
        {bot.name}
      </h3>
      {bot.platform && (
        <span className={`text-[10px] font-semibold uppercase tracking-wider mt-0.5 ${accent.text}`}>
          {bot.platform === 'alpaca' ? 'Brokerage' : bot.platform}
        </span>
      )}

      {/* P&L + Capital */}
      <div className="mt-3 flex items-baseline gap-2">
        <span className={`text-xl font-bold tabular-nums tracking-tight ${totalPnl > 0 ? 'text-emerald-600' : totalPnl < 0 ? 'text-red-500' : 'text-gray-300'}`}>
          {totalPnl !== 0 ? formatPnl(totalPnl) : '$0.00'}
        </span>
        {bot.starting_capital != null && (
          <span className="text-[11px] text-gray-400 tabular-nums">
            / ${bot.starting_capital.toFixed(0)}
          </span>
        )}
      </div>

      {/* Metrics row */}
      <div className="mt-2.5 flex items-center gap-2 text-[11px] text-gray-400 w-full">
        {bot.open_positions_count > 0 && (
          <span className="tabular-nums">{bot.open_positions_count} pos</span>
        )}
        {bot.open_positions_count > 0 && bot.total_runs > 0 && (
          <span className="text-gray-200">&middot;</span>
        )}
        {bot.total_runs > 0 && (
          <span className="tabular-nums">{bot.total_runs} runs</span>
        )}
        {bot.last_run_at && (
          <>
            <span className="text-gray-200">&middot;</span>
            <span>{formatTimeAgo(bot.last_run_at)}</span>
          </>
        )}
      </div>
    </button>
  );
}

export function CreateBotCard({ onClick, disabled }: { onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="group flex flex-col items-center justify-center p-5 rounded-2xl border-2 border-dashed border-gray-200 hover:border-gray-300 bg-transparent hover:bg-white/80 transition-all duration-300 text-center w-full min-h-[140px] disabled:opacity-40 disabled:pointer-events-none"
    >
      <div className="w-10 h-10 rounded-xl bg-gray-100 group-hover:bg-gray-900 flex items-center justify-center mb-2.5 transition-all duration-300">
        {disabled ? (
          <Loader2 className="w-4.5 h-4.5 text-gray-400 animate-spin" />
        ) : (
          <Plus className="w-4.5 h-4.5 text-gray-400 group-hover:text-white transition-colors duration-300" />
        )}
      </div>
      <span className="text-[13px] font-medium text-gray-400 group-hover:text-gray-600 transition-colors">
        {disabled ? 'Creating...' : 'New bot'}
      </span>
    </button>
  );
}
