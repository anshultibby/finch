'use client';

import React, { useState, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react';
import { chatApi } from '@/lib/api';

interface Chat {
  chat_id: string;
  title: string | null;
  icon: string | null;
  created_at: string;
  updated_at: string;
  last_message?: string;
}

interface ChatHistorySidebarProps {
  userId: string;
  currentChatId: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  isCollapsed: boolean;
  onToggle: () => void;
  refreshTrigger?: number;
  isCreatingChat?: boolean; // True when a new chat is being created + title generated
}

export interface ChatHistorySidebarRef {
  updateChatTitle: (chatId: string, title: string, icon: string) => void;
}

const ChatHistorySidebar = forwardRef<ChatHistorySidebarRef, ChatHistorySidebarProps>(({
  userId,
  currentChatId,
  onSelectChat,
  onNewChat,
  isCollapsed,
  onToggle,
  refreshTrigger,
  isCreatingChat,
}, ref) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadChats = useCallback(async () => {
    if (!userId) return;
    
    setIsLoading(true);
    try {
      const response = await chatApi.getUserChats(userId);
      setChats(response.chats || []);
    } catch (err) {
      console.error('Error loading chats:', err);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  // Update a specific chat's title without full refresh
  const updateChatTitle = useCallback((chatId: string, title: string, icon: string) => {
    setChats(prevChats => {
      const existingChat = prevChats.find(c => c.chat_id === chatId);
      if (existingChat) {
        // Update existing chat
        return prevChats.map(chat => 
          chat.chat_id === chatId 
            ? { ...chat, title, icon }
            : chat
        );
      } else {
        // Add new chat at the top
        return [{
          chat_id: chatId,
          title,
          icon,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }, ...prevChats];
      }
    });
  }, []);

  // Expose updateChatTitle to parent via ref
  useImperativeHandle(ref, () => ({
    updateChatTitle,
  }), [updateChatTitle]);

  // Load chats on mount and when refresh trigger changes
  useEffect(() => {
    loadChats();
  }, [loadChats, refreshTrigger]);

  // Also reload when currentChatId changes (ensures new chats appear)
  useEffect(() => {
    if (currentChatId) {
      // Small delay to let backend save the chat
      const timer = setTimeout(() => {
        loadChats();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [currentChatId, loadChats]);

  const getChatTitle = (chat: Chat) => {
    return chat.title || 'New Chat';
  };

  const getChatIcon = (chat: Chat) => {
    return chat.icon || '💬';
  };

  const renderChatItem = (chat: Chat) => {
    const isActive = chat.chat_id === currentChatId;
    
    if (isCollapsed) {
      return (
        <button
          key={chat.chat_id}
          onClick={() => onSelectChat(chat.chat_id)}
          className={`w-10 h-10 flex items-center justify-center rounded-lg transition-all duration-150 text-lg ${
            isActive
              ? 'bg-white shadow-sm border border-gray-200'
              : 'hover:bg-gray-100'
          }`}
          title={getChatTitle(chat)}
        >
          {getChatIcon(chat)}
        </button>
      );
    }

    return (
      <button
        key={chat.chat_id}
        onClick={() => onSelectChat(chat.chat_id)}
        title={getChatTitle(chat)}
        className={`w-full text-left rounded-lg transition-all duration-150 px-3 py-2 group ${
          isActive
            ? 'bg-white shadow-sm border border-gray-200'
            : 'hover:bg-gray-100'
        }`}
      >
        <div className="flex items-center gap-2.5">
          <span className="text-base flex-shrink-0">{getChatIcon(chat)}</span>
          <span className={`text-sm truncate ${isActive ? 'text-gray-900 font-medium' : 'text-gray-600'}`}>
            {getChatTitle(chat)}
          </span>
        </div>
      </button>
    );
  };

  return (
    <div
      className={`h-full bg-gray-50 flex-shrink-0 transition-all duration-200 ease-out border-r border-gray-200 flex flex-col ${
        isCollapsed ? 'w-[60px]' : 'w-64'
      }`}
    >
      {/* Header */}
      <div className={`flex items-center p-3 ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
        {!isCollapsed && (
          <span className="text-sm font-semibold text-gray-700">Chats</span>
        )}
        <button
          onClick={onToggle}
          className="p-1.5 hover:bg-gray-200 rounded-md transition-colors"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isCollapsed ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* New Chat Button */}
      <div className={`px-2 pb-3 ${isCollapsed ? 'px-[10px]' : ''}`}>
        <button
          onClick={onNewChat}
          className={`flex items-center gap-2 w-full bg-white hover:bg-gray-100 border border-gray-200 rounded-lg transition-all text-sm font-medium text-gray-700 ${
            isCollapsed ? 'justify-center p-2.5' : 'px-3 py-2.5'
          }`}
          title="New Chat"
        >
          <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          {!isCollapsed && <span>New Chat</span>}
        </button>
      </div>

      {/* Chat List */}
      <div className={`flex-1 overflow-y-auto ${isCollapsed ? 'px-[10px]' : 'px-2'}`}>
        {/* Show creating chat spinner at top when generating title */}
        {isCreatingChat && (
          <div className={`mb-1 ${isCollapsed ? '' : ''}`}>
            {isCollapsed ? (
              <div className="w-10 h-10 flex items-center justify-center rounded-lg bg-blue-50 border border-blue-200">
                <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
              </div>
            ) : (
              <div className="w-full rounded-lg bg-blue-50 border border-blue-200 px-3 py-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin flex-shrink-0" />
                  <span className="text-sm text-blue-600">Creating chat...</span>
                </div>
              </div>
            )}
          </div>
        )}
        
        {isLoading && chats.length === 0 && !isCreatingChat ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
          </div>
        ) : chats.length === 0 && !isCreatingChat ? (
          <div className={`text-center py-8 ${isCollapsed ? 'px-1' : 'px-4'}`}>
            {!isCollapsed && (
              <>
                <div className="text-2xl mb-2">💬</div>
                <p className="text-xs text-gray-500">No chats yet</p>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-0.5">
            {chats.map(renderChatItem)}
          </div>
        )}
      </div>

    </div>
  );
});

ChatHistorySidebar.displayName = 'ChatHistorySidebar';

export default ChatHistorySidebar;
