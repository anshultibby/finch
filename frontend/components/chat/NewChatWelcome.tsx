'use client';

import React, { useState, KeyboardEvent } from 'react';

interface ActionPill {
  icon: string;
  label: string;
  prompt: string;
}

const ACTION_PILLS: ActionPill[] = [
  { icon: '📊', label: 'Screen stocks', prompt: 'Help me screen for stocks that match specific criteria' },
  { icon: '📈', label: 'Backtest strategy', prompt: 'Help me backtest an investment strategy' },
  { icon: '💹', label: 'Execute trades', prompt: 'Help me execute trades in my portfolio' },
  { icon: '💡', label: 'Brainstorm ideas', prompt: 'Let\'s brainstorm some investment ideas together' },
];

interface NewChatWelcomeProps {
  onSendMessage: (message: string, images?: any[]) => void;
  disabled?: boolean;
}

export default function NewChatWelcome({ onSendMessage, disabled = false }: NewChatWelcomeProps) {
  const [message, setMessage] = useState('');

  const handleSubmit = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handlePillClick = (pill: ActionPill) => {
    if (!disabled) {
      onSendMessage(pill.prompt);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12">
      {/* Main heading */}
      <h1 className="text-4xl md:text-5xl font-serif font-medium text-gray-900 mb-12 text-center tracking-tight">
        What can I do for you?
      </h1>

      {/* Input container */}
      <div className="w-full max-w-2xl mb-8">
        <div className="relative bg-gray-50 border border-gray-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow duration-200">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Assign a task or ask anything"
            disabled={disabled}
            rows={1}
            className="w-full resize-none bg-transparent px-5 py-4 pr-14 text-gray-900 placeholder-gray-400 focus:outline-none text-lg"
            style={{ minHeight: '60px', maxHeight: '150px' }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = Math.min(target.scrollHeight, 150) + 'px';
            }}
          />
          
          {/* Send button */}
          <button
            onClick={handleSubmit}
            disabled={disabled || !message.trim()}
            className="absolute right-3 bottom-3 w-10 h-10 flex items-center justify-center rounded-full bg-gray-800 text-white hover:bg-gray-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all duration-200"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          </button>
        </div>
      </div>

      {/* Action pills */}
      <div className="flex flex-wrap justify-center gap-3 max-w-2xl">
        {ACTION_PILLS.map((pill) => (
          <button
            key={pill.label}
            onClick={() => handlePillClick(pill)}
            disabled={disabled}
            className="group flex items-center gap-2 px-5 py-3 bg-white border border-gray-200 rounded-full hover:border-gray-400 hover:shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          >
            <span className="text-lg">{pill.icon}</span>
            <span className="text-gray-700 font-medium text-sm">{pill.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

