'use client';

import React, { useState } from 'react';
import type { StrategyDetail } from '@/lib/types';

interface SettingsTabProps {
  strategy: StrategyDetail;
  onUpdate: (updates: any) => Promise<void>;
  onApprove: () => Promise<void>;
  onDelete: () => Promise<void>;
}

const FREQUENCY_PRESETS = [
  { label: 'Every 5 min',  cron: '*/5 * * * *',   description: 'Every 5 minutes' },
  { label: 'Every 15 min', cron: '*/15 * * * *',  description: 'Every 15 minutes' },
  { label: 'Every 30 min', cron: '*/30 * * * *',  description: 'Every 30 minutes' },
  { label: 'Every hour',   cron: '0 * * * *',     description: 'Every hour' },
  { label: 'Every 4 hrs',  cron: '0 */4 * * *',   description: 'Every 4 hours' },
  { label: 'Daily 9am',    cron: '0 9 * * *',     description: 'Daily at 9am UTC' },
  { label: 'Weekdays 9am', cron: '0 9 * * 1-5',   description: 'Weekdays at 9am UTC' },
  { label: 'Custom',       cron: '',              description: '' },
] as const;

function matchPreset(cron: string) {
  return FREQUENCY_PRESETS.find(p => p.cron === cron && p.cron !== '') ?? FREQUENCY_PRESETS.find(p => p.label === 'Custom')!;
}

export function SettingsTab({ strategy, onUpdate, onApprove, onDelete }: SettingsTabProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isSavingSchedule, setIsSavingSchedule] = useState(false);
  const [isSavingRisk, setIsSavingRisk] = useState(false);

  const riskLimits = strategy.risk_limits;
  const isPaperMode = strategy.paper_mode ?? true;

  // Schedule state
  const currentPreset = matchPreset(strategy.schedule ?? '');
  const [selectedPreset, setSelectedPreset] = useState(currentPreset);
  const [customCron, setCustomCron] = useState(
    currentPreset.label === 'Custom' ? (strategy.schedule ?? '') : ''
  );
  const [scheduleChanged, setScheduleChanged] = useState(false);

  // Risk limits state
  const [maxOrderUsd, setMaxOrderUsd] = useState(riskLimits?.max_order_usd ?? '');
  const [maxDailyUsd, setMaxDailyUsd] = useState(riskLimits?.max_daily_usd ?? '');
  const [riskChanged, setRiskChanged] = useState(false);

  const handlePresetChange = (preset: typeof FREQUENCY_PRESETS[number]) => {
    setSelectedPreset(preset);
    setScheduleChanged(true);
  };

  const handleSaveSchedule = async () => {
    const cron = selectedPreset.label === 'Custom' ? customCron : selectedPreset.cron;
    const description = selectedPreset.label === 'Custom' ? customCron : selectedPreset.description;
    setIsSavingSchedule(true);
    try {
      await onUpdate({ schedule: cron || undefined, schedule_description: description || undefined });
      setScheduleChanged(false);
    } finally {
      setIsSavingSchedule(false);
    }
  };

  const handleSaveRisk = async () => {
    setIsSavingRisk(true);
    try {
      await onUpdate({
        risk_limits: {
          max_order_usd: maxOrderUsd ? Number(maxOrderUsd) : undefined,
          max_daily_usd: maxDailyUsd ? Number(maxDailyUsd) : undefined,
        },
      });
      setRiskChanged(false);
    } finally {
      setIsSavingRisk(false);
    }
  };

  return (
    <div className="space-y-6">

      {/* Approval */}
      {!strategy.approved && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Approval</h3>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800 mb-3">
              Review the code carefully before approving. Once approved the strategy can be enabled.
            </p>
            <button
              onClick={onApprove}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium text-sm"
            >
              Approve Strategy
            </button>
          </div>
        </div>
      )}

      {/* Execution Mode */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Execution Mode</h3>
        <div className={`rounded-lg border p-4 ${isPaperMode ? 'bg-blue-50 border-blue-200' : 'bg-green-50 border-green-200'}`}>
          <div className="flex items-center justify-between">
            <div>
              <div className={`font-semibold ${isPaperMode ? 'text-blue-900' : 'text-green-900'}`}>
                {isPaperMode ? 'Paper (shadow)' : 'Live'}
              </div>
              <div className={`text-sm mt-0.5 ${isPaperMode ? 'text-blue-700' : 'text-green-700'}`}>
                {isPaperMode
                  ? 'Runs simulate trades — no real orders placed'
                  : 'Runs place real orders'}
              </div>
            </div>
            <button
              onClick={() => onUpdate({ paper_mode: !isPaperMode })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                isPaperMode ? 'bg-blue-400' : 'bg-green-600'
              }`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                isPaperMode ? 'translate-x-1' : 'translate-x-6'
              }`} />
            </button>
          </div>
          {!isPaperMode && (
            <p className="mt-2 text-xs text-green-800 bg-green-100 rounded px-2 py-1">
              ⚠️ Real money will be spent on each scheduled run
            </p>
          )}
        </div>
      </div>

      {/* Frequency */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Run Frequency</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-4 gap-2">
            {FREQUENCY_PRESETS.map(preset => (
              <button
                key={preset.label}
                onClick={() => handlePresetChange(preset)}
                className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${
                  selectedPreset.label === preset.label
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:text-blue-600'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>

          {selectedPreset.label === 'Custom' && (
            <div>
              <label className="block text-xs text-gray-500 mb-1">Cron expression</label>
              <input
                type="text"
                value={customCron}
                onChange={e => { setCustomCron(e.target.value); setScheduleChanged(true); }}
                placeholder="e.g. 0 */2 * * *"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          {scheduleChanged && (
            <button
              onClick={handleSaveSchedule}
              disabled={isSavingSchedule}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {isSavingSchedule ? 'Saving…' : 'Save Frequency'}
            </button>
          )}

          {!scheduleChanged && strategy.schedule && (
            <p className="text-xs text-gray-400 font-mono">{strategy.schedule}</p>
          )}
        </div>
      </div>

      {/* Risk Limits */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Risk Limits</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Max per order (USD)</label>
              <input
                type="number"
                value={maxOrderUsd}
                onChange={e => { setMaxOrderUsd(e.target.value); setRiskChanged(true); }}
                placeholder="No limit"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Max per day (USD)</label>
              <input
                type="number"
                value={maxDailyUsd}
                onChange={e => { setMaxDailyUsd(e.target.value); setRiskChanged(true); }}
                placeholder="No limit"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          {riskChanged && (
            <button
              onClick={handleSaveRisk}
              disabled={isSavingRisk}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {isSavingRisk ? 'Saving…' : 'Save Risk Limits'}
            </button>
          )}
        </div>
      </div>

      {/* Capital (read-only) */}
      {strategy.capital && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Capital</h3>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 grid grid-cols-3 gap-4 text-sm">
            {strategy.capital.total !== undefined && (
              <div>
                <div className="text-xs text-gray-500 mb-0.5">Total</div>
                <div className="font-semibold">${strategy.capital.total}</div>
              </div>
            )}
            {strategy.capital.per_trade !== undefined && (
              <div>
                <div className="text-xs text-gray-500 mb-0.5">Per Trade</div>
                <div className="font-semibold">${strategy.capital.per_trade}</div>
              </div>
            )}
            {strategy.capital.max_positions !== undefined && (
              <div>
                <div className="text-xs text-gray-500 mb-0.5">Max Positions</div>
                <div className="font-semibold">{strategy.capital.max_positions}</div>
              </div>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            To change capital allocation, ask the AI to update and redeploy the strategy.
          </p>
        </div>
      )}

      {/* Enable/Pause */}
      {strategy.approved && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Scheduling</h3>
          <button
            onClick={() => onUpdate({ enabled: !strategy.enabled })}
            className={`w-full px-4 py-2 rounded-lg font-medium transition-colors ${
              strategy.enabled
                ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                : 'bg-green-600 text-white hover:bg-green-700'
            }`}
          >
            {strategy.enabled ? 'Pause Strategy' : 'Enable Strategy'}
          </button>
        </div>
      )}

      {/* Danger Zone */}
      <div>
        <h3 className="font-semibold text-red-600 mb-3">Danger Zone</h3>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
            >
              Delete Strategy
            </button>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-red-800 font-medium">Are you sure? This cannot be undone.</p>
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
