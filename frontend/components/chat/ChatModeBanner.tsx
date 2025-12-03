'use client';

import React from 'react';
import { useChatMode } from '@/contexts/ChatModeContext';
import { useNavigation } from '@/contexts/NavigationContext';

export default function ChatModeBanner() {
  const { mode, clearMode } = useChatMode();
  const { navigateTo } = useNavigation();

  const handleBack = () => {
    clearMode();
    navigateTo('chat');
  };

  if (mode.type === 'general') {
    return null; // No banner for general chat
  }

  const getBannerContent = () => {
    switch (mode.type) {
      case 'create_strategy':
        return {
          icon: '🎯',
          title: 'Creating New Strategy',
          description: "I'll help you design a trading strategy step by step",
          bgColor: 'from-purple-50 to-indigo-50',
          borderColor: 'border-purple-200',
        };
      
      case 'execute_strategy':
        return {
          icon: '⚡',
          title: `Running: ${mode.metadata?.strategyName || 'Strategy'}`,
          description: 'Executing strategy and screening candidates...',
          bgColor: 'from-blue-50 to-cyan-50',
          borderColor: 'border-blue-200',
        };
      
      case 'edit_strategy':
        return {
          icon: '✏️',
          title: `Editing: ${mode.metadata?.strategyName || 'Strategy'}`,
          description: 'What would you like to modify?',
          bgColor: 'from-amber-50 to-yellow-50',
          borderColor: 'border-amber-200',
        };
      
      case 'analyze_performance':
        return {
          icon: '📊',
          title: 'Analyzing Performance',
          description: 'Deep-diving into your trading patterns and results',
          bgColor: 'from-green-50 to-emerald-50',
          borderColor: 'border-green-200',
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
          Back to Strategies
        </button>
      </div>
    </div>
  );
}

