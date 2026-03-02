'use client';

import React, { useState, KeyboardEvent, useRef } from 'react';

interface ActionPill {
  icon: string;
  label: string;
  prompt: string;
}

const ACTION_PILLS: ActionPill[] = [
  { icon: '📊', label: 'Screen stocks', prompt: 'Help me screen for stocks that match specific criteria' },
  { icon: '📈', label: 'Backtest strategy', prompt: 'Help me backtest an investment strategy' },
  { icon: '💹', label: 'Execute trades', prompt: 'Help me execute trades in my portfolio' },
  { icon: '💡', label: 'Brainstorm ideas', prompt: "Let's brainstorm some investment ideas together" },
];

interface NewChatWelcomeProps {
  onSendMessage: (message: string, images?: any[], skills?: string[]) => void;
  disabled?: boolean;
}

export default function NewChatWelcome({ onSendMessage, disabled = false }: NewChatWelcomeProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handlePillClick = (prompt: string) => {
    if (!disabled) onSendMessage(prompt);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-full px-6 py-16">
      {/* Heading */}
      <div className="mb-10 text-center">
        <div className="w-12 h-12 rounded-2xl bg-primary-600 flex items-center justify-center mx-auto mb-5">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
        </div>
        <h1 className="text-3xl md:text-4xl font-semibold text-gray-900 tracking-tight">
          What can I do for you?
        </h1>
        <p className="text-gray-500 mt-2 text-sm">Ask anything about markets, trading, or your portfolio</p>
      </div>

      {/* Input */}
      <div className="w-full max-w-2xl mb-6">
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm focus-within:border-gray-300 focus-within:shadow-md transition-all">
          {/* Input row */}
          <div className="flex items-end gap-2 px-3 py-3">
            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Assign a task or ask anything..."
              disabled={disabled}
              rows={1}
              autoFocus
              className="flex-1 resize-none bg-transparent py-2 text-gray-900 placeholder-gray-400 focus:outline-none text-base disabled:cursor-not-allowed"
              style={{ minHeight: '24px', maxHeight: '150px', fontSize: '15px' }}
              onInput={(e) => {
                const t = e.target as HTMLTextAreaElement;
                t.style.height = 'auto';
                t.style.height = Math.min(t.scrollHeight, 150) + 'px';
              }}
            />

            {/* Send button */}
            <button
              onClick={handleSubmit}
              disabled={disabled || !message.trim()}
              className="flex items-center justify-center w-8 h-8 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-200 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Action pills */}
      <div className="flex flex-wrap justify-center gap-2.5 max-w-xl">
        {ACTION_PILLS.map((pill) => (
          <button
            key={pill.label}
            onClick={() => handlePillClick(pill.prompt)}
            disabled={disabled}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-700 hover:border-gray-300 hover:shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <span>{pill.icon}</span>
            <span className="font-medium">{pill.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
