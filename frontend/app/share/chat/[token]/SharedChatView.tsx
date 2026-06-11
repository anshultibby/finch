'use client';

import { useEffect } from 'react';
import { MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { initAnalytics, track } from '@/lib/analytics';
import type { SharedChat } from '@/lib/types';

export default function SharedChatView({ chat, token }: { chat: SharedChat | null; token: string }) {
  useEffect(() => {
    initAnalytics();
    track('shared_chat_viewed', { token, found: !!chat });
  }, [token, chat]);

  if (!chat) {
    return (
      <div className="min-h-screen bg-[#fafaf9] flex items-center justify-center">
        <div className="text-center">
          <div className="p-4 rounded-2xl bg-gray-100 inline-block mb-4">
            <MessageSquare className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-500 text-sm mb-4">This chat is not available or has been unshared.</p>
          <a
            href="/"
            className="inline-block px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors"
          >
            Try Finch free
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#fafaf9] flex flex-col">
      {/* Header */}
      <div className="sticky top-0 z-10 flex items-center gap-3 px-4 py-2.5 bg-white border-b border-gray-200">
        <img src="/logo.svg" alt="Finch" className="w-7 h-7 rounded-lg" />
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-gray-900 truncate">
            {`${chat.icon ? chat.icon + ' ' : ''}${chat.title || 'Shared chat'}`}
          </h1>
          <span className="text-[10px] text-gray-400 font-medium">
            AI analysis shared from Finch
            {chat.created_at ? ` · ${new Date(chat.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}` : ''}
          </span>
        </div>
        <a
          href="/"
          onClick={() => track('shared_chat_cta_clicked', { placement: 'header' })}
          className="shrink-0 px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors"
        >
          Try Finch
        </a>
      </div>

      {/* Messages */}
      <div className="flex-1 w-full max-w-3xl mx-auto px-4 py-6 pb-28 space-y-4">
        {chat.messages.map((m, i) =>
          m.role === 'user' ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] bg-emerald-600 text-white rounded-2xl rounded-br-md px-4 py-2.5 text-sm whitespace-pre-wrap break-words">
                {m.content}
              </div>
            </div>
          ) : (
            <div key={i} className="flex justify-start">
              <div className="max-w-[90%] bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 text-sm text-gray-800 shadow-sm">
                {m.tool_calls && m.tool_calls.length > 0 && (
                  <div className="mb-2 flex flex-wrap gap-1.5">
                    {m.tool_calls.map((tc, j) => (
                      <span key={j} className="text-[10px] font-medium text-gray-500 bg-gray-100 rounded px-1.5 py-0.5">
                        {tc.statusMessage || tc.tool_name}
                      </span>
                    ))}
                  </div>
                )}
                {m.content && (
                  <div className="prose prose-sm max-w-none prose-p:my-1.5 prose-pre:my-2">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          )
        )}
        {chat.messages.length === 0 && (
          <p className="text-center text-sm text-gray-400 py-16">This conversation is empty.</p>
        )}
      </div>

      {/* CTA banner */}
      <div className="fixed bottom-0 inset-x-0 z-10 bg-white/95 backdrop-blur border-t border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <p className="text-sm text-gray-600 min-w-0">
            <span className="font-medium text-gray-900">Made with Finch</span>
            <span className="hidden sm:inline"> — an AI analyst for your portfolio, watchlist, and daily brief.</span>
          </p>
          <a
            href="/"
            onClick={() => track('shared_chat_cta_clicked', { placement: 'banner' })}
            className="shrink-0 px-4 py-2 text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-full transition-colors"
          >
            Try it free
          </a>
        </div>
      </div>
    </div>
  );
}
