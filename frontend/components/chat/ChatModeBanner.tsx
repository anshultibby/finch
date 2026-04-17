'use client';

import React from 'react';
import { useChatMode } from '@/contexts/ChatModeContext';
import { useNavigation } from '@/contexts/NavigationContext';

export default function ChatModeBanner() {
  const { mode, clearMode } = useChatMode();
  const { navigateTo } = useNavigation();

  const handleBack = () => {
    clearMode();
    navigateTo({ type: 'home' });
  };

  if (mode.type === 'general') {
    return null;
  }

  const getBannerContent = () => {
    switch (mode.type) {
      case 'analyze_performance':
        return {
          icon: '📊',
          title: 'Analyzing Performance',
          description: 'Deep-diving into your trading patterns and results',
        };

      default:
        return null;
    }
  };

  const content = getBannerContent();
  if (!content) return null;

  return (
    <div className="border-b border-gray-200 bg-white px-6 py-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{content.icon}</span>
          <h3 className="font-medium text-gray-900 text-sm">
            {content.title}
          </h3>
        </div>

        <button
          onClick={handleBack}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back
        </button>
      </div>
    </div>
  );
}
