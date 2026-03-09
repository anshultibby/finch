'use client';

import React, { forwardRef, useImperativeHandle, useState, useEffect, useCallback } from 'react';
import { chatApi } from '@/lib/api';
import ProfileDropdown from '../ProfileDropdown';

export type SidebarPanel = 'chat';

interface Chat {
  chat_id: string;
  title: string | null;
  icon: string | null;
  created_at: string;
  updated_at: string;
}

interface AppSidebarProps {
  userId: string;
  currentChatId: string | null;
  activePanel: SidebarPanel;
  onSelectPanel: (panel: SidebarPanel) => void;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  refreshTrigger?: number;
  isCreatingChat?: boolean;
  activeChatIsLoading?: boolean;
}

export interface AppSidebarRef {
  updateChatTitle: (chatId: string, title: string, icon: string) => void;
}

const NAV_ITEMS: { id: SidebarPanel; label: string; icon: React.ReactNode }[] = [
  {
    id: 'chat',
    label: 'Chats',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
    ),
  },
];

const AppSidebar = forwardRef<AppSidebarRef, AppSidebarProps>(({
  userId,
  currentChatId,
  activePanel,
  onSelectPanel,
  onSelectChat,
  onNewChat,
  refreshTrigger,
  isCreatingChat,
  activeChatIsLoading,
}, ref) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const loadChats = useCallback(async () => {
    if (!userId) return;
    setIsLoading(true);
    try {
      const response = await chatApi.getUserChats(userId);
      setChats(response.chats || []);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  const updateChatTitle = useCallback((chatId: string, title: string, icon: string) => {
    setChats(prev => {
      const exists = prev.find(c => c.chat_id === chatId);
      if (exists) {
        return prev.map(c => c.chat_id === chatId ? { ...c, title, icon } : c);
      }
      return [{ chat_id: chatId, title, icon, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, ...prev];
    });
  }, []);

  useImperativeHandle(ref, () => ({ updateChatTitle }), [updateChatTitle]);

  useEffect(() => { loadChats(); }, [loadChats, refreshTrigger]);
  useEffect(() => {
    if (currentChatId) {
      const timer = setTimeout(() => loadChats(), 100);
      return () => clearTimeout(timer);
    }
  }, [currentChatId, loadChats]);

    return (
    <div className={`h-full bg-gray-50 border-r border-gray-200 flex flex-col flex-shrink-0 transition-all duration-200 ${expanded ? 'w-64' : 'w-14'}`}>
      {/* Top: logo + collapse toggle */}
      <div className={`flex items-center py-3 px-3 flex-shrink-0 ${expanded ? 'justify-between' : 'justify-center'}`}>
        {expanded && (
          <span className="text-gray-800 font-semibold text-sm tracking-wide select-none">Finch</span>
        )}
        <button
          onClick={() => setExpanded(e => !e)}
          className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-400 hover:text-gray-600 transition-colors"
          title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      {/* New chat — always at top */}
      <div className={`px-2 pb-2 flex-shrink-0 ${expanded ? '' : 'px-1'}`}>
        <button
          onClick={onNewChat}
          title="New Chat"
          className={`w-full flex items-center gap-2 py-2 px-3 rounded-lg bg-white border border-gray-200 shadow-sm hover:bg-gray-50 hover:border-gray-300 transition-colors text-sm font-medium text-gray-700 ${expanded ? '' : 'justify-center px-2'}`}
        >
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          {expanded && <span>New chat</span>}
        </button>

      </div>

      {/* Nav items */}
      <nav className="px-2 space-y-0.5 flex-shrink-0">
        {NAV_ITEMS.map(item => {
          const isActive = activePanel === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectPanel(item.id)}
              title={!expanded ? item.label : undefined}
              className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-white shadow-sm border border-gray-200 text-gray-900'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              } ${expanded ? '' : 'justify-center'}`}
            >
              {item.icon}
              {expanded && <span className="font-medium">{item.label}</span>}
            </button>
          );
        })}
      </nav>

      <div className="flex-1 overflow-y-auto mt-1 px-2 space-y-0.5 min-h-0 pb-1">
        {isLoading && chats.length === 0 ? (
          <div className="flex justify-center py-6">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {/* Creating chat placeholder - appears at top of chat list */}
            {isCreatingChat && (
              <div className={`flex items-center gap-2.5 px-2 py-2 rounded-lg bg-blue-50/50 border border-blue-100 ${expanded ? '' : 'justify-center'}`}>
                <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin flex-shrink-0" />
                {expanded && <span className="text-xs text-blue-600">Creating chat…</span>}
              </div>
            )}

            {chats.map(chat => {
              const isActive = chat.chat_id === currentChatId && activePanel === 'chat';
              const icon = chat.icon || '💬';
              const title = chat.title || 'New Chat';
              const showLoading = isActive && activeChatIsLoading;
              return (
                <button
                  key={chat.chat_id}
                  onClick={() => onSelectChat(chat.chat_id)}
                  title={!expanded ? title : undefined}
                  className={`w-full flex items-center gap-2.5 px-2 py-2 rounded-lg text-sm transition-colors text-left ${
                    isActive
                      ? 'bg-white shadow-sm border border-gray-200 text-gray-900 font-medium'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  } ${expanded ? '' : 'justify-center'}`}
                >
                  <span className="text-base flex-shrink-0">{icon}</span>
                  {expanded && <span className="truncate flex-1">{title}</span>}
                  {showLoading && (
                    <div className="w-3.5 h-3.5 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin flex-shrink-0" />
                  )}
                </button>
              );
            })}
          </>
        )}
      </div>
      {/* Profile / settings at bottom */}
      <div className={`flex-shrink-0 border-t border-gray-200 px-2 py-2 ${expanded ? '' : 'flex justify-center'}`}>
        <ProfileDropdown collapsed={!expanded} />
      </div>
    </div>
  );
});

AppSidebar.displayName = 'AppSidebar';
export default AppSidebar;
