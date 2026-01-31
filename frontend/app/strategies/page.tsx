'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import AuthGate from '@/components/PasswordGate';
import AppLayout from '@/components/layout/AppLayout';
import { NavigationProvider } from '@/contexts/NavigationContext';
import { useAuth } from '@/contexts/AuthContext';
import { strategiesApi } from '@/lib/api';
import type { Strategy, StrategyExecution } from '@/lib/types';
import { StrategyCard } from './components/StrategyCard';
import { StrategyDetails } from './components/StrategyDetails';
import { EmptyState } from './components/EmptyState';

type SortBy = 'name' | 'pnl' | 'winRate' | 'created';
type FilterStatus = 'all' | 'active' | 'paused' | 'needs_approval';
type FilterMode = 'all' | 'backtest' | 'paper' | 'live';
type FilterPlatform = 'all' | 'polymarket' | 'kalshi' | 'alpaca';

export default function StrategiesPage() {
  return (
    <AuthGate>
      <NavigationProvider>
        <AppLayout chatView={<StrategiesView />} />
      </NavigationProvider>
    </AuthGate>
  );
}

function StrategiesView() {
  const router = useRouter();
  const { user } = useAuth();
  
  // Data state
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [executions, setExecutions] = useState<StrategyExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Filter & Sort state
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortBy>('created');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [filterMode, setFilterMode] = useState<FilterMode>('all');
  const [filterPlatform, setFilterPlatform] = useState<FilterPlatform>('all');

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
        
        // Auto-select first strategy if none selected
        if (!selectedStrategy && response.strategies.length > 0) {
          handleSelectStrategy(response.strategies[0]);
        }
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

  const handleUpdateStrategy = async (strategyId: string, updates: any) => {
    if (!user?.id) return;
    
    try {
      await strategiesApi.updateStrategy(user.id, strategyId, updates);
      await loadStrategies();
      
      // Update selected strategy
      if (selectedStrategy?.id === strategyId) {
        const updatedStrategy = strategies.find(s => s.id === strategyId);
        if (updatedStrategy) {
          setSelectedStrategy(updatedStrategy);
        }
      }
    } catch (error) {
      console.error('Error updating strategy:', error);
    }
  };

  const handleDeleteStrategy = async (strategyId: string) => {
    if (!user?.id) return;
    
    try {
      await strategiesApi.deleteStrategy(user.id, strategyId);
      
      // Clear selection if deleted strategy was selected
      if (selectedStrategy?.id === strategyId) {
        setSelectedStrategy(null);
        setExecutions([]);
      }
      
      await loadStrategies();
    } catch (error) {
      console.error('Error deleting strategy:', error);
    }
  };

  const handleGraduateToLive = async (strategyId: string) => {
    if (!user?.id) return;
    
    try {
      // Update mode to live
      await strategiesApi.updateStrategy(user.id, strategyId, {
        stats: {
          mode: 'live'
        }
      });
      await loadStrategies();
      
      // Refresh selected strategy
      if (selectedStrategy?.id === strategyId) {
        const updatedStrategy = strategies.find(s => s.id === strategyId);
        if (updatedStrategy) {
          setSelectedStrategy(updatedStrategy);
        }
      }
    } catch (error) {
      console.error('Error graduating strategy:', error);
    }
  };

  // Filter and sort strategies
  const filteredAndSortedStrategies = useMemo(() => {
    let result = [...strategies];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(s =>
        s.name.toLowerCase().includes(query) ||
        s.description?.toLowerCase().includes(query) ||
        s.config?.thesis?.toLowerCase().includes(query)
      );
    }

    // Apply status filter
    if (filterStatus !== 'all') {
      result = result.filter(s => {
        if (filterStatus === 'active') return s.enabled && s.approved;
        if (filterStatus === 'paused') return !s.enabled && s.approved;
        if (filterStatus === 'needs_approval') return !s.approved;
        return true;
      });
    }

    // Apply mode filter
    if (filterMode !== 'all') {
      result = result.filter(s => (s.stats?.mode || 'paper') === filterMode);
    }

    // Apply platform filter
    if (filterPlatform !== 'all') {
      result = result.filter(s => s.config?.platform === filterPlatform);
    }

    // Apply sorting
    result.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'pnl':
          return (b.stats?.total_pnl || 0) - (a.stats?.total_pnl || 0);
        case 'winRate':
          return (b.stats?.win_rate || 0) - (a.stats?.win_rate || 0);
        case 'created':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        default:
          return 0;
      }
    });

    return result;
  }, [strategies, searchQuery, sortBy, filterStatus, filterMode, filterPlatform]);

  // Get active strategy count for header badge
  const activeCount = strategies.filter(s => s.enabled && s.approved).length;
  const hasLiveStrategies = strategies.some(s => s.stats?.mode === 'live' && s.enabled);

  if (loading) {
    return (
      <div className="h-full bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-gray-400 text-5xl mb-4">🤖</div>
          <div className="text-gray-600">Loading strategies...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-50 flex flex-col overflow-hidden">
      {/* Subheader with actions */}
      <div className="bg-white border-b border-gray-200 flex-shrink-0">
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-gray-900">Your Trading Bots</h2>
              {activeCount > 0 && (
                <div className={`px-3 py-1 rounded-full text-sm font-medium flex items-center gap-1 ${
                  hasLiveStrategies
                    ? 'bg-green-100 text-green-800'
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  <span className={`w-2 h-2 rounded-full ${
                    hasLiveStrategies ? 'bg-green-600' : 'bg-blue-600'
                  }`} />
                  <span>{activeCount} active</span>
                </div>
              )}
            </div>
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2 text-sm"
            >
              <span>➕</span>
              <span className="hidden sm:inline">Create New Bot</span>
              <span className="sm:hidden">Create</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-6 overflow-y-auto">
          {strategies.length === 0 ? (
            <EmptyState />
          ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column - Strategy List (30%) */}
            <div className="lg:col-span-4 xl:col-span-3 space-y-4">
              {/* Search Bar */}
              <div className="bg-white rounded-lg border border-gray-200 p-3">
                <input
                  type="text"
                  placeholder="Search strategies..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Filters & Sort */}
              <div className="bg-white rounded-lg border border-gray-200 p-3 space-y-3">
                {/* Status Filter */}
                <div>
                  <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                    Status
                  </label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                  >
                    <option value="all">All</option>
                    <option value="active">Active</option>
                    <option value="paused">Paused</option>
                    <option value="needs_approval">Needs Approval</option>
                  </select>
                </div>

                {/* Mode Filter */}
                <div>
                  <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                    Mode
                  </label>
                  <select
                    value={filterMode}
                    onChange={(e) => setFilterMode(e.target.value as FilterMode)}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                  >
                    <option value="all">All</option>
                    <option value="backtest">Backtest</option>
                    <option value="paper">Paper</option>
                    <option value="live">Live</option>
                  </select>
                </div>

                {/* Platform Filter */}
                <div>
                  <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                    Platform
                  </label>
                  <select
                    value={filterPlatform}
                    onChange={(e) => setFilterPlatform(e.target.value as FilterPlatform)}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                  >
                    <option value="all">All</option>
                    <option value="polymarket">Polymarket</option>
                    <option value="kalshi">Kalshi</option>
                    <option value="alpaca">Alpaca</option>
                  </select>
                </div>

                {/* Sort By */}
                <div>
                  <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                    Sort By
                  </label>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as SortBy)}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                  >
                    <option value="created">Created Date</option>
                    <option value="name">Name (A-Z)</option>
                    <option value="pnl">P&L (High to Low)</option>
                    <option value="winRate">Win Rate (High to Low)</option>
                  </select>
                </div>
              </div>

              {/* Results Count */}
              <div className="text-sm text-gray-500 px-2">
                Showing {filteredAndSortedStrategies.length} of {strategies.length} strategies
              </div>

              {/* Strategy Cards */}
              <div className="space-y-3 max-h-[calc(100vh-400px)] overflow-y-auto pb-4">
                {filteredAndSortedStrategies.map((strategy) => (
                  <StrategyCard
                    key={strategy.id}
                    strategy={strategy}
                    isSelected={selectedStrategy?.id === strategy.id}
                    onSelect={() => handleSelectStrategy(strategy)}
                    onToggle={() => handleToggleStrategy(strategy.id, strategy.enabled)}
                    onRun={(dryRun) => handleRunStrategy(strategy.id, dryRun)}
                    isLoading={
                      actionLoading === strategy.id ||
                      actionLoading === `run-${strategy.id}`
                    }
                  />
                ))}
              </div>

              {filteredAndSortedStrategies.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-2">🔍</div>
                  <p>No strategies match your filters</p>
                </div>
              )}
            </div>

            {/* Right Column - Strategy Details (70%) */}
            <div className="lg:col-span-8 xl:col-span-9">
              {selectedStrategy ? (
                <StrategyDetails
                  strategy={selectedStrategy}
                  executions={executions}
                  onRefresh={() => loadExecutions(selectedStrategy.id)}
                  onUpdate={(updates) => handleUpdateStrategy(selectedStrategy.id, updates)}
                  onDelete={() => handleDeleteStrategy(selectedStrategy.id)}
                  onGraduate={() => handleGraduateToLive(selectedStrategy.id)}
                />
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 p-12 text-center h-full flex items-center justify-center">
                  <div>
                    <div className="text-gray-400 text-6xl mb-4">📊</div>
                    <p className="text-gray-500 text-lg font-medium">Select a strategy to view details</p>
                    <p className="text-gray-400 text-sm mt-2">
                      Click on any strategy card to see its performance, code, and settings
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
          )}
        </div>
      </div>
    </div>
  );
}
