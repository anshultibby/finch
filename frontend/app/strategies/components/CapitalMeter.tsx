'use client';

import React from 'react';

interface CapitalMeterProps {
  totalCapital: number;
  deployed: number;
  perTrade: number;
  currentPositions: number;
  maxPositions: number;
}

export function CapitalMeter({
  totalCapital,
  deployed,
  perTrade,
  currentPositions,
  maxPositions
}: CapitalMeterProps) {
  const available = totalCapital - deployed;
  const deployedPercent = totalCapital > 0 ? (deployed / totalCapital) * 100 : 0;
  const availablePercent = 100 - deployedPercent;

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <h4 className="font-semibold text-gray-900 mb-3">Capital Allocation</h4>
      
      <div className="space-y-3 font-mono text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Total Capital:</span>
          <span className="font-bold text-gray-900">${totalCapital.toFixed(2)}</span>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-gray-600">├── Deployed:</span>
          <span className="font-bold text-blue-600">${deployed.toFixed(2)}</span>
          <span className="text-xs text-gray-500">({deployedPercent.toFixed(0)}%)</span>
          <div className="flex-1 bg-gray-200 rounded-full h-1.5 ml-2">
            <div
              className="bg-blue-600 h-1.5 rounded-full"
              style={{ width: `${Math.min(deployedPercent, 100)}%` }}
            />
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-gray-600">├── Available:</span>
          <span className="font-bold text-green-600">${available.toFixed(2)}</span>
          <span className="text-xs text-gray-500">({availablePercent.toFixed(0)}%)</span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600">└── Per Trade:</span>
          <span className="font-bold text-gray-900">${perTrade.toFixed(2)}</span>
        </div>
        
        <div className="pt-2 border-t border-gray-300 flex justify-between">
          <span className="text-gray-600">Positions:</span>
          <span className="font-bold text-gray-900">
            {currentPositions} / {maxPositions} max
          </span>
        </div>
      </div>
    </div>
  );
}
