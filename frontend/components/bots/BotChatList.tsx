'use client';

import React from 'react';
import type { BotChat } from '@/lib/types';

interface BotChatListProps {
  chats: BotChat[];
  activeChatId: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
}

export default function BotChatList({ chats, activeChatId, onSelectChat, onNewChat }: BotChatListProps) {
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
    <div className="flex flex-col h-full bg-gray-50 border-r border-gray-200">
      {/* New Chat button */}
      <div className="p-3 border-b border-gray-200">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-600 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Chat
        </button>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto">
        {chats.length === 0 ? (
          <p className="p-4 text-xs text-gray-400 text-center">No chats yet</p>
        ) : (
          <div className="py-1">
            {chats.map((chat) => (
              <button
                key={chat.chat_id}
                onClick={() => onSelectChat(chat.chat_id)}
                className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${
                  activeChatId === chat.chat_id
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
