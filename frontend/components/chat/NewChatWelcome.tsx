'use client';

import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';

const TLH_PROMPT = `I'd like to find tax loss harvesting opportunities in my portfolio. Please:
1. Check if I have a brokerage account connected, and help me connect one if not
2. Analyze my current holdings for unrealized losses
3. Identify positions where I can harvest losses while maintaining market exposure
4. Show me the best swap candidates and estimated tax savings`;

interface ActionPill {
  icon: string;
  label: string;
  prompt: string;
}

const ACTION_PILLS: ActionPill[] = [
  { icon: '📊', label: 'Review my portfolio', prompt: 'Can you review my current portfolio and give me an overview of my holdings and performance?' },
  { icon: '🔄', label: 'Explain wash sale rules', prompt: 'Can you explain the wash sale rule and how it affects tax loss harvesting?' },
  { icon: '💰', label: 'Estimate my tax savings', prompt: 'Based on my portfolio, what are my potential tax savings from harvesting losses this year?' },
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

  return (
    <div className="flex flex-col items-center justify-center min-h-full px-6 py-16">
      {/* Heading */}
      <div className="mb-10 text-center">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-gray-900 to-gray-700 flex items-center justify-center mx-auto mb-6 shadow-lg shadow-gray-900/10">
          <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight">
          Find your tax losses
        </h1>
        <p className="text-gray-400 mt-3 text-[15px] max-w-md">
          Connect your brokerage, find opportunities to harvest losses, and execute smart swaps — all in one place.
        </p>
      </div>

      {/* Primary CTA */}
      <div className="w-full max-w-2xl mb-6">
        <button
          onClick={() => !disabled && onSendMessage(TLH_PROMPT)}
          disabled={disabled}
          className="w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-300 text-white rounded-2xl font-semibold text-base transition-all duration-200 shadow-sm hover:shadow-md flex items-center justify-center gap-3"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Scan my portfolio for tax losses
        </button>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3 w-full max-w-2xl mb-6">
        <div className="flex-1 border-t border-gray-200" />
        <span className="text-xs text-gray-400 font-medium">or ask something specific</span>
        <div className="flex-1 border-t border-gray-200" />
      </div>

      {/* Custom input */}
      <div className="w-full max-w-2xl mb-6">
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm hover:shadow-md focus-within:shadow-md focus-within:border-gray-300 transition-all duration-300">
          <div className="flex items-end gap-2 px-3 py-3">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your portfolio, tax strategy, or specific positions..."
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

      {/* Quick action pills */}
      <div className="flex flex-wrap justify-center gap-2.5 max-w-xl">
        {ACTION_PILLS.map((pill, i) => (
          <button
            key={pill.label}
            onClick={() => !disabled && onSendMessage(pill.prompt)}
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
