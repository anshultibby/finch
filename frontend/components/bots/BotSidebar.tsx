'use client';

import React from 'react';
import type { BotDetail, BotPosition } from '@/lib/types';

interface BotSidebarProps {
  bot: BotDetail;
  onClosePosition?: (positionId: string) => void;
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

export default function BotSidebar({ bot, onClosePosition }: BotSidebarProps) {
  const positions = bot.positions || [];
  const closedPositions = bot.closed_positions || [];
  const files = bot.files || [];
  const stats = bot.stats || {};

  const totalPnl = (bot.total_profit_usd || 0) + (bot.open_unrealized_pnl || 0);

  return (
    <div className="flex flex-col h-full bg-gray-50 border-l border-gray-200 overflow-y-auto">
      <div className="p-4 space-y-5">
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
              <div className="text-xs text-gray-400">P&L</div>
              <div className={`text-sm font-semibold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPnl(totalPnl)}
              </div>
            </div>
            <div className="px-2 py-1.5 rounded bg-white border border-gray-100">
              <div className="text-xs text-gray-400">Ticks</div>
              <div className="text-sm font-semibold text-gray-700">{stats.total_runs ?? 0}</div>
            </div>
          </div>
          {stats.last_run_summary && (
            <div className="mt-2 text-xs text-gray-500">
              <span className="font-medium">Last:</span> {stats.last_run_summary}
            </div>
          )}
        </section>

        {/* Recent Closed */}
        {closedPositions.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Recent Trades
            </h3>
            <div className="space-y-1">
              {closedPositions.slice(0, 5).map((p) => (
                <div key={p.id} className="flex items-center justify-between px-2 py-1.5 text-xs rounded bg-white border border-gray-100">
                  <span className="truncate text-gray-600">{p.market_title || p.market}</span>
                  <span className={(p.realized_pnl_usd ?? 0) >= 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                    {formatPnl(p.realized_pnl_usd ?? 0)}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
