'use client';

import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';

interface NewChatWelcomeProps {
  onSendMessage: (message: string, images?: any[], skills?: string[], files?: any) => void;
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
    <div className="flex flex-col h-full px-5 py-6">
      <div className="flex-1 flex flex-col justify-center max-w-2xl w-full mx-auto">
        {prefillMessage ? (
          <div className="text-sm font-medium text-gray-500 mb-2">
            {prefillLabel || 'Send your message'}
          </div>
        ) : (
          <h1 className="text-xl font-semibold text-gray-900 mb-3">What do you want to know?</h1>
        )}

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
            placeholder="Ask about your portfolio, research a stock, find trades..."
            disabled={disabled}
            rows={2}
            autoFocus
            className="w-full resize-none bg-transparent px-4 py-3 text-gray-900 placeholder-gray-400 focus:outline-none text-[14px] leading-relaxed disabled:cursor-not-allowed"
            style={{ minHeight: '64px', maxHeight: '200px' }}
          />
          <div className="flex items-center justify-end px-3 py-2 border-t border-gray-100">
            <button
              onClick={handleSubmit}
              disabled={disabled || !message.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-200 disabled:text-gray-400 text-white rounded-xl font-semibold text-[13px] transition-colors shadow-sm"
            >
              {prefillMessage ? 'Run' : 'Send'}
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
