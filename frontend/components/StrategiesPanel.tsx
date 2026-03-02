'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { strategiesApi } from '@/lib/api';
import type { Strategy, StrategyDetail, StrategyExecution } from '@/lib/types';
import { StrategyCard } from '@/app/strategies/components/StrategyCard';
import { StrategyDetails } from '@/app/strategies/components/StrategyDetails';
import { EmptyState } from '@/app/strategies/components/EmptyState';

type SortBy = 'name' | 'runs' | 'created';
type FilterStatus = 'all' | 'active' | 'paused' | 'needs_approval';

export default function StrategiesPanel() {
  const { user } = useAuth();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedDetail, setSelectedDetail] = useState<StrategyDetail | null>(null);
  const [executions, setExecutions] = useState<StrategyExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortBy>('created');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');

  useEffect(() => {
    if (user?.id) loadStrategies();
  }, [user?.id]);

  useEffect(() => {
    const handleRefresh = () => { if (user?.id) loadStrategies(); };
    window.addEventListener('strategies:refresh', handleRefresh);
    return () => window.removeEventListener('strategies:refresh', handleRefresh);
  }, [user?.id]);

  const loadStrategies = async () => {
    if (!user?.id) return;
    setLoading(true);
    try {
      const data = await strategiesApi.listStrategies(user.id);
      const list: Strategy[] = Array.isArray(data) ? data : [];
      setStrategies(list);
      // Auto-select first if none selected
      if (!selectedDetail && list.length > 0) {
        await loadDetail(list[0].id);
      }
    } catch (err) {
      console.error('Error loading strategies:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (strategyId: string) => {
    if (!user?.id) return;
    try {
      const detail = await strategiesApi.getStrategy(user.id, strategyId);
      setSelectedDetail(detail);
      await loadExecutions(strategyId);
    } catch (err) {
      console.error('Error loading strategy detail:', err);
    }
  };

  const loadExecutions = async (strategyId: string) => {
    if (!user?.id) return;
    try {
      const data = await strategiesApi.getExecutions(user.id, strategyId);
      setExecutions(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectStrategy = async (strategyId: string) => {
    await loadDetail(strategyId);
  };

  const handleToggleStrategy = async (strategyId: string, currentEnabled: boolean) => {
    if (!user?.id) return;
    setActionLoading(strategyId);
    try {
      await strategiesApi.updateStrategy(user.id, strategyId, { enabled: !currentEnabled });
      await loadStrategies();
      if (selectedDetail?.id === strategyId) await loadDetail(strategyId);
    } catch (err) { console.error(err); }
    finally { setActionLoading(null); }
  };

  const handleRunStrategy = async (strategyId: string, dryRun: boolean) => {
    if (!user?.id) return;
    setActionLoading(`run-${strategyId}`);
    try {
      await strategiesApi.runStrategy(user.id, strategyId, dryRun);
      await loadStrategies();
      if (selectedDetail?.id === strategyId) await loadDetail(strategyId);
    } catch (err) { console.error(err); }
    finally { setActionLoading(null); }
  };

  const handleUpdateStrategy = async (strategyId: string, updates: any) => {
    if (!user?.id) return;
    try {
      await strategiesApi.updateStrategy(user.id, strategyId, updates);
      await loadStrategies();
      if (selectedDetail?.id === strategyId) await loadDetail(strategyId);
    } catch (err) { console.error(err); }
  };

  const handleApproveStrategy = async (strategyId: string) => {
    if (!user?.id) return;
    try {
      await strategiesApi.approveStrategy(user.id, strategyId);
      await loadStrategies();
      await loadDetail(strategyId);
    } catch (err) { console.error(err); }
  };

  const handleDeleteStrategy = async (strategyId: string) => {
    if (!user?.id) return;
    try {
      await strategiesApi.deleteStrategy(user.id, strategyId);
      if (selectedDetail?.id === strategyId) {
        setSelectedDetail(null);
        setExecutions([]);
      }
      await loadStrategies();
    } catch (err) { console.error(err); }
  };

  const filtered = useMemo(() => {
    let result = [...strategies];
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(s =>
        s.name.toLowerCase().includes(q) ||
        s.description?.toLowerCase().includes(q)
      );
    }
    if (filterStatus !== 'all') {
      result = result.filter(s => {
        if (filterStatus === 'active') return s.enabled && s.approved;
        if (filterStatus === 'paused') return !s.enabled && s.approved;
        if (filterStatus === 'needs_approval') return !s.approved;
        return true;
      });
    }
    result.sort((a, b) => {
      switch (sortBy) {
        case 'name': return a.name.localeCompare(b.name);
        case 'runs': return b.total_runs - a.total_runs;
        case 'created': return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        default: return 0;
      }
    });
    return result;
  }, [strategies, searchQuery, sortBy, filterStatus]);

  const activeCount = strategies.filter(s => s.enabled && s.approved).length;

  if (loading && strategies.length === 0) {
    return (
      <div className="h-full bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-3">🤖</div>
          <div className="text-gray-500 text-sm">Loading strategies…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-50 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200 bg-white flex-shrink-0">
        <h2 className="text-base font-semibold text-gray-900">Trading Bots</h2>
        {activeCount > 0 && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            {activeCount} active
          </span>
        )}
        <button
          onClick={() => {
            window.dispatchEvent(new CustomEvent('panel:switch-to-chat'));
            window.dispatchEvent(new CustomEvent('chat:prompt', { detail: 'Build me a new trading strategy bot.' }));
          }}
          className="ml-auto px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors"
        >
          + New Bot
        </button>
      </div>

      {strategies.length === 0 ? (
        <div className="flex-1 overflow-y-auto p-6">
          <EmptyState onPromptSelect={(prompt) => {
            window.dispatchEvent(new CustomEvent('panel:switch-to-chat'));
            window.dispatchEvent(new CustomEvent('chat:prompt', { detail: prompt }));
          }} />
        </div>
      ) : (
        <div className="flex-1 overflow-hidden flex">
          {/* Left: strategy list */}
          <div className="w-64 border-r border-gray-200 bg-white flex flex-col flex-shrink-0">
            <div className="p-3 space-y-2 border-b border-gray-100">
              <input
                type="text"
                placeholder="Search…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex gap-2">
                <select
                  value={filterStatus}
                  onChange={e => setFilterStatus(e.target.value as FilterStatus)}
                  className="flex-1 text-xs border border-gray-200 rounded px-1.5 py-1 bg-white"
                >
                  <option value="all">All</option>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                  <option value="needs_approval">Needs approval</option>
                </select>
                <select
                  value={sortBy}
                  onChange={e => setSortBy(e.target.value as SortBy)}
                  className="flex-1 text-xs border border-gray-200 rounded px-1.5 py-1 bg-white"
                >
                  <option value="created">Newest</option>
                  <option value="name">Name</option>
                  <option value="runs">Most runs</option>
                </select>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {filtered.length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">No strategies match</div>
              ) : filtered.map(strategy => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  isSelected={selectedDetail?.id === strategy.id}
                  onSelect={() => handleSelectStrategy(strategy.id)}
                  onToggle={() => handleToggleStrategy(strategy.id, strategy.enabled)}
                  onRun={dryRun => handleRunStrategy(strategy.id, dryRun)}
                  isLoading={actionLoading === strategy.id || actionLoading === `run-${strategy.id}`}
                />
              ))}
            </div>
          </div>

          {/* Right: details */}
          <div className="flex-1 overflow-y-auto">
            {selectedDetail ? (
              <StrategyDetails
                strategy={selectedDetail}
                executions={executions}
                onRefresh={() => loadExecutions(selectedDetail.id)}
                onUpdate={updates => handleUpdateStrategy(selectedDetail.id, updates)}
                onApprove={() => handleApproveStrategy(selectedDetail.id)}
                onDelete={() => handleDeleteStrategy(selectedDetail.id)}
                onRun={dryRun => handleRunStrategy(selectedDetail.id, dryRun)}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-center">
                <div>
                  <div className="text-5xl mb-3 text-gray-200">📊</div>
                  <p className="text-gray-400 font-medium">Select a strategy</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
