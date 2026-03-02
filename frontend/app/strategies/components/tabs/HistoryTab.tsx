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
        <p className="text-gray-500 font-medium">No executions yet</p>
        <p className="text-sm text-gray-400 mt-2">This strategy hasn't run yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          {(['all', 'success', 'failed'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                filter === f
                  ? f === 'success' ? 'bg-green-600 text-white'
                    : f === 'failed' ? 'bg-red-600 text-white'
                    : 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)} ({f === 'all' ? executions.length : executions.filter(e => e.status === f).length})
            </button>
          ))}
        </div>
        <button
          onClick={onRefresh}
          className="px-3 py-1 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-2">
        {filteredExecutions.map(execution => (
          <ExecutionCard
            key={execution.id}
            execution={execution}
            isExpanded={expandedId === execution.id}
            onToggle={() => setExpandedId(expandedId === execution.id ? null : execution.id)}
          />
        ))}
        {filteredExecutions.length === 0 && (
          <div className="text-center py-8 text-gray-500 text-sm">No {filter} executions</div>
        )}
      </div>
    </div>
  );
}

function ExecutionCard({
  execution,
  isExpanded,
  onToggle,
}: {
  execution: StrategyExecution;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const statusColor =
    execution.status === 'success' ? 'bg-green-100 text-green-800 border-green-200' :
    execution.status === 'failed' ? 'bg-red-100 text-red-800 border-red-200' :
    'bg-gray-100 text-gray-600 border-gray-200';

  const summary = execution.summary || `Run ${execution.id.slice(0, 8)}`;
  const duration = execution.duration_ms
    ? `${(execution.duration_ms / 1000).toFixed(1)}s`
    : null;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      <div onClick={onToggle} className="p-4 cursor-pointer hover:bg-gray-50 transition-colors">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusColor}`}>
                {execution.status}
              </span>
              <span className="text-sm text-gray-700 truncate">{summary}</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-400">
              <span>{new Date(execution.started_at).toLocaleString()}</span>
              {duration && <span>{duration}</span>}
              <span className="capitalize">{execution.trigger}</span>
            </div>
          </div>
          <span className="text-gray-400 text-xs ml-2">{isExpanded ? '▼' : '▶'}</span>
        </div>
      </div>

      {isExpanded && (
        <div className="border-t border-gray-200 bg-gray-50 p-4 space-y-3">
          {execution.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="text-xs font-semibold text-red-700 mb-1 uppercase tracking-wide">Error</div>
              <div className="text-sm text-red-800 font-mono">{execution.error}</div>
            </div>
          )}

          {execution.actions && execution.actions.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">
                Actions ({execution.actions.length})
              </div>
              <div className="space-y-2">
                {execution.actions.map((action, i) => (
                  <div key={i} className="bg-white border border-gray-200 rounded p-3 text-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-900 capitalize">{action.type}</span>
                      {action.dry_run && (
                        <span className="text-xs text-yellow-600 bg-yellow-50 px-1.5 py-0.5 rounded">DRY RUN</span>
                      )}
                      <span className="text-xs text-gray-400">{new Date(action.timestamp).toLocaleTimeString()}</span>
                    </div>
                    {action.details && Object.keys(action.details).length > 0 && (
                      <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto mt-1">
                        {JSON.stringify(action.details, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {execution.logs && execution.logs.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Logs</div>
              <div className="bg-gray-900 rounded-lg p-3 font-mono text-xs text-green-400 max-h-48 overflow-y-auto">
                {execution.logs.map((log, i) => (
                  <div key={i} className="mb-0.5">{log}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
