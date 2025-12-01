'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { useChatMode } from '@/contexts/ChatModeContext';
import { strategiesApi, TradingStrategy, StrategyExecutionResult } from '@/lib/api';

export default function StrategiesView() {
  const { user } = useAuth();
  const { navigateTo } = useNavigation();
  const { setMode } = useChatMode();
  const [strategies, setStrategies] = useState<TradingStrategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [executing, setExecuting] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<StrategyExecutionResult | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<TradingStrategy | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'detail' | 'results'>('list');

  useEffect(() => {
    loadStrategies();
  }, [user?.id]);

  const loadStrategies = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await strategiesApi.getStrategies(user.id, true);
      setStrategies(data);
    } catch (err: any) {
      console.error('Error loading strategies:', err);
      setError(err.response?.data?.detail || 'Failed to load strategies');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStrategy = () => {
    // Set chat mode to strategy creation
    setMode({ type: 'create_strategy' });
    // Navigate to chat
    navigateTo('chat');
  };

  const handleRunStrategy = async (strategy: TradingStrategy) => {
    if (!user?.id) return;
    
    setExecuting(strategy.id);
    setSelectedStrategy(strategy);
    setError(null);
    setExecutionResult(null);
    setViewMode('results');
    
    try {
      const result = await strategiesApi.executeStrategy(user.id, strategy.id);
      setExecutionResult(result);
    } catch (err: any) {
      console.error('Error executing strategy:', err);
      setError(err.response?.data?.detail || 'Failed to execute strategy');
      setViewMode('list');
    } finally {
      setExecuting(null);
    }
  };

  const handleViewStrategy = (strategy: TradingStrategy) => {
    setSelectedStrategy(strategy);
    setViewMode('detail');
    setExecutionResult(null);
  };

  const handleBackToList = () => {
    setViewMode('list');
    setSelectedStrategy(null);
    setExecutionResult(null);
  };

  const handleEditStrategy = (strategy: TradingStrategy) => {
    // Set chat mode to edit
    setMode({ 
      type: 'edit_strategy',
      metadata: {
        strategyId: strategy.id,
        strategyName: strategy.name,
      }
    });
    // Navigate to chat
    navigateTo('chat');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading strategies...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center max-w-md">
          <div className="text-5xl mb-4">⚠️</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Strategies</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={loadStrategies}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatCandidateSource = (source: any) => {
    if (source.type === 'universe') {
      return source.universe?.toUpperCase() || 'SP500';
    } else if (source.type === 'custom' || source.type === 'tickers') {
      return `${source.tickers?.length || 0} Custom Tickers`;
    } else if (source.type === 'reddit_trending') {
      return `Reddit Top ${source.limit || 50}`;
    } else if (source.type === 'sector') {
      return source.sector || 'All Sectors';
    }
    return 'Unknown';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    return date.toLocaleDateString();
  };

  return (
    <>
      <div className="h-full overflow-y-auto bg-gray-50">
        <div className="max-w-6xl mx-auto px-6 py-8">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                {viewMode !== 'list' && (
                  <button
                    onClick={handleBackToList}
                    className="flex items-center gap-2 px-3 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Back
                  </button>
                )}
                <h2 className="text-3xl font-bold text-gray-900">
                  {viewMode === 'detail' && selectedStrategy ? selectedStrategy.name : 
                   viewMode === 'results' ? 'Execution Results' : 
                   'Your Trading Strategies'}
                </h2>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleCreateStrategy}
                  className="flex items-center gap-2 px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all"
                >
                  <span className="text-xl">+</span>
                  Create New
                </button>
              </div>
            </div>
            {viewMode === 'list' && (
              <p className="text-gray-600">
                {strategies.length === 0 
                  ? "Get started by creating your first trading strategy"
                  : `${strategies.length} ${strategies.length === 1 ? 'active strategy' : 'active strategies'}`
                }
              </p>
            )}
          </div>

          {/* Main Content Area */}
          {viewMode === 'list' && (
            <>
              {strategies.length === 0 ? (
                <div className="text-center py-16 bg-white rounded-xl border-2 border-dashed border-gray-300">
                  <div className="text-6xl mb-4">📊</div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">No Strategies Yet</h3>
                  <p className="text-gray-600 mb-6 max-w-md mx-auto">
                    Create your first trading strategy to start screening stocks and managing positions
                  </p>
                  <button
                    onClick={handleCreateStrategy}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all"
                  >
                    <span className="text-xl">+</span>
                    Create Your First Strategy
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {strategies.map((strategy) => (
                    <div
                      key={strategy.id}
                      className="bg-white border border-gray-200 rounded-lg hover:shadow-md hover:border-purple-300 transition-all cursor-pointer group"
                      onClick={() => handleViewStrategy(strategy)}
                    >
                      <div className="p-5">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="text-xl font-bold text-gray-900 truncate">{strategy.name}</h3>
                              <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-semibold rounded-full shrink-0">
                                ACTIVE
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 line-clamp-1 mb-3">{strategy.description}</p>
                            
                            <div className="flex items-center gap-6 text-sm">
                              <div className="flex items-center gap-1.5">
                                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                </svg>
                                <span className="text-gray-700">{formatCandidateSource(strategy.candidate_source)}</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                </svg>
                                <span className="text-gray-700">{strategy.screening_rules.length + strategy.management_rules.length} rules</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <span className="text-gray-500">{formatDate(strategy.created_at)}</span>
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEditStrategy(strategy);
                              }}
                              className="px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                              Edit
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRunStrategy(strategy);
                              }}
                              disabled={executing === strategy.id}
                              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-lg shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {executing === strategy.id ? (
                                <>
                                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                  Running...
                                </>
                              ) : (
                                <>
                                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                                  </svg>
                                  Run
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Detail View */}
          {viewMode === 'detail' && selectedStrategy && (
            <div className="space-y-6">
              {/* Overview */}
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-purple-600 mb-1">STRATEGY OVERVIEW</p>
                    <p className="text-gray-700">{selectedStrategy.description}</p>
                  </div>
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => handleEditStrategy(selectedStrategy)}
                      className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleRunStrategy(selectedStrategy)}
                      disabled={executing === selectedStrategy.id}
                      className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-lg shadow-sm hover:shadow-md transition-all disabled:opacity-50"
                    >
                      {executing === selectedStrategy.id ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          Running...
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                          </svg>
                          Run Strategy
                        </>
                      )}
                    </button>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-100">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Candidate Source</p>
                    <p className="text-sm font-semibold text-gray-900">{formatCandidateSource(selectedStrategy.candidate_source)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Max Positions</p>
                    <p className="text-sm font-semibold text-gray-900">{selectedStrategy.risk_parameters.max_positions}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Position Size</p>
                    <p className="text-sm font-semibold text-gray-900">{selectedStrategy.risk_parameters.position_size_pct}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Created</p>
                    <p className="text-sm font-semibold text-gray-900">{formatDate(selectedStrategy.created_at)}</p>
                  </div>
                </div>
              </div>

              {/* Risk Parameters */}
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <p className="text-sm font-semibold text-purple-600 mb-4">RISK MANAGEMENT</p>
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Stop Loss</p>
                    <p className="text-lg font-bold text-red-600">
                      {selectedStrategy.risk_parameters.stop_loss_pct ? `${selectedStrategy.risk_parameters.stop_loss_pct}%` : 'None'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Take Profit</p>
                    <p className="text-lg font-bold text-green-600">
                      {selectedStrategy.risk_parameters.take_profit_pct ? `${selectedStrategy.risk_parameters.take_profit_pct}%` : 'None'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Max Hold Days</p>
                    <p className="text-lg font-bold text-gray-900">
                      {selectedStrategy.risk_parameters.max_hold_days || 'Unlimited'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Screening Rules */}
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm font-semibold text-purple-600">SCREENING RULES ({selectedStrategy.screening_rules.length})</p>
                  <p className="text-xs text-gray-500">Evaluate candidates to find BUY opportunities</p>
                </div>
                <div className="space-y-3">
                  {selectedStrategy.screening_rules
                    .sort((a, b) => a.order - b.order)
                    .map((rule, idx) => (
                      <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                        <div className="flex items-start justify-between gap-4 mb-2">
                          <div className="flex items-center gap-3">
                            <div className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-100 text-purple-700 text-xs font-bold">
                              {rule.order}
                            </div>
                            <h4 className="font-semibold text-gray-900">{rule.description}</h4>
                          </div>
                          <span className="text-xs font-semibold text-gray-500 shrink-0">Weight: {(rule.weight * 100).toFixed(0)}%</span>
                        </div>
                        <div className="ml-9">
                          <p className="text-sm text-gray-700 mb-2">{rule.decision_logic}</p>
                          {rule.data_sources && rule.data_sources.length > 0 && (
                            <div className="flex items-center gap-2 flex-wrap mt-2">
                              <span className="text-xs text-gray-500">Data:</span>
                              {rule.data_sources.map((ds, dsIdx) => (
                                <span key={dsIdx} className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                                  {ds.type.toUpperCase()}: {ds.endpoint}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Management Rules */}
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm font-semibold text-purple-600">MANAGEMENT RULES ({selectedStrategy.management_rules.length})</p>
                  <p className="text-xs text-gray-500">Manage existing positions (BUY/HOLD/SELL)</p>
                </div>
                <div className="space-y-3">
                  {selectedStrategy.management_rules
                    .sort((a, b) => a.order - b.order)
                    .map((rule, idx) => (
                      <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                        <div className="flex items-start justify-between gap-4 mb-2">
                          <div className="flex items-center gap-3">
                            <div className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                              {rule.order}
                            </div>
                            <h4 className="font-semibold text-gray-900">{rule.description}</h4>
                          </div>
                          <span className="text-xs font-semibold text-gray-500 shrink-0">Weight: {(rule.weight * 100).toFixed(0)}%</span>
                        </div>
                        <div className="ml-9">
                          <p className="text-sm text-gray-700 mb-2">{rule.decision_logic}</p>
                          {rule.data_sources && rule.data_sources.length > 0 && (
                            <div className="flex items-center gap-2 flex-wrap mt-2">
                              <span className="text-xs text-gray-500">Data:</span>
                              {rule.data_sources.map((ds, dsIdx) => (
                                <span key={dsIdx} className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                                  {ds.type.toUpperCase()}: {ds.endpoint}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}

          {/* Results View */}
          {viewMode === 'results' && executionResult && selectedStrategy && (
            <div className="mt-8 bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-6 py-4 bg-gradient-to-r from-purple-600 to-purple-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="bg-white/20 p-2 rounded-lg">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">Execution Results</h3>
                    <p className="text-purple-100 text-sm">{selectedStrategy.name}</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setExecutionResult(null);
                    setSelectedStrategy(null);
                  }}
                  className="text-white hover:bg-white/10 p-2 rounded-lg transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="p-6">
                {/* Summary Stats */}
                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                    <p className="text-green-600 text-sm font-semibold mb-1">BUY Signals</p>
                    <p className="text-3xl font-bold text-green-700">
                      {[...executionResult.screening_decisions, ...executionResult.management_decisions].filter(d => d.action === 'BUY').length}
                    </p>
                  </div>
                  <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                    <p className="text-red-600 text-sm font-semibold mb-1">SELL Signals</p>
                    <p className="text-3xl font-bold text-red-700">
                      {[...executionResult.screening_decisions, ...executionResult.management_decisions].filter(d => d.action === 'SELL').length}
                    </p>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                    <p className="text-blue-600 text-sm font-semibold mb-1">HOLD Signals</p>
                    <p className="text-3xl font-bold text-blue-700">
                      {[...executionResult.screening_decisions, ...executionResult.management_decisions].filter(d => d.action === 'HOLD').length}
                    </p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                    <p className="text-purple-600 text-sm font-semibold mb-1">Total Decisions</p>
                    <p className="text-3xl font-bold text-purple-700">
                      {executionResult.screening_decisions.length + executionResult.management_decisions.length}
                    </p>
                  </div>
                </div>

                {/* Budget Info */}
                {executionResult.budget && (
                  <div className="bg-gray-50 rounded-lg p-4 mb-6 border border-gray-200">
                    <h4 className="font-semibold text-gray-900 mb-3">Budget Status</h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-sm text-gray-600">Total Budget</p>
                        <p className="font-semibold text-gray-900">{formatCurrency(executionResult.budget.total_budget)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Available Cash</p>
                        <p className="font-semibold text-green-600">{formatCurrency(executionResult.budget.cash_available)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Invested</p>
                        <p className="font-semibold text-blue-600">{formatCurrency(executionResult.budget.position_value)}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Screening Decisions */}
                {executionResult.screening_decisions.length > 0 && (
                  <div className="mb-6">
                    <h4 className="font-semibold text-gray-900 mb-3">Screening Decisions</h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {executionResult.screening_decisions.map((decision, idx) => (
                        <div key={idx} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <span className="font-bold text-gray-900 text-lg">{decision.ticker}</span>
                              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                decision.action === 'BUY' 
                                  ? 'bg-green-100 text-green-700' 
                                  : decision.action === 'SELL'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-gray-100 text-gray-700'
                              }`}>
                                {decision.action}
                              </span>
                            </div>
                            <div className="text-sm text-gray-600">
                              Confidence: {(decision.confidence * 100).toFixed(0)}%
                            </div>
                          </div>
                          <p className="text-sm text-gray-600 mt-2">{decision.reasoning}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Management Decisions */}
                {executionResult.management_decisions.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Position Management</h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {executionResult.management_decisions.map((decision, idx) => (
                        <div key={idx} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <span className="font-bold text-gray-900 text-lg">{decision.ticker}</span>
                              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                decision.action === 'BUY' 
                                  ? 'bg-green-100 text-green-700' 
                                  : decision.action === 'SELL'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-blue-100 text-blue-700'
                              }`}>
                                {decision.action}
                              </span>
                            </div>
                            <div className="text-sm text-gray-600">
                              Confidence: {(decision.confidence * 100).toFixed(0)}%
                            </div>
                          </div>
                          <p className="text-sm text-gray-600 mt-2">{decision.reasoning}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* No Decisions */}
                {executionResult.screening_decisions.length === 0 && executionResult.management_decisions.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <p>No trading decisions at this time.</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

