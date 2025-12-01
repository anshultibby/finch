'use client';

import React, { useState, useEffect } from 'react';
import { chatApi } from '@/lib/api';

interface Chat {
  chat_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  last_message?: string;
}

interface ChatHistorySidebarProps {
  userId: string;
  currentChatId: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export default function ChatHistorySidebar({
  userId,
  currentChatId,
  onSelectChat,
  onNewChat,
  isOpen,
  onToggle,
}: ChatHistorySidebarProps) {
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadChats = async () => {
      if (!userId) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        const response = await chatApi.getUserChats(userId);
        setChats(response.chats);
      } catch (err) {
        console.error('Error loading chats:', err);
        setError('Failed to load chat history');
      } finally {
        setIsLoading(false);
      }
    };

    if (isOpen) {
      loadChats();
    }
  }, [userId, isOpen]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  const getChatTitle = (chat: Chat, index: number) => {
    if (chat.title) return chat.title;
    
    // Generate a title based on date
    const date = new Date(chat.created_at);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    if (isToday) {
      return `Chat ${date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`;
    }
    
    return `Chat ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
  };

  return (
    <div
      className={`h-full bg-white flex-shrink-0 transition-all duration-300 ease-in-out overflow-hidden ${
        isOpen ? 'w-80 border-r border-gray-200 shadow-sm' : 'w-0'
      }`}
    >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-3 border-b border-gray-200">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-gray-900">Chats</h2>
              <button
                onClick={onToggle}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title={isOpen ? "Collapse sidebar" : "Expand sidebar"}
              >
                <svg
                  className={`w-4 h-4 text-gray-600 transition-transform ${isOpen ? '' : 'rotate-180'}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
              </button>
            </div>
            
            {/* New Chat Button */}
            <button
              onClick={onNewChat}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors text-sm"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              New Chat
            </button>
          </div>

          {/* Chat List */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="flex space-x-1.5">
                  <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            ) : error ? (
              <div className="p-4 text-center text-red-600 text-xs">{error}</div>
            ) : chats.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                <div className="text-2xl mb-2">💬</div>
                <p className="text-sm font-medium text-gray-700">No chats yet</p>
                <p className="text-xs mt-1 text-gray-500">Start a new conversation!</p>
              </div>
            ) : (
              <div className="py-2">
                {chats.map((chat, index) => {
                  const isActive = chat.chat_id === currentChatId;
                  
                  return (
                    <button
                      key={chat.chat_id}
                      onClick={() => onSelectChat(chat.chat_id)}
                      className={`w-full text-left px-4 py-2.5 transition-colors ${
                        isActive
                          ? 'bg-purple-100 hover:bg-purple-100'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p
                              className={`text-sm font-medium truncate ${
                                isActive ? 'text-purple-900' : 'text-gray-900'
                              }`}
                            >
                              {getChatTitle(chat, index)}
                            </p>
                            <p className="text-xs text-gray-400 flex-shrink-0">
                              {formatDate(chat.updated_at)}
                            </p>
                          </div>
                          {chat.last_message && (
                            <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed">
                              {chat.last_message}
                            </p>
                          )}
                        </div>
                        {isActive && (
                          <div className="flex-shrink-0 mt-1">
                            <div className="w-1.5 h-1.5 bg-purple-600 rounded-full"></div>
                          </div>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center">
              {chats.length} {chats.length === 1 ? 'chat' : 'chats'}
            </p>
          </div>
        </div>
    </div>
  );
}

