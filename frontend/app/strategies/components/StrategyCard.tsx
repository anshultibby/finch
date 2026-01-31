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
  const mode = strategy.stats?.mode || 'paper';
  const totalTrades = strategy.stats?.total_trades || 0;
  const winRate = strategy.stats?.win_rate || 0;
  const totalPnl = strategy.stats?.total_pnl || 0;
  
  // Capital allocation (from config)
  const capital = strategy.config?.capital || {};
  const totalCapital = capital.total_capital || 0;
  const deployed = capital.deployed || 0;
  const available = totalCapital - deployed;
  const deployedPercent = totalCapital > 0 ? (deployed / totalCapital) * 100 : 0;

  const getStatusBadge = () => {
    if (!strategy.approved) {
      return { text: 'Needs Approval', icon: '⚠️', color: 'bg-yellow-100 text-yellow-800 border-yellow-200' };
    }
    if (!strategy.enabled) {
      return { text: 'Paused', icon: '⏸️', color: 'bg-gray-100 text-gray-600 border-gray-200' };
    }
    
    if (mode === 'live') {
      return { text: 'Live', icon: '🟢', color: 'bg-green-100 text-green-800 border-green-200' };
    } else if (mode === 'paper') {
      return { text: 'Paper', icon: '📝', color: 'bg-blue-100 text-blue-800 border-blue-200' };
    } else if (mode === 'backtest') {
      return { text: 'Backtest', icon: '🧪', color: 'bg-purple-100 text-purple-800 border-purple-200' };
    }
    return { text: 'Active', icon: '✅', color: 'bg-green-100 text-green-800 border-green-200' };
  };

  const getModeBadge = () => {
    if (mode === 'live') return { text: 'Live', color: 'bg-green-50 text-green-700' };
    if (mode === 'paper') return { text: 'Paper', color: 'bg-blue-50 text-blue-700' };
    if (mode === 'backtest') return { text: 'Backtest', color: 'bg-gray-50 text-gray-700' };
    return null;
  };

  const statusBadge = getStatusBadge();
  const modeBadge = getModeBadge();
  const frequency = strategy.config?.execution_frequency || 60;

  return (
    <div
      onClick={onSelect}
      className={`bg-white rounded-lg border-2 p-4 cursor-pointer transition-all hover:shadow-md ${
        isSelected
          ? 'border-blue-500 shadow-lg'
          : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0 mr-2">
          <h3 className="text-lg font-semibold text-gray-900 truncate">{strategy.name}</h3>
          <p className="text-xs text-gray-500 italic mt-0.5 line-clamp-2">
            {strategy.config?.thesis || strategy.description}
          </p>
        </div>
        <div className="flex flex-col gap-1">
          <div className={`px-2 py-1 rounded-full text-xs font-medium border flex items-center gap-1 whitespace-nowrap ${statusBadge.color}`}>
            <span>{statusBadge.icon}</span>
            <span>{statusBadge.text}</span>
          </div>
          {modeBadge && (
            <div className={`px-2 py-1 rounded text-xs font-medium text-center ${modeBadge.color}`}>
              {modeBadge.text}
            </div>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-gray-50 rounded p-2 text-center">
          <div className="text-base font-bold text-gray-900">{totalTrades}</div>
          <div className="text-xs text-gray-500">Trades</div>
        </div>
        <div className="bg-gray-50 rounded p-2 text-center">
          <div className={`text-base font-bold ${winRate > 0.55 ? 'text-green-600' : winRate < 0.45 ? 'text-red-600' : 'text-gray-900'}`}>
            {(winRate * 100).toFixed(0)}%
          </div>
          <div className="text-xs text-gray-500">Win Rate</div>
        </div>
        <div className="bg-gray-50 rounded p-2 text-center">
          <div className={`text-base font-bold ${totalPnl > 0 ? 'text-green-600' : totalPnl < 0 ? 'text-red-600' : 'text-gray-900'}`}>
            ${totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(0)}
          </div>
          <div className="text-xs text-gray-500">P&L</div>
        </div>
      </div>

      {/* Capital Meter */}
      {totalCapital > 0 && (
        <div className="mb-3">
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>${deployed.toFixed(0)} deployed</span>
            <span>${totalCapital.toFixed(0)} total</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${Math.min(deployedPercent, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Execution Frequency */}
      <div className="text-xs text-gray-500 mb-3 flex items-center gap-1">
        <span>⏱️</span>
        <span>Every {frequency}s</span>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        {strategy.approved && (
          <button
            onClick={(e) => { e.stopPropagation(); onToggle(); }}
            disabled={isLoading}
            className={`flex-1 px-3 py-2 rounded text-xs font-medium transition-colors ${
              strategy.enabled
                ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                : 'bg-green-600 text-white hover:bg-green-700'
            } disabled:opacity-50`}
          >
            {isLoading ? '...' : strategy.enabled ? '⏸️ Pause' : '▶️ Enable'}
          </button>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onRun(true); }}
          disabled={isLoading}
          className="px-3 py-2 rounded text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors disabled:opacity-50"
        >
          🧪 Test
        </button>
        <button
          onClick={onSelect}
          className="px-3 py-2 rounded text-xs font-medium bg-gray-50 text-gray-700 hover:bg-gray-100 transition-colors"
        >
          👁️ View
        </button>
      </div>
    </div>
  );
}
