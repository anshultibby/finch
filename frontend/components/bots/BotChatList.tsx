'use client';

import React from 'react';
import type { BotChat } from '@/lib/types';

export type BotPanel = 'chat' | 'strategy' | 'memory' | 'journal' | 'positions' | 'trades';

interface BotChatListProps {
  chats: BotChat[];
  activeChatId: string | null;
  activePanel: BotPanel;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  onSelectPanel: (panel: BotPanel) => void;
  loading?: boolean;
  hasStrategy?: boolean;
  hasMemory?: boolean;
  hasJournal?: boolean;
  hasPositions?: boolean;
  hasTrades?: boolean;
}

const NAV_ITEMS: { panel: BotPanel; icon: React.ReactNode; label: string }[] = [
  {
    panel: 'strategy',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    ),
    label: 'Strategy',
  },
  {
    panel: 'memory',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
      </svg>
    ),
    label: 'Memory',
  },
  {
    panel: 'positions',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
      </svg>
    ),
    label: 'Positions',
  },
  {
    panel: 'trades',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 3M21 7.5H7.5" />
      </svg>
    ),
    label: 'Trades',
  },
  {
    panel: 'journal',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
      </svg>
    ),
    label: 'Journal',
  },
];

export default function BotChatList({
  chats, activeChatId, activePanel, onSelectChat, onNewChat, onSelectPanel, loading, hasStrategy, hasMemory, hasJournal, hasPositions, hasTrades,
}: BotChatListProps) {
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    if (isToday) return 'Today';
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const hasDot = (panel: BotPanel) => {
    if (panel === 'strategy') return hasStrategy;
    if (panel === 'memory') return hasMemory;
    if (panel === 'journal') return hasJournal;
    if (panel === 'positions') return hasPositions;
    if (panel === 'trades') return hasTrades;
    return false;
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 border-r border-gray-200">
      {/* Nav items */}
      <div className="px-3 pt-3 pb-1 space-y-0.5">
        {NAV_ITEMS.map(({ panel, icon, label }) => (
          <button
            key={panel}
            onClick={() => onSelectPanel(panel)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 text-[13px] rounded-lg transition-colors ${
              activePanel === panel
                ? 'bg-white text-gray-900 font-medium shadow-sm border border-gray-100'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
            }`}
          >
            <span className={activePanel === panel ? 'text-gray-700' : 'text-gray-400'}>{icon}</span>
            {label}
            {hasDot(panel) && (
              <span className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400" />
            )}
          </button>
        ))}
      </div>

      <div className="mx-3 my-2 border-t border-gray-200" />

      {/* New Chat button */}
      <div className="px-3 pb-2">
        <button
          onClick={() => { onNewChat(); onSelectPanel('chat'); }}
          className={`w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${
            activePanel === 'chat'
              ? 'text-gray-600 bg-white border-gray-200 hover:bg-gray-50'
              : 'text-gray-500 bg-transparent border-transparent hover:bg-gray-100'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Chat
        </button>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 flex justify-center">
            <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-400 rounded-full animate-spin" />
          </div>
        ) : chats.length === 0 ? (
          <p className="p-4 text-xs text-gray-400 text-center">No chats yet</p>
        ) : (
          <div className="py-1">
            {chats.map((chat) => (
              <button
                key={chat.chat_id}
                onClick={() => { onSelectChat(chat.chat_id); onSelectPanel('chat'); }}
                className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${
                  activePanel === 'chat' && activeChatId === chat.chat_id
                    ? 'bg-white border-r-2 border-blue-500 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <div className="truncate font-medium">
                  {chat.title || 'Untitled chat'}
                </div>
                <div className="text-xs text-gray-400 mt-0.5">
                  {formatDate(chat.updated_at || chat.created_at)}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
