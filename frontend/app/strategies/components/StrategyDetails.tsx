'use client';

import React, { useState } from 'react';
import type { StrategyDetail, StrategyExecution } from '@/lib/types';
import { CodeTab } from './tabs/CodeTab';
import { HistoryTab } from './tabs/HistoryTab';
import { SettingsTab } from './tabs/SettingsTab';

interface StrategyDetailsProps {
  strategy: StrategyDetail;
  executions: StrategyExecution[];
  onRefresh: () => void;
  onUpdate: (updates: any) => Promise<void>;
  onApprove: () => Promise<void>;
  onDelete: () => Promise<void>;
  onRun: (dryRun: boolean) => Promise<void>;
}

type TabType = 'code' | 'history' | 'settings';

function StatusDot({ enabled, approved }: { enabled: boolean; approved: boolean }) {
  if (!approved) return <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" />;
  if (enabled) return <span className="w-2 h-2 rounded-full bg-green-500 inline-block animate-pulse" />;
  return <span className="w-2 h-2 rounded-full bg-gray-300 inline-block" />;
}

function StatusLabel({ enabled, approved, paperMode }: { enabled: boolean; approved: boolean; paperMode: boolean }) {
  if (!approved) return <span className="text-yellow-700 font-medium">Needs approval</span>;
  if (enabled) return (
    <span className="text-green-700 font-medium">
      Running {paperMode ? <span className="text-blue-600">(paper)</span> : <span className="text-orange-600">(live)</span>}
    </span>
  );
  return <span className="text-gray-500 font-medium">Paused</span>;
}

export function StrategyDetails({
  strategy,
  executions,
  onRefresh,
  onUpdate,
  onApprove,
  onDelete,
  onRun,
}: StrategyDetailsProps) {
  const [activeTab, setActiveTab] = useState<TabType | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isToggling, setIsToggling] = useState(false);

  const stats = strategy.stats || {};
  const riskLimits = strategy.risk_limits;
  const isPaper = strategy.paper_mode ?? true;
  const lastExecution = executions[0];
  const successRate = (stats.total_runs || 0) > 0
    ? Math.round(((stats.successful_runs || 0) / (stats.total_runs || 1)) * 100)
    : null;

  const handlePreview = async () => {
    setIsRunning(true);
    try { await onRun(true); } finally { setIsRunning(false); }
  };

  const handleApprove = async () => {
    setIsApproving(true);
    try { await onApprove(); } finally { setIsApproving(false); }
  };

  const handleToggle = async () => {
    setIsToggling(true);
    try { await onUpdate({ enabled: !strategy.enabled }); } finally { setIsToggling(false); }
  };

  const tabs: Array<{ id: TabType; label: string; count?: number }> = [
    { id: 'code', label: 'Code' },
    { id: 'history', label: 'History', count: executions.length || undefined },
    { id: 'settings', label: 'Settings' },
  ];

  return (
    <div className="bg-white min-h-full flex flex-col">

      {/* Bot card header */}
      <div className="px-6 pt-6 pb-4 border-b border-gray-100">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <StatusDot enabled={strategy.enabled} approved={strategy.approved} />
              <StatusLabel enabled={strategy.enabled} approved={strategy.approved} paperMode={isPaper} />
              <span className="text-gray-300">·</span>
              <span className="text-sm text-gray-500">{strategy.platform}</span>
              {strategy.schedule_description && (
                <>
                  <span className="text-gray-300">·</span>
                  <span className="text-sm text-gray-500">{strategy.schedule_description}</span>
                </>
              )}
            </div>
            <h2 className="text-xl font-bold text-gray-900 truncate">{strategy.name}</h2>
            {(strategy.thesis || strategy.description) && (
              <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                {strategy.thesis || strategy.description}
              </p>
            )}
          </div>

          {/* Primary actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={handlePreview}
              disabled={isRunning}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {isRunning ? 'Running…' : 'Preview'}
            </button>
            {!strategy.approved ? (
              <button
                onClick={handleApprove}
                disabled={isApproving}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium disabled:opacity-50"
              >
                {isApproving ? 'Approving…' : 'Approve'}
              </button>
            ) : (
              <button
                onClick={handleToggle}
                disabled={isToggling}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
                  strategy.enabled
                    ? 'bg-gray-900 text-white hover:bg-gray-700'
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                {isToggling ? '…' : strategy.enabled ? 'Pause' : 'Enable'}
              </button>
            )}
          </div>
        </div>

        {/* Approval nudge */}
        {!strategy.approved && (
          <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 text-sm text-yellow-800">
            Review the <button onClick={() => setActiveTab('code')} className="underline font-medium">code</button> before approving.
            Once approved you can enable it to run on schedule.
          </div>
        )}
      </div>

      {/* Stats strip */}
      {(stats.total_runs || 0) > 0 && (
        <div className="px-6 py-3 border-b border-gray-100 flex items-center gap-6 text-sm">
          <div className="flex items-center gap-1.5">
            <span className="text-gray-500">Runs</span>
            <span className="font-semibold text-gray-900">{stats.total_runs}</span>
          </div>
          {successRate !== null && (
            <div className="flex items-center gap-1.5">
              <span className="text-gray-500">Success</span>
              <span className={`font-semibold ${successRate >= 80 ? 'text-green-600' : successRate < 50 ? 'text-red-600' : 'text-gray-900'}`}>
                {successRate}%
              </span>
            </div>
          )}
          {(stats.total_spent_usd || 0) > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-gray-500">Spent</span>
              <span className="font-semibold text-gray-900">${(stats.total_spent_usd || 0).toFixed(2)}</span>
            </div>
          )}
          {stats.total_profit_usd !== undefined && stats.total_profit_usd !== 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-gray-500">PnL</span>
              <span className={`font-semibold ${(stats.total_profit_usd || 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                {(stats.total_profit_usd || 0) > 0 ? '+' : ''}${(stats.total_profit_usd || 0).toFixed(2)}
              </span>
            </div>
          )}
          {riskLimits?.max_order_usd && (
            <div className="flex items-center gap-1.5 ml-auto">
              <span className="text-gray-400 text-xs">Max/order</span>
              <span className="text-gray-600 text-xs font-medium">${riskLimits.max_order_usd}</span>
            </div>
          )}
          {riskLimits?.max_daily_usd && (
            <div className="flex items-center gap-1.5">
              <span className="text-gray-400 text-xs">Max/day</span>
              <span className="text-gray-600 text-xs font-medium">${riskLimits.max_daily_usd}</span>
            </div>
          )}
        </div>
      )}

      {/* Last run result */}
      {lastExecution && !activeTab && (
        <div
          onClick={() => setActiveTab('history')}
          className="mx-6 mt-4 rounded-lg border border-gray-200 p-4 cursor-pointer hover:border-gray-300 hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                lastExecution.status === 'success' ? 'bg-green-100 text-green-700' :
                lastExecution.status === 'failed' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-600'
              }`}>
                {lastExecution.status}
              </span>
              <span className="text-xs text-gray-400">{new Date(lastExecution.started_at).toLocaleString()}</span>
              {lastExecution.trigger === 'dry_run' && (
                <span className="text-xs text-blue-500">preview</span>
              )}
            </div>
            <span className="text-xs text-gray-400">Last run →</span>
          </div>
          {lastExecution.summary && (
            <p className="text-sm text-gray-700">{lastExecution.summary}</p>
          )}
          {lastExecution.error && (
            <p className="text-sm text-red-600 font-mono">{lastExecution.error}</p>
          )}
          {lastExecution.logs && lastExecution.logs.length > 0 && (
            <div className="mt-2 bg-gray-900 rounded px-3 py-2 text-xs text-green-400 font-mono max-h-20 overflow-hidden">
              {lastExecution.logs.slice(0, 3).map((log, i) => (
                <div key={i}>{log}</div>
              ))}
              {lastExecution.logs.length > 3 && (
                <div className="text-gray-500">+{lastExecution.logs.length - 3} more…</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* No-runs nudge */}
      {!lastExecution && strategy.approved && !activeTab && (
        <div className="mx-6 mt-4 rounded-lg border border-dashed border-gray-200 p-6 text-center">
          <p className="text-sm text-gray-500">This bot hasn't run yet.</p>
          <button
            onClick={handlePreview}
            disabled={isRunning}
            className="mt-2 text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
          >
            {isRunning ? 'Running preview…' : 'Run a preview →'}
          </button>
        </div>
      )}

      {/* Tab bar */}
      <div className="flex items-center gap-1 px-6 mt-4 border-b border-gray-100">
        <button
          onClick={() => setActiveTab(null)}
          className={`px-3 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === null
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Overview
        </button>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 text-sm font-medium transition-colors border-b-2 -mb-px flex items-center gap-1.5 ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className={`px-1.5 py-0.5 rounded-full text-xs font-semibold ${
                activeTab === tab.id ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'code' && <CodeTab strategy={strategy} />}
        {activeTab === 'history' && <HistoryTab executions={executions} onRefresh={onRefresh} />}
        {activeTab === 'settings' && (
          <SettingsTab strategy={strategy} onUpdate={onUpdate} onApprove={onApprove} onDelete={onDelete} />
        )}
        {activeTab === null && (executions.length === 0 && !strategy.approved) && (
          <div className="text-sm text-gray-400 text-center py-4">
            Approve this strategy to enable scheduled execution.
          </div>
        )}
      </div>
    </div>
  );
}
