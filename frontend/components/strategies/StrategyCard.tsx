'use client';

import React from 'react';
import { TradingStrategy } from '@/lib/api';

interface StrategyCardProps {
  strategy: TradingStrategy;
  onRun: () => void;
  onEdit: () => void;
}

export default function StrategyCard({ strategy, onRun, onEdit }: StrategyCardProps) {
  const formatCandidateSource = () => {
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

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    return `${Math.floor(diffDays / 30)}mo ago`;
  };

  return (
    <div className="bg-white border-2 border-gray-200 rounded-xl p-5 hover:shadow-lg hover:border-purple-300 transition-all group">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-xl font-bold text-gray-900">{strategy.name}</h3>
            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-semibold rounded-full">
              ACTIVE
            </span>
          </div>
          <p className="text-sm text-gray-600 line-clamp-2">{strategy.description}</p>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4 py-3 border-y border-gray-100">
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Source</p>
          <p className="text-sm font-semibold text-gray-900 truncate" title={formatCandidateSource()}>
            {formatCandidateSource()}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Rules</p>
          <p className="text-sm font-semibold text-gray-900">
            {strategy.screening_rules.length + strategy.management_rules.length}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Max Positions</p>
          <p className="text-sm font-semibold text-gray-900">
            {strategy.risk_parameters.max_positions}
          </p>
        </div>
      </div>

      {/* Risk Metrics */}
      <div className="bg-gray-50 rounded-lg p-3 mb-4">
        <p className="text-xs font-semibold text-gray-500 mb-2">RISK PARAMETERS</p>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <span className="text-gray-500">Position:</span>{' '}
            <span className="font-semibold">{strategy.risk_parameters.position_size_pct}%</span>
          </div>
          <div>
            <span className="text-gray-500">Stop:</span>{' '}
            <span className="font-semibold text-red-600">
              {strategy.risk_parameters.stop_loss_pct ? `${strategy.risk_parameters.stop_loss_pct}%` : 'N/A'}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Target:</span>{' '}
            <span className="font-semibold text-green-600">
              {strategy.risk_parameters.take_profit_pct ? `${strategy.risk_parameters.take_profit_pct}%` : 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">
          Created {formatDate(strategy.created_at)}
        </p>
        
        <div className="flex items-center gap-2">
          <button
            onClick={onEdit}
            className="px-3 py-1.5 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Edit
          </button>
          <button
            onClick={onRun}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-lg shadow-sm hover:shadow-md transition-all"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
            </svg>
            Run
          </button>
        </div>
      </div>
    </div>
  );
}

