'use client';

import React from 'react';
import { useNavigation, View } from '@/contexts/NavigationContext';

export default function TabNavigation() {
  const { currentView, navigateTo } = useNavigation();

  const tabs: { id: View; label: string; icon: string; color: string; disabled?: boolean }[] = [
    { id: 'strategies', label: 'Strategies', icon: '📊', color: 'purple' },
    { id: 'chat', label: 'Chat', icon: '💬', color: 'blue' },
    { id: 'files', label: 'Files', icon: '📁', color: 'orange' },
    { id: 'analytics', label: 'Analytics', icon: '📈', color: 'green', disabled: true },
  ];

  const getTabStyles = (tab: typeof tabs[0]) => {
    const isActive = currentView === tab.id;
    
    if (tab.disabled) {
      return 'bg-gray-50 text-gray-400 cursor-not-allowed';
    }
    
    if (isActive) {
      const colorMap = {
        purple: 'bg-gradient-to-br from-purple-600 to-purple-700 text-white shadow-lg shadow-purple-200',
        blue: 'bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-lg shadow-blue-200',
        orange: 'bg-gradient-to-br from-orange-600 to-orange-700 text-white shadow-lg shadow-orange-200',
        green: 'bg-gradient-to-br from-green-600 to-green-700 text-white shadow-lg shadow-green-200',
      };
      return colorMap[tab.color as keyof typeof colorMap];
    }
    
    const hoverMap = {
      purple: 'text-gray-700 hover:text-purple-700 hover:bg-purple-50',
      blue: 'text-gray-700 hover:text-blue-700 hover:bg-blue-50',
      orange: 'text-gray-700 hover:text-orange-700 hover:bg-orange-50',
      green: 'text-gray-700 hover:text-green-700 hover:bg-green-50',
    };
    return `bg-transparent ${hoverMap[tab.color as keyof typeof hoverMap]}`;
  };

  return (
    <div className="inline-flex items-center gap-1 bg-white rounded-lg p-1 shadow-sm border border-gray-200">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => !tab.disabled && navigateTo(tab.id)}
          disabled={tab.disabled}
          className={`
            relative flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs 
            transition-all duration-200 ease-in-out
            ${getTabStyles(tab)}
          `}
        >
          <span className="text-sm">
            {tab.icon}
          </span>
          <span className="whitespace-nowrap">{tab.label}</span>
          {tab.disabled && (
            <span className="ml-0.5 text-[10px] bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded-full font-medium">
              Soon
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

