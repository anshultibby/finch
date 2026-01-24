'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { strategiesApi } from '@/lib/api';
import type { Strategy, StrategyExecution } from '@/lib/types';

export default function StrategiesPage() {
  const { user } = useAuth();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [executions, setExecutions] = useState<StrategyExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (user?.id) {
      loadStrategies();
    }
  }, [user?.id]);

  const loadStrategies = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    try {
      const response = await strategiesApi.listStrategies(user.id);
      if (response.success) {
        setStrategies(response.strategies);
      }
    } catch (error) {
      console.error('Error loading strategies:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadExecutions = async (strategyId: string) => {
    if (!user?.id) return;
    
    try {
      const response = await strategiesApi.getExecutions(user.id, strategyId);
      if (response.success) {
        setExecutions(response.executions);
      }
    } catch (error) {
      console.error('Error loading executions:', error);
    }
  };

  const handleToggleStrategy = async (strategyId: string, currentEnabled: boolean) => {
    if (!user?.id) return;
    
    setActionLoading(strategyId);
    try {
      await strategiesApi.updateStrategy(user.id, strategyId, {
        enabled: !currentEnabled
      });
      await loadStrategies();
    } catch (error) {
      console.error('Error toggling strategy:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRunStrategy = async (strategyId: string, dryRun: boolean) => {
    if (!user?.id) return;
    
    setActionLoading(`run-${strategyId}`);
    try {
      const response = await strategiesApi.runStrategy(user.id, strategyId, dryRun);
      if (response.success) {
        alert(dryRun ? 'Dry run completed!' : 'Strategy executed!');
        await loadStrategies();
        if (selectedStrategy?.id === strategyId) {
          await loadExecutions(strategyId);
        }
      }
    } catch (error) {
      console.error('Error running strategy:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSelectStrategy = async (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    await loadExecutions(strategy.id);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading strategies...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Trading Strategies</h1>
              <p className="mt-1 text-sm text-gray-500">
                Automated bots running on your behalf
              </p>
            </div>
            <button
              onClick={() => window.location.href = '/?mode=create_strategy'}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              ➕ Create New Strategy
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {strategies.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Strategies List */}
            <div className="lg:col-span-1 space-y-4">
              {strategies.map((strategy) => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  isSelected={selectedStrategy?.id === strategy.id}
                  onSelect={() => handleSelectStrategy(strategy)}
                  onToggle={() => handleToggleStrategy(strategy.id, strategy.enabled)}
                  onRun={(dryRun) => handleRunStrategy(strategy.id, dryRun)}
                  isLoading={actionLoading === strategy.id || actionLoading === `run-${strategy.id}`}
                />
              ))}
            </div>

            {/* Strategy Details */}
            <div className="lg:col-span-2">
              {selectedStrategy ? (
                <StrategyDetails
                  strategy={selectedStrategy}
                  executions={executions}
                  onRefresh={() => loadExecutions(selectedStrategy.id)}
                />
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                  <div className="text-gray-400 text-5xl mb-4">📊</div>
                  <p className="text-gray-500">Select a strategy to view details</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Strategy Card Component
// ============================================================================

interface StrategyCardProps {
  strategy: Strategy;
  isSelected: boolean;
  onSelect: () => void;
  onToggle: () => void;
  onRun: (dryRun: boolean) => void;
  isLoading: boolean;
}

function StrategyCard({ strategy, isSelected, onSelect, onToggle, onRun, isLoading }: StrategyCardProps) {
  const getStatusColor = () => {
    if (!strategy.approved) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    if (!strategy.enabled) return 'bg-gray-100 text-gray-600 border-gray-200';
    return 'bg-green-100 text-green-800 border-green-200';
  };

  const getStatusIcon = () => {
    if (!strategy.approved) return '⏸️';
    if (!strategy.enabled) return '💤';
    return '✅';
  };

  const getStatusText = () => {
    if (!strategy.approved) return 'Needs Approval';
    if (!strategy.enabled) return 'Paused';
    return 'Active';
  };

  return (
    <div
      onClick={onSelect}
      className={`bg-white rounded-lg border-2 p-4 cursor-pointer transition-all ${
        isSelected
          ? 'border-blue-500 shadow-lg'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-md'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{strategy.name}</h3>
          <p className="text-xs text-gray-500 mt-1 line-clamp-2">
            {strategy.description}
          </p>
        </div>
        <div className={`ml-2 px-2 py-1 rounded-full text-xs font-medium border flex items-center gap-1 ${getStatusColor()}`}>
          <span>{getStatusIcon()}</span>
          <span>{getStatusText()}</span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-3 text-center">
        <div className="bg-gray-50 rounded p-2">
          <div className="text-lg font-bold text-gray-900">{strategy.stats?.total_runs || 0}</div>
          <div className="text-xs text-gray-500">Runs</div>
        </div>
        <div className="bg-gray-50 rounded p-2">
          <div className="text-lg font-bold text-green-600">{strategy.stats?.successful_runs || 0}</div>
          <div className="text-xs text-gray-500">Success</div>
        </div>
        <div className="bg-gray-50 rounded p-2">
          <div className="text-lg font-bold text-red-600">{strategy.stats?.failed_runs || 0}</div>
          <div className="text-xs text-gray-500">Failed</div>
        </div>
      </div>

      {/* Schedule */}
      {strategy.schedule_description && (
        <div className="text-xs text-gray-500 mb-3 flex items-center gap-1">
          <span>⏱️</span>
          <span>{strategy.schedule_description}</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {strategy.approved && (
          <button
            onClick={(e) => { e.stopPropagation(); onToggle(); }}
            disabled={isLoading}
            className={`flex-1 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              strategy.enabled
                ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                : 'bg-green-600 text-white hover:bg-green-700'
            }`}
          >
            {isLoading ? '...' : strategy.enabled ? 'Pause' : 'Enable'}
          </button>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onRun(true); }}
          disabled={isLoading}
          className="px-3 py-1.5 rounded text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
        >
          Test Run
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Strategy Details Component
// ============================================================================

interface StrategyDetailsProps {
  strategy: Strategy;
  executions: StrategyExecution[];
  onRefresh: () => void;
}

function StrategyDetails({ strategy, executions, onRefresh }: StrategyDetailsProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'logs'>('overview');

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-6 py-3 font-medium text-sm transition-colors ${
              activeTab === 'overview'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-6 py-3 font-medium text-sm transition-colors ${
              activeTab === 'history'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Execution History ({executions.length})
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-6 py-3 font-medium text-sm transition-colors ${
              activeTab === 'logs'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Live Activity
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'overview' && <OverviewTab strategy={strategy} />}
        {activeTab === 'history' && <HistoryTab executions={executions} onRefresh={onRefresh} />}
        {activeTab === 'logs' && <LogsTab strategy={strategy} executions={executions} />}
      </div>
    </div>
  );
}

// ============================================================================
// Overview Tab
// ============================================================================

function OverviewTab({ strategy }: { strategy: Strategy }) {
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
                This strategy needs your approval before it can trade with real money.
                Review the code and approve it in the chat.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Description */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-2">Description</h3>
        <p className="text-gray-600">{strategy.description}</p>
      </div>

      {/* Schedule */}
      {strategy.schedule_description && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-2">Schedule</h3>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">⏱️</span>
              <span className="text-gray-900">{strategy.schedule_description}</span>
            </div>
          </div>
        </div>
      )}

      {/* Risk Limits */}
      {strategy.risk_limits && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-2">Risk Limits</h3>
          <div className="grid grid-cols-2 gap-4">
            {strategy.risk_limits.max_order_usd && (
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="text-sm text-blue-600 font-medium">Max Per Order</div>
                <div className="text-2xl font-bold text-blue-900 mt-1">
                  ${strategy.risk_limits.max_order_usd}
                </div>
              </div>
            )}
            {strategy.risk_limits.max_daily_usd && (
              <div className="bg-purple-50 rounded-lg p-4">
                <div className="text-sm text-purple-600 font-medium">Max Per Day</div>
                <div className="text-2xl font-bold text-purple-900 mt-1">
                  ${strategy.risk_limits.max_daily_usd}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Performance Stats */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-2">Performance</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Runs" value={strategy.stats?.total_runs || 0} />
          <StatCard label="Success Rate" value={`${calculateSuccessRate(strategy)}%`} color="green" />
          <StatCard label="Total Spent" value={`$${(strategy.stats?.total_spent_usd || 0).toFixed(2)}`} />
          <StatCard label="Profit" value={`$${(strategy.stats?.total_profit_usd || 0).toFixed(2)}`} color={strategy.stats?.total_profit_usd && strategy.stats.total_profit_usd > 0 ? 'green' : 'red'} />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// History Tab
// ============================================================================

function HistoryTab({ executions, onRefresh }: { executions: StrategyExecution[]; onRefresh: () => void }) {
  if (executions.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-5xl mb-4">📋</div>
        <p className="text-gray-500">No executions yet</p>
        <p className="text-sm text-gray-400 mt-2">This strategy hasn't run yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-gray-900">Recent Executions</h3>
        <button
          onClick={onRefresh}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          🔄 Refresh
        </button>
      </div>

      <div className="space-y-3">
        {executions.map((execution) => (
          <ExecutionCard key={execution.id} execution={execution} />
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Logs Tab (Live Activity)
// ============================================================================

function LogsTab({ strategy, executions }: { strategy: Strategy; executions: StrategyExecution[] }) {
  const latestExecution = executions[0];

  if (!latestExecution) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-5xl mb-4">💤</div>
        <p className="text-gray-500">No activity yet</p>
        <p className="text-sm text-gray-400 mt-2">Waiting for first execution</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Live Status */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 border border-blue-200">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          <div>
            <div className="font-semibold text-gray-900">
              {strategy.enabled ? 'Bot is Active' : 'Bot is Paused'}
            </div>
            <div className="text-sm text-gray-600">
              {latestExecution.data?.summary || 'Last run: ' + new Date(latestExecution.started_at).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Logs */}
      <div>
        <h4 className="font-semibold text-gray-900 mb-2">Latest Execution Logs</h4>
        <div className="bg-gray-900 rounded-lg p-4 font-mono text-xs text-green-400 max-h-96 overflow-y-auto">
          {latestExecution.data?.logs && latestExecution.data.logs.length > 0 ? (
            latestExecution.data.logs.map((log: string, i: number) => (
              <div key={i} className="mb-1">{log}</div>
            ))
          ) : (
            <div className="text-gray-500">No logs available</div>
          )}
        </div>
      </div>

      {/* Actions Taken */}
      {latestExecution.data?.actions && latestExecution.data.actions.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 mb-2">Actions Taken</h4>
          <div className="space-y-2">
            {latestExecution.data.actions.map((action: any, i: number) => (
              <div key={i} className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-blue-900">{action.type}</div>
                  <div className="text-sm text-blue-600">
                    {new Date(action.timestamp).toLocaleTimeString()}
                  </div>
                </div>
                <div className="text-sm text-blue-700 mt-1">
                  {JSON.stringify(action.details, null, 2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Execution Card
// ============================================================================

function ExecutionCard({ execution }: { execution: StrategyExecution }) {
  const [expanded, setExpanded] = useState(false);

  const getStatusColor = () => {
    if (execution.status === 'success') return 'bg-green-100 text-green-800 border-green-200';
    if (execution.status === 'failed') return 'bg-red-100 text-red-800 border-red-200';
    return 'bg-gray-100 text-gray-600 border-gray-200';
  };

  const getStatusIcon = () => {
    if (execution.status === 'success') return '✅';
    if (execution.status === 'failed') return '❌';
    return '⏳';
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div
        onClick={() => setExpanded(!expanded)}
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1">
            <span className="text-xl">{getStatusIcon()}</span>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-gray-900">
                {execution.data?.summary || 'Execution ' + execution.id.slice(0, 8)}
              </div>
              <div className="text-sm text-gray-500 mt-1">
                {new Date(execution.started_at).toLocaleString()}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor()}`}>
              {execution.status}
            </div>
            <div className="text-gray-400">{expanded ? '▼' : '▶'}</div>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-3">
          {execution.data?.error && (
            <div className="bg-red-50 border border-red-200 rounded p-3 text-red-900 text-sm">
              {execution.data.error}
            </div>
          )}

          {execution.data?.logs && execution.data.logs.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-700 mb-2">Logs:</div>
              <div className="bg-gray-900 rounded p-3 font-mono text-xs text-green-400 max-h-48 overflow-y-auto">
                {execution.data.logs.map((log: string, i: number) => (
                  <div key={i}>{log}</div>
                ))}
              </div>
            </div>
          )}

          {execution.data?.actions && execution.data.actions.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-700 mb-2">
                Actions: {execution.data.actions.length}
              </div>
              <div className="space-y-1">
                {execution.data.actions.map((action: any, i: number) => (
                  <div key={i} className="text-xs bg-white rounded p-2 border border-gray-200">
                    <span className="font-medium">{action.type}</span>
                    {action.dry_run && <span className="ml-2 text-yellow-600">(DRY RUN)</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Helper Components
// ============================================================================

function StatCard({ label, value, color }: { label: string; value: string | number; color?: 'green' | 'red' }) {
  const textColor = color === 'green' ? 'text-green-600' : color === 'red' ? 'text-red-600' : 'text-gray-900';
  
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${textColor}`}>{value}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="bg-white rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
      <div className="text-gray-400 text-6xl mb-4">🤖</div>
      <h3 className="text-xl font-semibold text-gray-900 mb-2">No Strategies Yet</h3>
      <p className="text-gray-500 mb-6">
        Create your first automated trading bot with AI assistance
      </p>
      <button
        onClick={() => window.location.href = '/?mode=create_strategy'}
        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
      >
        Create Your First Strategy
      </button>
    </div>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

function calculateSuccessRate(strategy: Strategy): number {
  const total = strategy.stats?.total_runs || 0;
  const successful = strategy.stats?.successful_runs || 0;
  if (total === 0) return 0;
  return Math.round((successful / total) * 100);
}
