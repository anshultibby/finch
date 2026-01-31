'use client';

import React, { useState } from 'react';
import type { StrategyExecution } from '@/lib/types';

interface HistoryTabProps {
  executions: StrategyExecution[];
  onRefresh: () => void;
}

export function HistoryTab({ executions, onRefresh }: HistoryTabProps) {
  const [filter, setFilter] = useState<'all' | 'success' | 'failed'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filteredExecutions = executions.filter(ex => {
    if (filter === 'all') return true;
    return ex.status === filter;
  });

  if (executions.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-5xl mb-4">📋</div>
        <p className="text-gray-500 font-medium">No executions yet</p>
        <p className="text-sm text-gray-400 mt-2">This strategy hasn't run yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Filter and Refresh */}
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              filter === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            All ({executions.length})
          </button>
          <button
            onClick={() => setFilter('success')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              filter === 'success'
                ? 'bg-green-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Success ({executions.filter(e => e.status === 'success').length})
          </button>
          <button
            onClick={() => setFilter('failed')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              filter === 'failed'
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Failed ({executions.filter(e => e.status === 'failed').length})
          </button>
        </div>
        <button
          onClick={onRefresh}
          className="px-3 py-1 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 transition-colors"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        {filteredExecutions.map((execution) => (
          <ExecutionCard
            key={execution.id}
            execution={execution}
            isExpanded={expandedId === execution.id}
            onToggle={() => setExpandedId(expandedId === execution.id ? null : execution.id)}
          />
        ))}
      </div>

      {filteredExecutions.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No {filter} executions found
        </div>
      )}
    </div>
  );
}

interface ExecutionCardProps {
  execution: StrategyExecution;
  isExpanded: boolean;
  onToggle: () => void;
}

function ExecutionCard({ execution, isExpanded, onToggle }: ExecutionCardProps) {
  const getStatusIcon = () => {
    if (execution.status === 'success') return '✅';
    if (execution.status === 'failed') return '❌';
    return '⏳';
  };

  const getStatusColor = () => {
    if (execution.status === 'success') return 'bg-green-100 text-green-800 border-green-200';
    if (execution.status === 'failed') return 'bg-red-100 text-red-800 border-red-200';
    return 'bg-gray-100 text-gray-600 border-gray-200';
  };

  const getModeIcon = () => {
    const mode = execution.data?.mode || 'paper';
    if (mode === 'live') return '🟢';
    if (mode === 'paper') return '📝';
    if (mode === 'backtest') return '🧪';
    return '📝';
  };

  const duration = execution.data?.duration_ms 
    ? `${(execution.data.duration_ms / 1000).toFixed(1)}s`
    : 'N/A';

  const summary = execution.data?.summary || execution.summary || `Execution ${execution.id.slice(0, 8)}`;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      {/* Header */}
      <div
        onClick={onToggle}
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <span className="text-2xl">{getStatusIcon()}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-gray-900">{summary}</span>
                <span className="text-lg">{getModeIcon()}</span>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <span>{new Date(execution.started_at).toLocaleString()}</span>
                <span>Duration: {duration}</span>
                {execution.data?.trigger && (
                  <span className="capitalize">Trigger: {execution.data.trigger}</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor()}`}>
              {execution.status}
            </div>
            <div className="text-gray-400 text-sm">{isExpanded ? '▼' : '▶'}</div>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-gray-200 bg-gray-50 p-4 space-y-4">
          {/* Error */}
          {execution.data?.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <span className="text-red-600">❌</span>
                <div>
                  <div className="font-semibold text-red-900 text-sm mb-1">Error</div>
                  <div className="text-sm text-red-800 font-mono">{execution.data.error}</div>
                </div>
              </div>
            </div>
          )}

          {/* Signals */}
          {execution.data?.signals && execution.data.signals.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                Signals Generated ({execution.data.signals.length})
              </div>
              <div className="space-y-2">
                {execution.data.signals.map((signal: any, i: number) => (
                  <div key={i} className="bg-blue-50 border border-blue-200 rounded p-3 text-sm">
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-medium text-blue-900">{signal.market_name}</span>
                      <span className="text-xs text-blue-600">
                        Confidence: {((signal.confidence || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="text-xs text-blue-700">{signal.reason}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          {execution.data?.actions && execution.data.actions.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                Actions Taken ({execution.data.actions.length})
              </div>
              <div className="space-y-2">
                {execution.data.actions.map((action: any, i: number) => (
                  <div key={i} className="bg-white border border-gray-200 rounded p-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium text-gray-900 text-sm capitalize">
                          {action.type}
                          {action.dry_run && (
                            <span className="ml-2 text-xs text-yellow-600 font-normal">(DRY RUN)</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {new Date(action.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                    {action.details && (
                      <div className="mt-2 text-xs text-gray-600 font-mono bg-gray-50 p-2 rounded">
                        {JSON.stringify(action.details, null, 2)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Logs */}
          {execution.data?.logs && execution.data.logs.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                Execution Logs
              </div>
              <div className="bg-gray-900 rounded-lg p-3 font-mono text-xs text-green-400 max-h-64 overflow-y-auto">
                {execution.data.logs.map((log: string, i: number) => (
                  <div key={i} className="mb-1">{log}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
