'use client';

import React from 'react';
import type { Strategy } from '@/lib/types';

interface PerformanceTabProps {
  strategy: Strategy;
}

export function PerformanceTab({ strategy }: PerformanceTabProps) {
  const stats = strategy.stats || {};
  
  const totalPnl = stats.total_pnl || 0;
  const winRate = (stats.win_rate || 0) * 100;
  const sharpeRatio = stats.sharpe_ratio || 0;
  const maxDrawdown = Math.abs(stats.max_drawdown || 0) * 100;

  const backtestStats = {
    trades: stats.backtest_trades || 0,
    winRate: (stats.backtest_win_rate || 0) * 100,
    pnl: stats.backtest_pnl || 0,
    status: stats.backtest_trades ? 'Complete' : 'Not Run'
  };

  const paperStats = {
    trades: stats.paper_trades || 0,
    winRate: (stats.paper_win_rate || 0) * 100,
    pnl: stats.paper_pnl || 0,
    status: stats.paper_trades ? 'In Progress' : 'Not Started'
  };

  const liveStats = {
    trades: stats.live_trades || 0,
    winRate: (stats.live_win_rate || 0) * 100,
    pnl: stats.live_pnl || 0,
    status: stats.live_trades ? 'Active' : 'Locked'
  };

  const avgWin = stats.avg_win || 0;
  const avgLoss = stats.avg_loss || 0;
  const largestWin = stats.largest_win || 0;
  const largestLoss = stats.largest_loss || 0;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total P&L"
          value={`$${totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}`}
          color={totalPnl > 0 ? 'green' : totalPnl < 0 ? 'red' : undefined}
          large
        />
        <MetricCard
          label="Win Rate"
          value={`${winRate.toFixed(1)}%`}
          color={winRate > 55 ? 'green' : winRate < 45 ? 'red' : undefined}
          large
        />
        <MetricCard
          label="Sharpe Ratio"
          value={sharpeRatio > 0 ? sharpeRatio.toFixed(2) : 'N/A'}
          large
        />
        <MetricCard
          label="Max Drawdown"
          value={`${maxDrawdown.toFixed(1)}%`}
          color="red"
          large
        />
      </div>

      {/* Mode Breakdown Table */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Performance by Mode</h3>
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  Mode
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  Trades
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  Win Rate
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  P&L
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              <tr className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm">
                  <span className="inline-flex items-center gap-1">
                    <span>🧪</span>
                    <span className="font-medium">Backtest</span>
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">{backtestStats.trades}</td>
                <td className="px-4 py-3 text-sm">{backtestStats.winRate.toFixed(1)}%</td>
                <td className="px-4 py-3 text-sm">
                  <span className={backtestStats.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                    ${backtestStats.pnl >= 0 ? '+' : ''}{backtestStats.pnl.toFixed(2)}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">
                  <span className={backtestStats.trades > 0 ? 'text-green-600' : 'text-gray-500'}>
                    {backtestStats.status === 'Complete' ? '✅' : '⏳'} {backtestStats.status}
                  </span>
                </td>
              </tr>
              <tr className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm">
                  <span className="inline-flex items-center gap-1">
                    <span>📝</span>
                    <span className="font-medium">Paper</span>
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">{paperStats.trades}</td>
                <td className="px-4 py-3 text-sm">{paperStats.winRate.toFixed(1)}%</td>
                <td className="px-4 py-3 text-sm">
                  <span className={paperStats.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                    ${paperStats.pnl >= 0 ? '+' : ''}{paperStats.pnl.toFixed(2)}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">
                  <span className={paperStats.trades > 0 ? 'text-blue-600' : 'text-gray-500'}>
                    {paperStats.status === 'In Progress' ? '⏳' : '⏸️'} {paperStats.status}
                  </span>
                </td>
              </tr>
              <tr className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm">
                  <span className="inline-flex items-center gap-1">
                    <span>🟢</span>
                    <span className="font-medium">Live</span>
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">{liveStats.trades}</td>
                <td className="px-4 py-3 text-sm">
                  {liveStats.trades > 0 ? `${liveStats.winRate.toFixed(1)}%` : '-'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {liveStats.trades > 0 ? (
                    <span className={liveStats.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                      ${liveStats.pnl >= 0 ? '+' : ''}{liveStats.pnl.toFixed(2)}
                    </span>
                  ) : '-'}
                </td>
                <td className="px-4 py-3 text-sm">
                  <span className={liveStats.trades > 0 ? 'text-green-600' : 'text-gray-500'}>
                    {liveStats.status === 'Active' ? '🟢' : '🔒'} {liveStats.status}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Performance Chart Placeholder */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Cumulative P&L Over Time</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <div className="text-gray-400 text-4xl mb-2">📈</div>
          <p className="text-gray-500">Chart visualization coming soon</p>
          <p className="text-xs text-gray-400 mt-1">
            Will show cumulative P&L over time, color-coded by mode
          </p>
        </div>
      </div>

      {/* Trade Statistics */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Trade Statistics</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Avg Win"
            value={`$${avgWin >= 0 ? '+' : ''}${avgWin.toFixed(2)}`}
            color="green"
          />
          <MetricCard
            label="Avg Loss"
            value={`$${avgLoss.toFixed(2)}`}
            color="red"
          />
          <MetricCard
            label="Largest Win"
            value={`$${largestWin >= 0 ? '+' : ''}${largestWin.toFixed(2)}`}
            color="green"
          />
          <MetricCard
            label="Largest Loss"
            value={`$${largestLoss.toFixed(2)}`}
            color="red"
          />
        </div>
      </div>

      {/* Best/Worst Trades */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Notable Trades</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Best Trade */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🏆</span>
              <h4 className="font-semibold text-green-900">Best Trade</h4>
            </div>
            {largestWin > 0 ? (
              <div>
                <div className="text-2xl font-bold text-green-600 mb-1">
                  +${largestWin.toFixed(2)}
                </div>
                <div className="text-sm text-green-700">
                  Market name would appear here
                </div>
              </div>
            ) : (
              <p className="text-sm text-green-700">No profitable trades yet</p>
            )}
          </div>

          {/* Worst Trade */}
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">💀</span>
              <h4 className="font-semibold text-red-900">Worst Trade</h4>
            </div>
            {largestLoss < 0 ? (
              <div>
                <div className="text-2xl font-bold text-red-600 mb-1">
                  ${largestLoss.toFixed(2)}
                </div>
                <div className="text-sm text-red-700">
                  Market name would appear here
                </div>
              </div>
            ) : (
              <p className="text-sm text-red-700">No losing trades yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  color,
  large
}: {
  label: string;
  value: string;
  color?: 'green' | 'red';
  large?: boolean;
}) {
  const textColor = color === 'green'
    ? 'text-green-600'
    : color === 'red'
    ? 'text-red-600'
    : 'text-gray-900';

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`${large ? 'text-3xl' : 'text-2xl'} font-bold ${textColor}`}>{value}</div>
    </div>
  );
}
