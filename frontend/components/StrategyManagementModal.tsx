'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { strategiesApi, TradingStrategy, StrategyExecutionResult } from '@/lib/api';

interface StrategyManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function StrategyManagementModal({ isOpen, onClose }: StrategyManagementModalProps) {
  const { user } = useAuth();
  const [strategies, setStrategies] = useState<TradingStrategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<StrategyExecutionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && user?.id) {
      loadStrategies();
    }
  }, [isOpen, user?.id]);

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

  const handleExecuteStrategy = async (strategyId: string, strategyName: string) => {
    if (!user?.id) return;
    
    if (!confirm(`Execute strategy "${strategyName}"?\n\nThis will screen candidates and manage positions based on your rules.`)) {
      return;
    }
    
    setExecuting(strategyId);
    setError(null);
    setExecutionResult(null);
    setSelectedStrategy(strategyId);
    
    try {
      const result = await strategiesApi.executeStrategy(user.id, strategyId);
      setExecutionResult(result);
    } catch (err: any) {
      console.error('Error executing strategy:', err);
      setError(err.response?.data?.detail || 'Failed to execute strategy');
    } finally {
      setExecuting(null);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCandidateSource = (strategy: TradingStrategy) => {
    const source = strategy.candidate_source;
    if (source.type === 'universe') {
      return `${source.universe?.toUpperCase() || 'SP500'} Universe`;
    } else if (source.type === 'custom' || source.type === 'tickers') {
      return `Custom (${source.tickers?.length || 0} tickers)`;
    } else if (source.type === 'reddit_trending') {
      return `Reddit Trending (Top ${source.limit || 50})`;
    } else if (source.type === 'sector') {
      return `${source.sector || 'All'} Sector`;
    }
    return 'Unknown';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-5 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Strategy Management</h2>
            <p className="text-purple-100 text-sm mt-1">View and execute your trading strategies</p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
            </div>
          ) : strategies.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <div className="text-5xl mb-4">📈</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Strategies Yet</h3>
              <p className="text-gray-600 mb-4">
                Create a trading strategy using the chat to get started
              </p>
              <p className="text-sm text-gray-500">
                Try: "Create a momentum strategy for tech stocks"
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Strategies List */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Your Strategies</h3>
                <div className="space-y-3">
                  {strategies.map((strategy) => (
                    <div
                      key={strategy.id}
                      className="bg-white border-2 border-gray-200 rounded-lg p-5 hover:shadow-lg transition-shadow"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h4 className="text-xl font-bold text-gray-900">{strategy.name}</h4>
                            <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full">
                              ACTIVE
                            </span>
                          </div>
                          <p className="text-gray-600 mb-4">{strategy.description}</p>
                          
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
                            <div>
                              <span className="text-gray-500 block mb-1">Candidate Source</span>
                              <span className="font-semibold text-gray-900">{formatCandidateSource(strategy)}</span>
                            </div>
                            <div>
                              <span className="text-gray-500 block mb-1">Screening Rules</span>
                              <span className="font-semibold text-gray-900">{strategy.screening_rules.length} rules</span>
                            </div>
                            <div>
                              <span className="text-gray-500 block mb-1">Management Rules</span>
                              <span className="font-semibold text-gray-900">{strategy.management_rules.length} rules</span>
                            </div>
                            <div>
                              <span className="text-gray-500 block mb-1">Created</span>
                              <span className="font-semibold text-gray-900">{formatDate(strategy.created_at)}</span>
                            </div>
                          </div>

                          {/* Risk Parameters */}
                          <div className="bg-gray-50 rounded-lg p-3 mb-3">
                            <p className="text-xs font-semibold text-gray-600 mb-2">RISK PARAMETERS</p>
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
                              <div>
                                <span className="text-gray-500 block text-xs">Position Size</span>
                                <span className="font-semibold">{strategy.risk_parameters.position_size_pct}%</span>
                              </div>
                              <div>
                                <span className="text-gray-500 block text-xs">Max Positions</span>
                                <span className="font-semibold">{strategy.risk_parameters.max_positions}</span>
                              </div>
                              <div>
                                <span className="text-gray-500 block text-xs">Stop Loss</span>
                                <span className="font-semibold text-red-600">
                                  {strategy.risk_parameters.stop_loss_pct ? `${strategy.risk_parameters.stop_loss_pct}%` : 'N/A'}
                                </span>
                              </div>
                              <div>
                                <span className="text-gray-500 block text-xs">Take Profit</span>
                                <span className="font-semibold text-green-600">
                                  {strategy.risk_parameters.take_profit_pct ? `${strategy.risk_parameters.take_profit_pct}%` : 'N/A'}
                                </span>
                              </div>
                              <div>
                                <span className="text-gray-500 block text-xs">Max Hold Days</span>
                                <span className="font-semibold">
                                  {strategy.risk_parameters.max_hold_days || 'Unlimited'}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <button
                          onClick={() => handleExecuteStrategy(strategy.id, strategy.name)}
                          disabled={executing === strategy.id}
                          className="ml-4 flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
                        >
                          {executing === strategy.id ? (
                            <>
                              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                              Running...
                            </>
                          ) : (
                            <>
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              Run Strategy
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Execution Results */}
              {executionResult && selectedStrategy && (
                <div className="border-t-2 pt-6">
                  <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border-2 border-purple-200 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-bold text-gray-900">Execution Results</h3>
                      <span className="text-sm text-gray-600">
                        {formatDate(executionResult.timestamp)}
                      </span>
                    </div>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-white rounded-lg p-4 shadow-sm">
                        <p className="text-xs font-semibold text-gray-500 mb-1">BUY SIGNALS</p>
                        <p className="text-3xl font-bold text-green-600">
                          {executionResult.screening_decisions.filter(d => d.action === 'BUY').length +
                           executionResult.management_decisions.filter(d => d.action === 'BUY').length}
                        </p>
                      </div>
                      <div className="bg-white rounded-lg p-4 shadow-sm">
                        <p className="text-xs font-semibold text-gray-500 mb-1">SELL SIGNALS</p>
                        <p className="text-3xl font-bold text-red-600">
                          {executionResult.management_decisions.filter(d => d.action === 'SELL').length}
                        </p>
                      </div>
                      <div className="bg-white rounded-lg p-4 shadow-sm">
                        <p className="text-xs font-semibold text-gray-500 mb-1">HOLD SIGNALS</p>
                        <p className="text-3xl font-bold text-blue-600">
                          {executionResult.management_decisions.filter(d => d.action === 'HOLD').length}
                        </p>
                      </div>
                      <div className="bg-white rounded-lg p-4 shadow-sm">
                        <p className="text-xs font-semibold text-gray-500 mb-1">CASH AVAILABLE</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {formatCurrency(executionResult.budget.cash_available)}
                        </p>
                      </div>
                    </div>

                    {/* Screening Decisions */}
                    {executionResult.screening_decisions.length > 0 && (
                      <div className="mb-6">
                        <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                          Screening Decisions ({executionResult.screening_decisions.length})
                        </h4>
                        <div className="space-y-2 max-h-60 overflow-y-auto">
                          {executionResult.screening_decisions.map((decision) => (
                            <div
                              key={decision.decision_id}
                              className={`bg-white rounded-lg p-3 border-l-4 ${
                                decision.action === 'BUY' ? 'border-green-500' : 'border-gray-300'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-3">
                                  <span className="font-bold text-lg">{decision.ticker}</span>
                                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                    decision.action === 'BUY' 
                                      ? 'bg-green-100 text-green-700' 
                                      : 'bg-gray-100 text-gray-700'
                                  }`}>
                                    {decision.action}
                                  </span>
                                  <span className="text-sm text-gray-600">
                                    Confidence: {decision.confidence}%
                                  </span>
                                </div>
                                <span className="text-sm font-semibold">
                                  {formatCurrency(decision.current_price)}
                                </span>
                              </div>
                              <p className="text-sm text-gray-600 whitespace-pre-line">{decision.reasoning}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Management Decisions */}
                    {executionResult.management_decisions.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                          </svg>
                          Position Management ({executionResult.management_decisions.length})
                        </h4>
                        <div className="space-y-2 max-h-60 overflow-y-auto">
                          {executionResult.management_decisions.map((decision) => (
                            <div
                              key={decision.decision_id}
                              className={`bg-white rounded-lg p-3 border-l-4 ${
                                decision.action === 'SELL' 
                                  ? 'border-red-500' 
                                  : decision.action === 'BUY'
                                  ? 'border-green-500'
                                  : 'border-blue-500'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-3">
                                  <span className="font-bold text-lg">{decision.ticker}</span>
                                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                    decision.action === 'SELL' 
                                      ? 'bg-red-100 text-red-700'
                                      : decision.action === 'BUY'
                                      ? 'bg-green-100 text-green-700'
                                      : 'bg-blue-100 text-blue-700'
                                  }`}>
                                    {decision.action}
                                  </span>
                                  <span className="text-sm text-gray-600">
                                    Confidence: {decision.confidence}%
                                  </span>
                                </div>
                                {decision.position_data && (
                                  <span className={`text-sm font-semibold ${
                                    decision.position_data.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'
                                  }`}>
                                    {decision.position_data.pnl_pct >= 0 ? '+' : ''}{decision.position_data.pnl_pct.toFixed(2)}%
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-gray-600 whitespace-pre-line">{decision.reasoning}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t px-6 py-4 bg-gray-50 flex justify-between items-center">
          <p className="text-sm text-gray-600">
            Strategies are executed on virtual portfolios
          </p>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

