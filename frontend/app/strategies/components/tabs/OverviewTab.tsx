'use client';

import React from 'react';
import type { StrategyDetail } from '@/lib/types';

interface OverviewTabProps {
  strategy: StrategyDetail;
}

export function OverviewTab({ strategy }: OverviewTabProps) {
  const stats = strategy.stats || {};
  const capital = strategy.capital;
  const riskLimits = strategy.risk_limits;

  const successRate = (stats.total_runs || 0) > 0
    ? Math.round(((stats.successful_runs || 0) / (stats.total_runs || 1)) * 100)
    : null;

  return (
    <div className="space-y-6">
      {/* Approval banner */}
      {!strategy.approved && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
          <span className="text-xl">⚠️</span>
          <div>
            <h4 className="font-semibold text-yellow-900">Approval Required</h4>
            <p className="text-sm text-yellow-700 mt-1">
              Review the code and settings, then approve this strategy before enabling it.
            </p>
          </div>
        </div>
      )}

      {/* Thesis */}
      {(strategy.thesis || strategy.description) && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-semibold text-blue-900 mb-1">Thesis</h4>
          <p className="text-sm text-blue-800 italic">
            {strategy.thesis || strategy.description}
          </p>
        </div>
      )}

      {/* Meta */}
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full font-medium">
          {strategy.platform}
        </span>
        {strategy.schedule_description && (
          <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full">
            {strategy.schedule_description}
          </span>
        )}
        <span className={`px-3 py-1 rounded-full font-medium ${
          !strategy.approved
            ? 'bg-yellow-100 text-yellow-800'
            : strategy.enabled
            ? 'bg-green-100 text-green-800'
            : 'bg-gray-100 text-gray-600'
        }`}>
          {!strategy.approved ? 'Needs Approval' : strategy.enabled ? 'Active' : 'Paused'}
        </span>
        <span className={`px-3 py-1 rounded-full font-medium ${
          (strategy.paper_mode ?? true) ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'
        }`}>
          {(strategy.paper_mode ?? true) ? 'Paper' : 'Live'}
        </span>
      </div>

      {/* Run stats */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Execution Stats</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Runs" value={stats.total_runs ?? 0} />
          <StatCard label="Successful" value={stats.successful_runs ?? 0} color="green" />
          <StatCard label="Failed" value={stats.failed_runs ?? 0} color={(stats.failed_runs || 0) > 0 ? 'red' : undefined} />
          <StatCard
            label="Success Rate"
            value={successRate !== null ? `${successRate}%` : '—'}
            color={successRate !== null ? (successRate >= 80 ? 'green' : successRate < 50 ? 'red' : undefined) : undefined}
          />
        </div>
      </div>

      {/* Spend / profit */}
      {((stats.total_spent_usd || 0) > 0 || (stats.total_profit_usd || 0) !== 0) && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Financials</h3>
          <div className="grid grid-cols-2 gap-4">
            <StatCard label="Total Spent" value={`$${(stats.total_spent_usd || 0).toFixed(2)}`} />
            <StatCard
              label="Total Profit"
              value={`$${(stats.total_profit_usd || 0).toFixed(2)}`}
              color={(stats.total_profit_usd || 0) > 0 ? 'green' : (stats.total_profit_usd || 0) < 0 ? 'red' : undefined}
            />
          </div>
        </div>
      )}

      {/* Capital */}
      {capital && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Capital Allocation</h3>
          <div className="grid grid-cols-3 gap-4">
            {capital.total !== undefined && (
              <StatCard label="Total Capital" value={`$${capital.total}`} />
            )}
            {capital.per_trade !== undefined && (
              <StatCard label="Per Trade" value={`$${capital.per_trade}`} />
            )}
            {capital.max_positions !== undefined && (
              <StatCard label="Max Positions" value={capital.max_positions} />
            )}
          </div>
        </div>
      )}

      {/* Risk limits */}
      {riskLimits && (riskLimits.max_order_usd || riskLimits.max_daily_usd) && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Risk Limits</h3>
          <div className="grid grid-cols-2 gap-4">
            {riskLimits.max_order_usd && (
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <div className="text-xs text-blue-600 font-medium uppercase tracking-wide mb-1">Max Per Order</div>
                <div className="text-2xl font-bold text-blue-900">${riskLimits.max_order_usd}</div>
              </div>
            )}
            {riskLimits.max_daily_usd && (
              <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                <div className="text-xs text-purple-600 font-medium uppercase tracking-wide mb-1">Max Per Day</div>
                <div className="text-2xl font-bold text-purple-900">${riskLimits.max_daily_usd}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Last run */}
      {strategy.last_run_summary && (
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Last Run</div>
          <p className="text-sm text-gray-700">{strategy.last_run_summary}</p>
          {strategy.last_run_at && (
            <p className="text-xs text-gray-400 mt-1">{new Date(strategy.last_run_at).toLocaleString()}</p>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: 'green' | 'red';
}) {
  const textColor = color === 'green' ? 'text-green-600' : color === 'red' ? 'text-red-600' : 'text-gray-900';
  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-bold ${textColor}`}>{value}</div>
    </div>
  );
}
