'use client';

import React, { forwardRef, useImperativeHandle, useState, useEffect, useCallback, useRef } from 'react';
import { chatApi } from '@/lib/api';
import ProfileDropdown from '../ProfileDropdown';

export type SidebarPanel = 'chat' | 'files' | 'charts' | 'portfolio' | 'skills';

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
    id: 'files',
    label: 'Files',
    icon: (
      <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
      </svg>
    ),
  },
  {
    id: 'charts',
    label: 'Charts',
    icon: (
      <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
      </svg>
    ),
  },
  {
    id: 'portfolio',
    label: 'Portfolio',
    icon: (
      <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    id: 'skills',
    label: 'Skills',
    icon: (
      <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
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
  const [chatsCollapsed, setChatsCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchActive, setSearchActive] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    if (searchActive) searchInputRef.current?.focus();
  }, [searchActive]);

  const filteredChats = searchQuery
    ? chats.filter(c => (c.title || 'New Chat').toLowerCase().includes(searchQuery.toLowerCase()))
    : chats;

  return (
    <div className={`h-full bg-gray-50 border-r border-gray-200 flex flex-col flex-shrink-0 transition-all duration-200 ${expanded ? 'w-64' : 'w-14'}`}>
      {/* Header: logo + collapse toggle */}
      <div className={`flex items-center py-3 px-3 flex-shrink-0 ${expanded ? 'justify-between' : 'justify-center'}`}>
        {expanded && (
          <span className="text-gray-800 font-semibold text-sm tracking-wide select-none">Finch</span>
        )}
        <button
          onClick={() => setExpanded(e => !e)}
          className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-400 hover:text-gray-600 transition-colors"
          title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {/* ChatGPT-style panel toggle icon */}
          <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <rect x="3" y="3" width="18" height="18" rx="2" strokeWidth={1.8} />
            <path strokeLinecap="round" strokeWidth={1.8} d="M9 3v18" />
          </svg>
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto min-h-0">

        {/* New Chat */}
        <div className="px-2 mb-0.5">
          <button
            onClick={onNewChat}
            className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors ${expanded ? '' : 'justify-center'}`}
            title={!expanded ? 'New Chat' : undefined}
          >
            <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            {expanded && <span className="font-medium">New chat</span>}
          </button>
        </div>

        {/* Search Chats */}
        <div className="px-2 mb-1">
          {searchActive && expanded ? (
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg border border-gray-200 bg-white">
              <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search chats…"
                className="flex-1 text-sm bg-transparent outline-none text-gray-900 placeholder-gray-400"
                onBlur={() => { if (!searchQuery) setSearchActive(false); }}
                onKeyDown={e => { if (e.key === 'Escape') { setSearchActive(false); setSearchQuery(''); } }}
              />
              {searchQuery && (
                <button onClick={() => { setSearchQuery(''); setSearchActive(false); }} className="text-gray-400 hover:text-gray-600">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          ) : (
            <button
              onClick={() => { setSearchActive(true); setChatsCollapsed(false); }}
              className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors ${expanded ? '' : 'justify-center'}`}
              title={!expanded ? 'Search Chats' : undefined}
            >
              <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              {expanded && <span className="font-medium">Search chats</span>}
            </button>
          )}
        </div>

        {/* Divider */}
        <div className="mx-3 mb-1 border-t border-gray-200" />

        {/* Nav items */}
        <nav className="px-2 space-y-0.5 mb-2">
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

        {/* Divider */}
        <div className="mx-3 mb-1 border-t border-gray-200" />

        {/* Recent Chats */}
        <div className="pb-2">
          {expanded && (
            <button
              onClick={() => setChatsCollapsed(c => !c)}
              className="w-full flex items-center justify-between px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-600 transition-colors"
            >
              <span>Recent Chats</span>
              <svg
                className={`w-3 h-3 transition-transform ${chatsCollapsed ? '' : 'rotate-90'}`}
                fill="currentColor" viewBox="0 0 20 20"
              >
                <path fillRule="evenodd" d="M7.293 4.707a1 1 0 010 1.414L3.414 10l3.879 3.879a1 1 0 01-1.414 1.414l-4.586-4.586a1 1 0 010-1.414l4.586-4.586a1 1 0 011.414 0z" clipRule="evenodd" transform="rotate(180 10 10)" />
              </svg>
            </button>
          )}

          {!chatsCollapsed && (
            <div className="px-2 space-y-0.5 mt-0.5">
              {isLoading && chats.length === 0 ? (
                <div className="flex justify-center py-6">
                  <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin" />
                </div>
              ) : (
                <>
                  {isCreatingChat && (
                    <div className={`flex items-center gap-2.5 px-2 py-2 rounded-lg bg-blue-50/50 border border-blue-100 ${expanded ? '' : 'justify-center'}`}>
                      <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin flex-shrink-0" />
                      {expanded && <span className="text-xs text-blue-600">Creating chat…</span>}
                    </div>
                  )}
                  {filteredChats.map(chat => {
                    const isActive = chat.chat_id === currentChatId;
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
                  {searchQuery && filteredChats.length === 0 && expanded && (
                    <p className="text-xs text-gray-400 text-center py-4">No chats match "{searchQuery}"</p>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Profile pinned at bottom */}
      <div className={`flex-shrink-0 border-t border-gray-200 px-2 py-2 ${expanded ? '' : 'flex justify-center'}`}>
        <ProfileDropdown collapsed={!expanded} />
      </div>
    </div>
  );
});

AppSidebar.displayName = 'AppSidebar';
export default AppSidebar;
