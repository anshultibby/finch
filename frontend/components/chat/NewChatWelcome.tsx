'use client';

import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { TLH_PROMPT, PORTFOLIO_REVIEW_PROMPT, RESEARCH_STOCK_PROMPT } from '@/lib/aiPrompts';

interface QuickAction {
  label: string;
  description: string;
  prompt: string;
  accent: 'emerald' | 'violet' | 'gray';
  icon: React.ReactNode;
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    label: 'Tax-loss harvesting',
    description: 'Find tax savings in my portfolio',
    accent: 'emerald',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
      </svg>
    ),
    prompt: TLH_PROMPT,
  },
  {
    label: 'Portfolio review',
    description: 'Analyze my holdings and risks',
    accent: 'violet',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5V6Z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13.5 10.5H21A7.5 7.5 0 0 0 13.5 3v7.5Z" />
      </svg>
    ),
    prompt: PORTFOLIO_REVIEW_PROMPT,
  },
  {
    label: 'Research a stock',
    description: 'Get the AI take on any ticker',
    accent: 'gray',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
    ),
    prompt: RESEARCH_STOCK_PROMPT,
  },
];

const QUICK_ACTION_STYLES: Record<QuickAction['accent'], { bg: string; iconBg: string; iconText: string; hover: string }> = {
  emerald: { bg: 'bg-emerald-50',  iconBg: 'bg-emerald-500/15', iconText: 'text-emerald-600', hover: 'hover:bg-emerald-100/70' },
  violet:  { bg: 'bg-violet-50',   iconBg: 'bg-violet-500/15',  iconText: 'text-violet-600',  hover: 'hover:bg-violet-100/70' },
  gray:    { bg: 'bg-gray-50',     iconBg: 'bg-gray-500/15',    iconText: 'text-gray-600',    hover: 'hover:bg-gray-100' },
};

interface NewChatWelcomeProps {
  onSendMessage: (message: string, images?: any[], skills?: string[]) => void;
  disabled?: boolean;
  prefillMessage?: string;
  prefillLabel?: string;
}

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
        // Place cursor at end
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

  // ─── Prefilled mode: compact header + editable prompt + Run button ───────
  if (prefillMessage) {
    return (
      <div className="flex flex-col h-full px-5 pt-6 pb-4">
        <div className="mb-3">
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Ready to run</div>
          <h1 className="text-xl font-bold text-gray-900 leading-tight">
            {prefillLabel || 'Send your message'}
          </h1>
          <p className="text-[12px] text-gray-400 mt-1">Edit if you want, then hit Run.</p>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm focus-within:border-gray-300 focus-within:shadow-md transition-all">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => {
              setMessage(e.target.value);
              const t = e.target;
              t.style.height = 'auto';
              t.style.height = Math.min(t.scrollHeight, 220) + 'px';
            }}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={3}
            autoFocus
            className="w-full resize-none bg-transparent px-4 py-3 text-gray-900 placeholder-gray-400 focus:outline-none text-[14px] leading-relaxed disabled:cursor-not-allowed"
            style={{ minHeight: '88px', maxHeight: '220px' }}
          />
          <div className="flex items-center justify-between px-3 py-2 border-t border-gray-100">
            <span className="text-[11px] text-gray-400">⌘↵ to run</span>
            <button
              onClick={handleSubmit}
              disabled={disabled || !message.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-200 disabled:text-gray-400 text-white rounded-xl font-semibold text-[13px] transition-colors shadow-sm"
            >
              Run
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── Empty mode: centered welcome + compact horizontal quick actions + input ──
  return (
    <div className="flex flex-col h-full px-5 py-6">
      <div className="flex-1 flex flex-col justify-center max-w-2xl w-full mx-auto">
        <div className="text-center mb-6">
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">AI Assistant</div>
          <h1 className="text-2xl font-bold text-gray-900 leading-tight">How can I help?</h1>
          <p className="text-[13px] text-gray-400 mt-1.5">Pick a quick action or ask anything about your portfolio.</p>
        </div>

        {/* Compact horizontal quick actions */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          {QUICK_ACTIONS.map((action) => {
            const s = QUICK_ACTION_STYLES[action.accent];
            return (
              <button
                key={action.label}
                onClick={() => {
                  if (disabled) return;
                  setMessage(action.prompt);
                  setTimeout(() => {
                    const t = textareaRef.current;
                    if (!t) return;
                    t.focus();
                    t.style.height = 'auto';
                    t.style.height = Math.min(t.scrollHeight, 180) + 'px';
                    t.setSelectionRange(t.value.length, t.value.length);
                  }, 50);
                }}
                disabled={disabled}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left transition-all ${s.bg} ${s.hover} disabled:opacity-50`}
              >
                <div className={`w-7 h-7 rounded-lg ${s.iconBg} ${s.iconText} flex items-center justify-center flex-shrink-0`}>
                  {action.icon}
                </div>
                <div className="text-[12px] font-semibold text-gray-900 leading-tight truncate">{action.label}</div>
              </button>
            );
          })}
        </div>

        {/* Free-form input */}
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm focus-within:border-gray-300 focus-within:shadow-md transition-all">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => {
              setMessage(e.target.value);
              const t = e.target;
              t.style.height = 'auto';
              t.style.height = Math.min(t.scrollHeight, 180) + 'px';
            }}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            disabled={disabled}
            rows={2}
            className="w-full resize-none bg-transparent px-4 py-3 text-gray-900 placeholder-gray-400 focus:outline-none text-[14px] leading-relaxed disabled:cursor-not-allowed"
            style={{ minHeight: '64px', maxHeight: '180px' }}
          />
          <div className="flex items-center justify-between px-3 py-2 border-t border-gray-100">
            <span className="text-[11px] text-gray-400">⌘↵ to send</span>
            <button
              onClick={handleSubmit}
              disabled={disabled || !message.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-200 disabled:text-gray-400 text-white rounded-xl font-semibold text-[13px] transition-colors shadow-sm"
            >
              Send
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
