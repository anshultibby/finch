'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { memoryApi } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MemorySnapshot {
  id: string;
  chat_id: string | null;
  content: string;
  diff: string | null;
  source: string;
  created_at: string;
}

export default function MemoryPage() {
  const [currentMemory, setCurrentMemory] = useState('');
  const [history, setHistory] = useState<MemorySnapshot[]>([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState<MemorySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'current' | 'history'>('current');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [mem, hist] = await Promise.all([
        memoryApi.getCurrent().catch(() => ({ content: '' })),
        memoryApi.getHistory(30).catch(() => ({ snapshots: [] })),
      ]);
      setCurrentMemory(mem.content || '');
      setHistory(hist.snapshots || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-100">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Memory</h1>
            <p className="text-xs text-gray-400">Powered by Cognee — gets smarter with every conversation</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4 bg-gray-100 rounded-lg p-0.5">
          {(['current', 'history'] as const).map(t => (
            <button key={t} onClick={() => { setTab(t); setSelectedSnapshot(null); }}
              className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${
                tab === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}>
              {t === 'current' ? 'Current Memory' : 'History'}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-violet-300 border-t-violet-600 rounded-full animate-spin" />
          </div>
        ) : tab === 'current' ? (
          <div className="p-6">
            {currentMemory ? (
              <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-600 prose-li:text-gray-600 prose-strong:text-gray-800">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{currentMemory}</ReactMarkdown>
              </div>
            ) : (
              <div className="text-center py-16">
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-gray-500">No memory yet</p>
                <p className="text-xs text-gray-400 mt-1">Start a conversation and Finch will build its memory automatically</p>
              </div>
            )}
          </div>
        ) : selectedSnapshot ? (
          <div className="p-6">
            <button onClick={() => setSelectedSnapshot(null)}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to history
            </button>
            <div className="mb-3">
              <div className="text-xs text-gray-400">{timeAgo(selectedSnapshot.created_at)}</div>
              {selectedSnapshot.diff && (
                <div className="mt-2 px-3 py-2 bg-violet-50 border border-violet-100 rounded-lg text-xs text-violet-700">
                  {selectedSnapshot.diff}
                </div>
              )}
            </div>
            <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-600">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedSnapshot.content}</ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {history.length === 0 ? (
              <div className="text-center py-16">
                <p className="text-sm text-gray-400">No history yet</p>
              </div>
            ) : history.map(snap => (
              <button key={snap.id} onClick={() => setSelectedSnapshot(snap)}
                className="w-full text-left px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-violet-600 bg-violet-50 px-2 py-0.5 rounded-full">
                    {snap.source}
                  </span>
                  <span className="text-xs text-gray-400">{timeAgo(snap.created_at)}</span>
                </div>
                {snap.diff && (
                  <p className="text-sm text-gray-600 line-clamp-2 mt-1">{snap.diff}</p>
                )}
                {snap.chat_id && (
                  <p className="text-xs text-gray-400 mt-1">Chat {snap.chat_id.slice(0, 8)}</p>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
