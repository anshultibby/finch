'use client';

import React from 'react';
import type { BotChat, BotWakeup } from '@/lib/types';

export type BotPanel = 'chat' | 'strategy' | 'memory' | 'journal' | 'positions' | 'trades' | 'files';

interface BotChatListProps {
  chats: BotChat[];
  activeChatId: string | null;
  activePanel: BotPanel;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  onSelectPanel: (panel: BotPanel) => void;
  loading?: boolean;
  hasPositions?: boolean;
  hasTrades?: boolean;
  wakeups?: BotWakeup[];
}

const NAV_ITEMS: { panel: BotPanel; icon: React.ReactNode; label: string }[] = [
  {
    panel: 'positions',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
      </svg>
    ),
    label: 'Positions',
  },
  {
    panel: 'trades',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 3M21 7.5H7.5" />
      </svg>
    ),
    label: 'Trades',
  },
  {
    panel: 'files',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
      </svg>
    ),
    label: 'Files',
  },
];

export default function BotChatList({
  chats, activeChatId, activePanel, onSelectChat, onNewChat, onSelectPanel, loading, wakeups = [],
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

  return (
    <div className="h-full overflow-y-auto bg-gray-50 border-r border-gray-200">
      {/* New Chat */}
      <div className="px-2 pt-3 pb-1">
        <button
          onClick={() => { onNewChat(); onSelectPanel('chat'); }}
          className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
          </svg>
          New chat
        </button>
      </div>

      {/* Nav items */}
      <div className="px-2 py-1">
        {NAV_ITEMS.map(({ panel, icon, label }) => (
          <button
            key={panel}
            onClick={() => onSelectPanel(panel)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors ${
              activePanel === panel
                ? 'bg-gray-200/70 text-gray-900 font-medium'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <span className={activePanel === panel ? 'text-gray-700' : 'text-gray-400'}>{icon}</span>
            {label}
          </button>
        ))}
      </div>

      {/* Scheduled wakeups */}
      {wakeups.length > 0 && (
        <div className="px-2 pt-3 pb-1">
          <div className="text-xs font-medium text-gray-400 px-3 mb-1">
            Scheduled
          </div>
          <div className="space-y-0.5">
            {wakeups.map((w) => {
              const t = new Date(w.trigger_at);
              const now = new Date();
              const diffMs = t.getTime() - now.getTime();
              const diffMins = Math.round(diffMs / 60000);
              let timeLabel: string;
              if (diffMins < 0) {
                timeLabel = 'overdue';
              } else if (diffMins < 60) {
                timeLabel = `in ${diffMins}m`;
              } else if (diffMins < 1440) {
                timeLabel = `in ${Math.round(diffMins / 60)}h`;
              } else {
                timeLabel = t.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
              }
              return (
                <div
                  key={w.id}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg bg-amber-50/80"
                >
                  <svg className="w-5 h-5 text-amber-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                  </svg>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-gray-700 truncate">
                      {w.reason || w.trigger_type}
                    </div>
                    <div className="text-xs text-amber-600 font-medium">
                      {timeLabel}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Chats — exclude auto-generated wakeup chats */}
      <div className="px-2 pt-4 pb-1">
        <div className="text-xs font-medium text-gray-400 px-3 mb-1">
          Chats
        </div>
        {loading ? (
          <div className="py-4 flex justify-center">
            <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-400 rounded-full animate-spin" />
          </div>
        ) : chats.filter((c) => !c.title?.startsWith('Wakeup:')).length === 0 ? (
          <p className="px-3 py-3 text-sm text-gray-400">No chats yet</p>
        ) : (
          <div className="space-y-0.5">
            {chats.filter((c) => !c.title?.startsWith('Wakeup:')).map((chat) => (
              <button
                key={chat.chat_id}
                onClick={() => { onSelectChat(chat.chat_id); onSelectPanel('chat'); }}
                className={`w-full text-left px-3 py-2.5 text-sm rounded-lg transition-colors ${
                  activePanel === 'chat' && activeChatId === chat.chat_id
                    ? 'bg-gray-200/70 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <div className="truncate">
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
