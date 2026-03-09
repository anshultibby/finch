'use client';

import React from 'react';
import type { Bot } from '@/lib/types';
import { Plus, Loader2 } from 'lucide-react';

interface BotCardProps {
  bot: Bot;
  onClick: () => void;
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

export default function BotCard({ bot, onClick }: BotCardProps) {
  const state = getBotState(bot);
  const totalPnl = (bot.total_profit_usd || 0) + (bot.open_unrealized_pnl || 0);
  const isActive = bot.enabled && bot.approved;

  return (
    <button
      onClick={onClick}
      className="group relative flex flex-col items-start p-5 rounded-2xl bg-white border border-gray-100 hover:border-gray-200 shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)] transition-all duration-300 text-left w-full"
    >
      {/* Top row: icon + state */}
      <div className="flex items-start justify-between w-full mb-4">
        <div className="w-11 h-11 rounded-xl bg-gray-50 flex items-center justify-center text-2xl group-hover:scale-105 transition-transform duration-200">
          {bot.icon || '🤖'}
        </div>
        <div className={`flex items-center gap-1.5 ${state.textColor}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${state.dotColor} ${isActive ? 'animate-pulse' : ''}`} />
          <span className="text-[11px] font-medium tracking-wide uppercase">{state.label}</span>
        </div>
      </div>

      {/* Name */}
      <h3 className="text-[15px] font-semibold text-gray-900 truncate w-full leading-tight">
        {bot.name}
      </h3>

      {/* Stats row */}
      <div className="mt-2.5 flex items-center gap-2.5 text-xs">
        {totalPnl !== 0 ? (
          <span className={`font-semibold tabular-nums ${totalPnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {formatPnl(totalPnl)}
          </span>
        ) : (
          <span className="text-gray-300 font-medium">$0.00</span>
        )}
        {bot.open_positions_count > 0 && (
          <>
            <span className="text-gray-200">&middot;</span>
            <span className="text-gray-400">{bot.open_positions_count} pos</span>
          </>
        )}
        {bot.total_runs > 0 && !bot.open_positions_count && (
          <>
            <span className="text-gray-200">&middot;</span>
            <span className="text-gray-400">{bot.total_runs} runs</span>
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
