'use client';

import React from 'react';
import type { Strategy } from '@/lib/types';

interface StrategyCardProps {
  strategy: Strategy;
  isSelected: boolean;
  onSelect: () => void;
  onToggle: () => void;
  onRun: (dryRun: boolean) => void;
  isLoading: boolean;
}

export function StrategyCard({
  strategy,
  isSelected,
  onSelect,
  onToggle,
  onRun,
  isLoading
}: StrategyCardProps) {
  const isLive = strategy.approved && strategy.enabled;
  const needsApproval = !strategy.approved;
  const isPaused = strategy.approved && !strategy.enabled;

  const lastRunText = strategy.last_run_at
    ? relativeTime(strategy.last_run_at)
    : null;

  return (
    <div
      onClick={onSelect}
      className={`rounded-lg border p-3 cursor-pointer transition-all ${
        isSelected
          ? 'border-blue-500 bg-blue-50/50 shadow-sm'
          : 'border-gray-200 bg-white hover:border-gray-300'
      }`}
    >
      {/* Status + name row */}
      <div className="flex items-start gap-2 mb-1.5">
        <div className="mt-1.5 flex-shrink-0">
          {isLive ? (
            <span className="w-2 h-2 rounded-full bg-green-500 block animate-pulse" />
          ) : needsApproval ? (
            <span className="w-2 h-2 rounded-full bg-yellow-400 block" />
          ) : (
            <span className="w-2 h-2 rounded-full bg-gray-300 block" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 leading-tight truncate">{strategy.name}</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            {needsApproval ? 'Needs approval' : isLive ? 'Running' : 'Paused'}
            {strategy.schedule_description ? ` · ${strategy.schedule_description}` : ''}
          </p>
        </div>
      </div>

      {/* Last run / run count */}
      <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
        {strategy.total_runs > 0 ? (
          <span>{strategy.total_runs} run{strategy.total_runs !== 1 ? 's' : ''}{lastRunText ? ` · ${lastRunText}` : ''}</span>
        ) : (
          <span className="text-gray-300">Never run</span>
        )}
        {strategy.last_run_status && (
          <span className={
            strategy.last_run_status === 'success' ? 'text-green-500' :
            strategy.last_run_status === 'failed' ? 'text-red-400' : ''
          }>
            {strategy.last_run_status === 'success' ? '✓' : strategy.last_run_status === 'failed' ? '✗' : ''}
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-1.5" onClick={e => e.stopPropagation()}>
        <button
          onClick={() => onRun(true)}
          disabled={isLoading}
          className="flex-1 px-2 py-1.5 rounded text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors disabled:opacity-50"
        >
          Preview
        </button>
        {strategy.approved && (
          <button
            onClick={onToggle}
            disabled={isLoading}
            className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50 ${
              strategy.enabled
                ? 'bg-gray-900 text-white hover:bg-gray-700'
                : 'bg-green-600 text-white hover:bg-green-700'
            }`}
          >
            {isLoading ? '…' : strategy.enabled ? 'Pause' : 'Enable'}
          </button>
        )}
      </div>
    </div>
  );
}

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
