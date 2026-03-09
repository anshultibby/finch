'use client';

import React, { useState } from 'react';
import type { Bot } from '@/lib/types';
import { Plus, Loader2, MoreHorizontal, Trash2 } from 'lucide-react';

interface BotCardProps {
  bot: Bot;
  onClick: () => void;
  onDelete?: (id: string) => void;
}

function getBotState(bot: Bot): { label: string; dotColor: string; textColor: string } {
  if (!bot.enabled) return { label: 'Paused', dotColor: 'bg-gray-300', textColor: 'text-gray-400' };
  if (bot.open_positions_count > 0) {
    return { label: 'Holding', dotColor: 'bg-blue-400', textColor: 'text-blue-500' };
  }
  return { label: 'Seeking', dotColor: 'bg-emerald-400', textColor: 'text-emerald-500' };
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
  const state = getBotState(bot);
  const totalPnl = (bot.total_profit_usd || 0) + (bot.open_unrealized_pnl || 0);
  const isActive = bot.enabled && bot.approved;

  return (
    <button
      onClick={onClick}
      className="group relative flex flex-col items-start p-5 rounded-2xl bg-white border border-gray-100 hover:border-gray-200 shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)] transition-all duration-300 text-left w-full"
    >
      {/* Top row: icon + state + menu */}
      <div className="flex items-start justify-between w-full mb-3">
        <div className="w-11 h-11 rounded-xl bg-gray-50 flex items-center justify-center text-2xl group-hover:scale-105 transition-transform duration-200">
          {bot.icon || '🤖'}
        </div>
        <div className="flex items-center gap-2">
          <div className={`flex items-center gap-1.5 ${state.textColor}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${state.dotColor} ${isActive ? 'animate-pulse' : ''}`} />
            <span className="text-[11px] font-medium tracking-wide uppercase">{state.label}</span>
          </div>
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

      {/* P&L */}
      <div className="mt-2 flex items-baseline gap-2">
        <span className={`text-lg font-bold tabular-nums tracking-tight ${totalPnl > 0 ? 'text-emerald-600' : totalPnl < 0 ? 'text-red-500' : 'text-gray-300'}`}>
          {totalPnl !== 0 ? formatPnl(totalPnl) : '$0.00'}
        </span>
        {bot.capital_balance != null && (
          <span className="text-[11px] text-gray-400 tabular-nums">
            / ${bot.capital_balance.toFixed(0)}
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
      className="group flex flex-col items-center justify-center p-5 rounded-2xl border border-dashed border-gray-200 hover:border-gray-300 bg-transparent hover:bg-white/60 transition-all duration-300 text-center w-full min-h-[140px] disabled:opacity-40 disabled:pointer-events-none"
    >
      <div className="w-10 h-10 rounded-xl bg-gray-100 group-hover:bg-gray-200/80 flex items-center justify-center mb-2.5 transition-colors duration-200">
        {disabled ? (
          <Loader2 className="w-4.5 h-4.5 text-gray-400 animate-spin" />
        ) : (
          <Plus className="w-4.5 h-4.5 text-gray-400 group-hover:text-gray-500 transition-colors" />
        )}
      </div>
      <span className="text-[13px] font-medium text-gray-400 group-hover:text-gray-500 transition-colors">
        {disabled ? 'Creating...' : 'New bot'}
      </span>
    </button>
  );
}
