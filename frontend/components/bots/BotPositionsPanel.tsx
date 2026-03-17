'use client';

import React from 'react';
import type { BotDetail, BotPosition } from '@/lib/types';

interface BotPositionsPanelProps {
  bot: BotDetail;
  userId: string;
  onBack: () => void;
  onClosePosition?: (positionId: string) => void;
}

function formatPnl(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function PositionRow({ position, onClose }: { position: BotPosition; onClose?: () => void }) {
  const pnl = position.unrealized_pnl_usd ?? position.realized_pnl_usd ?? 0;
  const isOpen = position.status === 'open';
  const pnlColor = pnl > 0 ? 'text-emerald-600' : pnl < 0 ? 'text-red-500' : 'text-gray-400';

  return (
    <div className="px-6 py-3 border-b border-gray-100 last:border-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium text-gray-800 leading-snug">
            {position.market_title || position.market}
          </div>
          <div className="flex items-center gap-2 mt-1 text-[11px] text-gray-400">
            <span className={`font-semibold uppercase text-[10px] px-1.5 py-0.5 rounded ${position.side === 'yes' ? 'bg-blue-50 text-blue-600' : 'bg-orange-50 text-orange-600'}`}>
              {position.side}
            </span>
            <span>{position.entry_price}¢{position.current_price != null ? ` → ${position.current_price}¢` : ''}</span>
            <span>×{position.quantity}</span>
            {!isOpen && position.close_reason && (
              <span className="text-gray-300 italic">{position.close_reason}</span>
            )}
          </div>
          {position.monitor_note && (
            <div className="mt-1 text-[11px] text-gray-400 italic">{position.monitor_note}</div>
          )}
        </div>
        <div className="text-right shrink-0">
          <div className={`text-sm font-bold tabular-nums ${pnlColor}`}>
            {formatPnl(pnl)}
          </div>
          {isOpen && onClose && (
            <button
              onClick={onClose}
              className="mt-1 text-[10px] font-medium text-red-400 hover:text-red-600 transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function BotPositionsPanel({ bot, onBack, onClosePosition }: BotPositionsPanelProps) {
  const positions = bot.positions || [];
  const closedPositions = bot.closed_positions || [];

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
          <h2 className="text-sm font-semibold text-gray-900">Positions</h2>
          <p className="text-[11px] text-gray-400">
            {positions.length} open · {closedPositions.length} closed
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Performance summary */}
        {(() => {
          const stats = bot.stats || {};
          const totalPnl = (bot.total_profit_usd || 0) + (bot.open_unrealized_pnl || 0);
          const pnlColor = totalPnl > 0 ? 'text-emerald-600' : totalPnl < 0 ? 'text-red-500' : 'text-gray-400';
          return (
            <div className="px-6 py-4 border-b border-gray-100 grid grid-cols-3 gap-4">
              <div>
                <div className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">P&L</div>
                <div className={`text-base font-bold tabular-nums ${pnlColor}`}>
                  {totalPnl >= 0 ? '+' : ''}${Math.abs(totalPnl).toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">Runs</div>
                <div className="text-base font-bold text-gray-700">{stats.total_runs ?? 0}</div>
              </div>
              <div>
                <div className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">Open</div>
                <div className="text-base font-bold text-gray-700">{positions.length}</div>
              </div>
              {stats.last_run_summary && (
                <div className="col-span-3 pt-1 border-t border-gray-100 text-[11px] text-gray-500 leading-relaxed">
                  <span className="font-medium text-gray-600">Last run:</span> {stats.last_run_summary}
                </div>
              )}
            </div>
          );
        })()}
        {positions.length === 0 && closedPositions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <span className="text-3xl mb-3">📊</span>
            <p className="text-sm font-medium text-gray-500">No positions yet</p>
            <p className="text-xs text-gray-400 mt-1 max-w-xs leading-relaxed">
              Positions will appear here after the bot places trades.
            </p>
          </div>
        ) : (
          <>
            {positions.length > 0 && (
              <div>
                <div className="px-6 pt-4 pb-2">
                  <h3 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Open ({positions.length})</h3>
                </div>
                {positions.map((p) => (
                  <PositionRow
                    key={p.id}
                    position={p}
                    onClose={onClosePosition ? () => onClosePosition(p.id) : undefined}
                  />
                ))}
              </div>
            )}
            {closedPositions.length > 0 && (
              <div>
                <div className="px-6 pt-4 pb-2">
                  <h3 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Closed ({closedPositions.length})</h3>
                </div>
                {closedPositions.map((p) => (
                  <PositionRow key={p.id} position={p} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
