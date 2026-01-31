'use client';

import React from 'react';

interface TrackRecordProgressProps {
  mode: string;
  paperTrades: number;
  paperWinRate: number;
  paperPnl: number;
  maxDrawdown: number;
  onGraduate?: () => void;
}

export function TrackRecordProgress({
  mode,
  paperTrades,
  paperWinRate,
  paperPnl,
  maxDrawdown,
  onGraduate
}: TrackRecordProgressProps) {
  if (mode === 'live') {
    return null; // Don't show if already live
  }

  const requiredTrades = 20;
  const tradesCompleted = Math.min(paperTrades, requiredTrades);
  const progressPercent = (tradesCompleted / requiredTrades) * 100;
  
  const criteria = {
    trades: paperTrades >= requiredTrades,
    winRate: paperWinRate > 0.55,
    pnl: paperPnl > 0,
    drawdown: Math.abs(maxDrawdown) < 0.20
  };
  
  const allCriteriaMet = criteria.trades && criteria.winRate && criteria.pnl && criteria.drawdown;
  const remainingTrades = Math.max(0, requiredTrades - paperTrades);

  return (
    <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg p-4 border border-blue-200">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">📊</span>
        <h4 className="font-semibold text-gray-900">Paper Trading Progress</h4>
      </div>
      
      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-600 mb-1">
          <span>{tradesCompleted}/{requiredTrades} trades completed</span>
          <span>{progressPercent.toFixed(0)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all ${
              allCriteriaMet ? 'bg-green-600' : 'bg-blue-600'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
      
      {/* Criteria Checklist */}
      <div className="space-y-2 text-sm mb-3">
        <div className="flex items-center justify-between">
          <span className="text-gray-700">Win Rate: {(paperWinRate * 100).toFixed(0)}%</span>
          <span>{criteria.winRate ? '✅' : '❌'} (need {'>'}55%)</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-700">P&L: ${paperPnl >= 0 ? '+' : ''}{paperPnl.toFixed(2)}</span>
          <span>{criteria.pnl ? '✅' : '❌'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-700">Max Drawdown: {(Math.abs(maxDrawdown) * 100).toFixed(0)}%</span>
          <span>{criteria.drawdown ? '✅' : '❌'} (limit 20%)</span>
        </div>
      </div>
      
      {/* Status */}
      {allCriteriaMet ? (
        <div>
          <p className="text-sm text-green-700 font-medium mb-2">
            🎉 Ready to graduate to live trading!
          </p>
          {onGraduate && (
            <button
              onClick={onGraduate}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              Graduate to Live Trading
            </button>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-600">
          ⏳ {remainingTrades > 0 ? `${remainingTrades} more trade${remainingTrades === 1 ? '' : 's'} to graduate` : 'Complete remaining criteria to graduate'}
        </p>
      )}
    </div>
  );
}
