'use client';

import React, { useState } from 'react';
import type { Strategy, StrategyExecution } from '@/lib/types';
import { OverviewTab } from './tabs/OverviewTab';
import { CodeTab } from './tabs/CodeTab';
import { HistoryTab } from './tabs/HistoryTab';
import { PerformanceTab } from './tabs/PerformanceTab';
import { SettingsTab } from './tabs/SettingsTab';

interface StrategyDetailsProps {
  strategy: Strategy;
  executions: StrategyExecution[];
  onRefresh: () => void;
  onUpdate: (updates: any) => Promise<void>;
  onDelete: () => Promise<void>;
  onGraduate?: () => Promise<void>;
}

type TabType = 'overview' | 'code' | 'history' | 'performance' | 'settings';

export function StrategyDetails({
  strategy,
  executions,
  onRefresh,
  onUpdate,
  onDelete,
  onGraduate
}: StrategyDetailsProps) {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview', icon: '📊' },
    { id: 'code' as TabType, label: 'Code', icon: '💻' },
    { id: 'history' as TabType, label: 'Execution History', badge: executions.length, icon: '📋' },
    { id: 'performance' as TabType, label: 'Performance', icon: '📈' },
    { id: 'settings' as TabType, label: 'Settings', icon: '⚙️' },
  ];

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <h2 className="text-xl font-bold text-gray-900">{strategy.name}</h2>
        <p className="text-sm text-gray-500 mt-1 line-clamp-2">
          {strategy.config?.thesis || strategy.description}
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 overflow-x-auto">
        <div className="flex">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 font-medium text-sm transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-b-2 border-blue-600 text-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <span className="inline-flex items-center gap-2">
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.badge !== undefined && (
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                    activeTab === tab.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {tab.badge}
                  </span>
                )}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'overview' && (
          <OverviewTab strategy={strategy} onGraduate={onGraduate} />
        )}
        {activeTab === 'code' && (
          <CodeTab strategy={strategy} />
        )}
        {activeTab === 'history' && (
          <HistoryTab executions={executions} onRefresh={onRefresh} />
        )}
        {activeTab === 'performance' && (
          <PerformanceTab strategy={strategy} />
        )}
        {activeTab === 'settings' && (
          <SettingsTab
            strategy={strategy}
            onUpdate={onUpdate}
            onDelete={onDelete}
            onGraduate={onGraduate}
          />
        )}
      </div>
    </div>
  );
}
