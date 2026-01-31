'use client';

import React from 'react';
import type { Strategy } from '@/lib/types';
import { CapitalMeter } from '../CapitalMeter';
import { TrackRecordProgress } from '../TrackRecordProgress';

interface OverviewTabProps {
  strategy: Strategy;
  onGraduate?: () => void;
}

export function OverviewTab({ strategy, onGraduate }: OverviewTabProps) {
  const config = strategy.config || {};
  const stats = strategy.stats || {};
  const capital = config.capital || {};
  const mode = stats.mode || 'paper';

  return (
    <div className="space-y-6">
      {/* Status Banner */}
      {!strategy.approved && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <h4 className="font-semibold text-yellow-900">Approval Required</h4>
              <p className="text-sm text-yellow-700 mt-1">
                This strategy needs your approval before it can be enabled.
                Review the code and settings, then approve it in the Settings tab.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Thesis */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <span className="text-xl">💡</span>
          <div>
            <h4 className="font-semibold text-blue-900 mb-1">Investment Thesis</h4>
            <p className="text-sm text-blue-800 italic">
              {config.thesis || strategy.description}
            </p>
          </div>
        </div>
      </div>

      {/* Platform Badge */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 uppercase tracking-wide">Platform:</span>
        <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
          {config.platform || 'Unknown'}
        </span>
        <span className="text-xs text-gray-500 uppercase tracking-wide ml-4">Mode:</span>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          mode === 'live' ? 'bg-green-100 text-green-800' :
          mode === 'paper' ? 'bg-blue-100 text-blue-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          {mode.charAt(0).toUpperCase() + mode.slice(1)}
        </span>
      </div>

      {/* Capital Allocation */}
      <CapitalMeter
        totalCapital={capital.total_capital || 0}
        deployed={capital.deployed || 0}
        perTrade={capital.capital_per_trade || 0}
        currentPositions={stats.current_positions || 0}
        maxPositions={capital.max_positions || 5}
      />

      {/* Entry/Exit Conditions */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Entry & Exit Conditions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Entry */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">🚪</span>
              <h4 className="font-semibold text-green-900">Entry</h4>
            </div>
            <p className="text-sm text-green-800">
              {config.entry_description || 'No entry description provided'}
            </p>
          </div>

          {/* Exit */}
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">🚪</span>
              <h4 className="font-semibold text-red-900">Exit</h4>
            </div>
            <p className="text-sm text-red-800">
              {config.exit_description || 'No exit description provided'}
            </p>
          </div>
        </div>
      </div>

      {/* Track Record Progress (only show in paper mode) */}
      {mode === 'paper' && (
        <TrackRecordProgress
          mode={mode}
          paperTrades={stats.paper_trades || 0}
          paperWinRate={stats.paper_win_rate || 0}
          paperPnl={stats.paper_pnl || 0}
          maxDrawdown={stats.max_drawdown || 0}
          onGraduate={onGraduate}
        />
      )}

      {/* Performance Stats */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Performance Summary</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Trades"
            value={stats.total_trades || 0}
          />
          <StatCard
            label="Win Rate"
            value={`${((stats.win_rate || 0) * 100).toFixed(1)}%`}
            color={(stats.win_rate || 0) > 0.55 ? 'green' : (stats.win_rate || 0) < 0.45 ? 'red' : undefined}
          />
          <StatCard
            label="Total P&L"
            value={`$${(stats.total_pnl || 0).toFixed(2)}`}
            color={(stats.total_pnl || 0) > 0 ? 'green' : (stats.total_pnl || 0) < 0 ? 'red' : undefined}
          />
          <StatCard
            label="Max Drawdown"
            value={`${(Math.abs(stats.max_drawdown || 0) * 100).toFixed(1)}%`}
            color="red"
          />
        </div>
      </div>

      {/* Risk Limits */}
      {config.risk_limits && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Risk Limits</h3>
          <div className="grid grid-cols-2 gap-4">
            {config.risk_limits.max_order_usd && (
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <div className="text-xs text-blue-600 font-medium uppercase tracking-wide mb-1">
                  Max Per Order
                </div>
                <div className="text-2xl font-bold text-blue-900">
                  ${config.risk_limits.max_order_usd}
                </div>
              </div>
            )}
            {config.risk_limits.max_daily_usd && (
              <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                <div className="text-xs text-purple-600 font-medium uppercase tracking-wide mb-1">
                  Max Per Day
                </div>
                <div className="text-2xl font-bold text-purple-900">
                  ${config.risk_limits.max_daily_usd}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ 
  label, 
  value, 
  color 
}: { 
  label: string; 
  value: string | number; 
  color?: 'green' | 'red' 
}) {
  const textColor = color === 'green' 
    ? 'text-green-600' 
    : color === 'red' 
    ? 'text-red-600' 
    : 'text-gray-900';
  
  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-bold ${textColor}`}>{value}</div>
    </div>
  );
}
