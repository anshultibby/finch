'use client';

import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';

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
  prefillMessage?: string;
}

export default function NewChatWelcome({ onSendMessage, disabled = false, prefillMessage }: NewChatWelcomeProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (prefillMessage) {
      setMessage(prefillMessage);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [prefillMessage]);

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
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-gray-900 to-gray-700 flex items-center justify-center mx-auto mb-6 shadow-lg shadow-gray-900/10">
          <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
        </div>
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight">
          What can I do for you?
        </h1>
        <p className="text-gray-400 mt-3 text-[15px]">Ask anything about markets, trading, or your portfolio</p>
      </div>

      {/* Input */}
      <div className="w-full max-w-2xl mb-8">
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm hover:shadow-md focus-within:shadow-md focus-within:border-gray-300 transition-all duration-300">
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
              className="flex items-center justify-center w-9 h-9 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:bg-gray-200 disabled:cursor-not-allowed transition-all duration-200 flex-shrink-0 shadow-sm"
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
        {ACTION_PILLS.map((pill, i) => (
          <button
            key={pill.label}
            onClick={() => handlePillClick(pill.prompt)}
            disabled={disabled}
            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-150 rounded-xl text-sm text-gray-600 hover:text-gray-900 hover:border-gray-300 hover:shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 animate-card-in"
            style={{ animationDelay: `${i * 80 + 200}ms` }}
          >
            <span className="text-base">{pill.icon}</span>
            <span className="font-medium">{pill.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
