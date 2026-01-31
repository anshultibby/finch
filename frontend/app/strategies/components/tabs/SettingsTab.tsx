'use client';

import React, { useState } from 'react';
import type { Strategy } from '@/lib/types';

interface SettingsTabProps {
  strategy: Strategy;
  onUpdate: (updates: any) => Promise<void>;
  onDelete: () => Promise<void>;
  onGraduate?: () => Promise<void>;
}

export function SettingsTab({ strategy, onUpdate, onDelete, onGraduate }: SettingsTabProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const stats = strategy.stats || {};
  const config = strategy.config || {};
  const capital = config.capital || {};
  const mode = stats.mode || 'paper';

  const [formData, setFormData] = useState({
    totalCapital: capital.total_capital || 0,
    capitalPerTrade: capital.capital_per_trade || 0,
    maxPositions: capital.max_positions || 5,
    maxDailyLoss: capital.max_daily_loss || 0,
    executionFrequency: config.execution_frequency || 60,
  });

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onUpdate({
        config: {
          ...config,
          execution_frequency: formData.executionFrequency,
          capital: {
            ...capital,
            total_capital: formData.totalCapital,
            capital_per_trade: formData.capitalPerTrade,
            max_positions: formData.maxPositions,
            max_daily_loss: formData.maxDailyLoss,
          }
        }
      });
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const canGraduateToLive = () => {
    const paperTrades = stats.paper_trades || 0;
    const paperWinRate = stats.paper_win_rate || 0;
    const paperPnl = stats.paper_pnl || 0;
    const maxDrawdown = Math.abs(stats.max_drawdown || 0);

    return (
      paperTrades >= 20 &&
      paperWinRate > 0.55 &&
      paperPnl > 0 &&
      maxDrawdown < 0.20
    );
  };

  const graduationCriteria = [
    {
      label: '20+ paper trades',
      met: (stats.paper_trades || 0) >= 20,
      value: `${stats.paper_trades || 0}/20`
    },
    {
      label: '55%+ win rate',
      met: (stats.paper_win_rate || 0) > 0.55,
      value: `${((stats.paper_win_rate || 0) * 100).toFixed(1)}%`
    },
    {
      label: 'Positive P&L',
      met: (stats.paper_pnl || 0) > 0,
      value: `$${(stats.paper_pnl || 0).toFixed(2)}`
    },
    {
      label: '<20% max drawdown',
      met: Math.abs(stats.max_drawdown || 0) < 0.20,
      value: `${(Math.abs(stats.max_drawdown || 0) * 100).toFixed(1)}%`
    }
  ];

  return (
    <div className="space-y-6">
      {/* Execution Mode */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Execution Mode</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="mb-4">
            <span className="text-sm text-gray-600">Current Mode: </span>
            <span className={`text-lg font-semibold ${
              mode === 'live' ? 'text-green-600' :
              mode === 'paper' ? 'text-blue-600' :
              'text-gray-600'
            }`}>
              {mode === 'live' ? '🟢 Live Trading' :
               mode === 'paper' ? '📝 Paper Trading' :
               '🧪 Backtest'}
            </span>
          </div>

          {/* Mode Pills */}
          <div className="flex gap-2 mb-4">
            <button
              disabled
              className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-200 text-gray-500 cursor-not-allowed"
            >
              🧪 Backtest
            </button>
            <button
              disabled={mode === 'paper'}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                mode === 'paper'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              📝 Paper
            </button>
            <button
              disabled={mode === 'live' || !canGraduateToLive()}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                mode === 'live'
                  ? 'bg-green-600 text-white'
                  : canGraduateToLive()
                  ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
            >
              🟢 Live
            </button>
          </div>

          {/* Live Trading Requirements */}
          {mode !== 'live' && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start gap-2 mb-3">
                <span className="text-xl">⚠️</span>
                <div>
                  <h4 className="font-semibold text-yellow-900 text-sm">Live Trading Requirements</h4>
                </div>
              </div>
              <div className="space-y-2">
                {graduationCriteria.map((criterion, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700">{criterion.label}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-600">{criterion.value}</span>
                      <span>{criterion.met ? '✅' : '❌'}</span>
                    </div>
                  </div>
                ))}
              </div>
              {canGraduateToLive() && onGraduate && (
                <button
                  onClick={onGraduate}
                  className="w-full mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                >
                  Graduate to Live Trading
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Capital Settings */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">Capital Settings</h3>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
            >
              ✏️ Edit
            </button>
          )}
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Total Capital (USD)
            </label>
            <input
              type="number"
              disabled={!isEditing}
              value={formData.totalCapital}
              onChange={(e) => setFormData({ ...formData, totalCapital: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100 disabled:text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Capital Per Trade (USD)
            </label>
            <input
              type="number"
              disabled={!isEditing}
              value={formData.capitalPerTrade}
              onChange={(e) => setFormData({ ...formData, capitalPerTrade: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100 disabled:text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Positions
            </label>
            <input
              type="number"
              disabled={!isEditing}
              value={formData.maxPositions}
              onChange={(e) => setFormData({ ...formData, maxPositions: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100 disabled:text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Daily Loss (USD)
            </label>
            <input
              type="number"
              disabled={!isEditing}
              value={formData.maxDailyLoss}
              onChange={(e) => setFormData({ ...formData, maxDailyLoss: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100 disabled:text-gray-600"
            />
          </div>

          {isEditing && (
            <div className="flex gap-2 pt-2">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Execution Settings */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Execution Settings</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Execution Frequency (seconds)
          </label>
          <input
            type="range"
            min="10"
            max="300"
            step="10"
            disabled={!isEditing}
            value={formData.executionFrequency}
            onChange={(e) => setFormData({ ...formData, executionFrequency: parseInt(e.target.value) })}
            className="w-full"
          />
          <div className="text-sm text-gray-600 mt-2">
            Checks every {formData.executionFrequency} seconds
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div>
        <h3 className="font-semibold text-red-600 mb-3">Danger Zone</h3>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-3">
          <button
            onClick={() => onUpdate({ enabled: !strategy.enabled })}
            className={`w-full px-4 py-2 rounded-lg font-medium transition-colors ${
              strategy.enabled
                ? 'bg-gray-600 text-white hover:bg-gray-700'
                : 'bg-green-600 text-white hover:bg-green-700'
            }`}
          >
            {strategy.enabled ? '⏸️ Pause Strategy' : '▶️ Resume Strategy'}
          </button>

          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
            >
              🗑️ Delete Strategy
            </button>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-red-800 font-medium">
                Are you sure? This cannot be undone.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={onDelete}
                  className="flex-1 px-4 py-2 bg-red-700 text-white rounded-lg hover:bg-red-800 transition-colors font-medium"
                >
                  Yes, Delete
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
