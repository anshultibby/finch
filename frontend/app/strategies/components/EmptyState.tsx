'use client';

import React from 'react';

const STARTER_PROMPTS = [
  {
    icon: '📋',
    title: 'Copy top traders',
    description: 'Mirror bets from profitable Polymarket traders onto Kalshi',
    prompt: 'Build a strategy that identifies the top 10 profitable sports traders on Polymarket and copies their active bets onto Kalshi. Run every 15 minutes, max $50/trade.',
  },
  {
    icon: '📉',
    title: 'Buy the dip',
    description: 'Buy YES contracts when prices drop below a threshold',
    prompt: 'Build a strategy that monitors Kalshi markets and buys YES contracts when the price drops below 20¢ on markets with high volume. Run hourly, max $30/trade.',
  },
  {
    icon: '📰',
    title: 'Congress trading bot',
    description: 'Trade around congressional stock disclosures',
    prompt: 'Build a strategy that checks for new congressional stock disclosures and places matching bets on related Kalshi prediction markets. Run daily at 9am, max $50/trade.',
  },
  {
    icon: '🏈',
    title: 'Sports momentum',
    description: 'Bet on teams with recent winning streaks',
    prompt: 'Build a strategy that identifies sports teams on winning streaks of 3+ games and places YES bets on their next game on Kalshi. Run daily at 10am, max $25/trade.',
  },
];

interface EmptyStateProps {
  onPromptSelect?: (prompt: string) => void;
}

export function EmptyState({ onPromptSelect }: EmptyStateProps) {
  return (
    <div className="max-w-xl mx-auto py-8">
      <div className="text-center mb-8">
        <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-3 text-2xl">🤖</div>
        <h3 className="text-lg font-semibold text-gray-900 mb-1">No bots yet</h3>
        <p className="text-sm text-gray-500">
          Describe what you want to automate and the AI will build and deploy it.
        </p>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">Start with a template</p>
        {STARTER_PROMPTS.map((item) => (
          <button
            key={item.title}
            onClick={() => onPromptSelect?.(item.prompt)}
            className="w-full text-left bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:bg-blue-50/30 transition-all group"
          >
            <div className="flex items-start gap-3">
              <span className="text-xl flex-shrink-0 mt-0.5">{item.icon}</span>
              <div>
                <div className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                  {item.title}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{item.description}</div>
              </div>
              <span className="ml-auto text-gray-300 group-hover:text-blue-400 transition-colors text-sm self-center flex-shrink-0">→</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
