'use client';

import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { TrendingUp, Scale, Landmark, Trophy, Search, LineChart } from 'lucide-react';

interface NewChatWelcomeProps {
  onSendMessage: (message: string, images?: any[], skills?: string[], files?: any) => void;
  disabled?: boolean;
  prefillMessage?: string;
  prefillLabel?: string;
}

// Example prompts shown as one-click starters. Mirrors the landing page so the
// empty chat feels alive and teaches what Finch can do.
const SUGGESTIONS: { icon: React.ElementType; label: string; prompt: string }[] = [
  { icon: TrendingUp, label: 'Valuation check', prompt: 'Is NVDA overvalued right now?' },
  { icon: Scale, label: 'Compare companies', prompt: 'Compare Apple and Microsoft margins over the last 5 years' },
  { icon: Search, label: 'Insider activity', prompt: 'Which insiders bought their own stock this week?' },
  { icon: Landmark, label: 'Macro & rates', prompt: 'What are prediction markets pricing for the next Fed decision?' },
  { icon: Trophy, label: 'My portfolio', prompt: 'Show me my biggest winners this month' },
  { icon: LineChart, label: 'Build a screen', prompt: 'Find profitable small-cap tech stocks growing revenue over 20%' },
];

export default function NewChatWelcome({ onSendMessage, disabled = false, prefillMessage, prefillLabel }: NewChatWelcomeProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (prefillMessage) {
      setMessage(prefillMessage);
      setTimeout(() => {
        const t = textareaRef.current;
        if (!t) return;
        t.focus();
        t.style.height = 'auto';
        t.style.height = Math.min(t.scrollHeight, 220) + 'px';
        t.setSelectionRange(t.value.length, t.value.length);
      }, 50);
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
    <div className="flex flex-col h-full items-center justify-center px-5">
      <div className="w-full max-w-3xl -mt-20">
        <h1 className="text-4xl font-light text-gray-800 text-center mb-2 tracking-tight">Finch</h1>
        <p className="text-sm text-gray-400 text-center mb-8">Research smarter. Invest better.</p>

        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm focus-within:border-gray-300 focus-within:shadow-md transition-all">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => {
              setMessage(e.target.value);
              const t = e.target;
              t.style.height = 'auto';
              t.style.height = Math.min(t.scrollHeight, 200) + 'px';
            }}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            disabled={disabled}
            rows={2}
            autoFocus
            className="w-full resize-none bg-transparent px-5 py-4 text-gray-900 placeholder-gray-400 focus:outline-none text-[15px] leading-relaxed disabled:cursor-not-allowed"
            style={{ minHeight: '64px', maxHeight: '200px' }}
          />
          <div className="flex items-center justify-end px-3 py-2">
            <button
              onClick={handleSubmit}
              disabled={disabled || !message.trim()}
              className="p-2 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-200 disabled:text-gray-400 text-white rounded-full transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        {/* One-click starters */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {SUGGESTIONS.map(({ icon: Icon, label, prompt }) => (
            <button
              key={label}
              onClick={() => !disabled && onSendMessage(prompt)}
              disabled={disabled}
              className="group flex items-center gap-3 text-left rounded-xl border border-gray-200 bg-white px-4 py-3 transition-all hover:border-emerald-300 hover:shadow-sm hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100 transition-colors">
                <Icon className="w-4 h-4" strokeWidth={2} />
              </span>
              <span className="min-w-0">
                <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400 group-hover:text-emerald-600 transition-colors">{label}</span>
                <span className="block text-[13px] text-gray-700 truncate">{prompt}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
