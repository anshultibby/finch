'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatApi } from '@/lib/api';
import type { SharedChat } from '@/lib/types';

export default function SharedChatPage() {
  const { token } = useParams<{ token: string }>();
  const [chat, setChat] = useState<SharedChat | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    chatApi
      .getSharedChat(token)
      .then(setChat)
      .catch(() => setError('This chat is not available or has been unshared.'));
  }, [token]);

  if (error) {
    return (
      <div className="min-h-screen bg-[#fafaf9] flex items-center justify-center">
        <div className="text-center">
          <div className="p-4 rounded-2xl bg-gray-100 inline-block mb-4">
            <MessageSquare className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-500 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#fafaf9] flex flex-col">
      {/* Header */}
      <div className="sticky top-0 z-10 flex items-center gap-3 px-4 py-2.5 bg-white border-b border-gray-200">
        <div className="p-1.5 rounded-lg bg-emerald-50">
          <MessageSquare className="w-4 h-4 text-emerald-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-gray-900 truncate">
            {chat ? `${chat.icon ? chat.icon + ' ' : ''}${chat.title || 'Shared chat'}` : 'Loading…'}
          </h1>
          <span className="text-[10px] text-gray-400 font-medium">Read-only shared conversation</span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-gray-400">Shared from Finch</span>
          <a
            href="https://finchapp.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors"
          >
            Try Finch
          </a>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 w-full max-w-3xl mx-auto px-4 py-6 space-y-4">
        {!chat && !error && (
          <div className="flex items-center justify-center py-16">
            <div className="w-5 h-5 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
          </div>
        )}
        {chat?.messages.map((m, i) =>
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
                        {tc.tool_name}
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
        {chat && chat.messages.length === 0 && (
          <p className="text-center text-sm text-gray-400 py-16">This conversation is empty.</p>
        )}
      </div>
    </div>
  );
}
