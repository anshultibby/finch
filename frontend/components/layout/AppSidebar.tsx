'use client';

import React, { forwardRef, useImperativeHandle, useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { chatApi } from '@/lib/api';
import ProfileDropdown from '../ProfileDropdown';

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
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  refreshTrigger?: number;
  isCreatingChat?: boolean;
  activeChatIsLoading?: boolean;
  activePanel: 'chat' | 'portfolio' | 'connections' | 'swaps';
  onSelectPanel: (panel: 'chat' | 'portfolio' | 'connections' | 'swaps') => void;
  pendingSwapCount?: number;
}

export interface AppSidebarRef {
  updateChatTitle: (chatId: string, title: string, icon: string) => void;
}

const AppSidebar = forwardRef<AppSidebarRef, AppSidebarProps>(({
  userId,
  currentChatId,
  onSelectChat,
  onNewChat,
  refreshTrigger,
  isCreatingChat,
  activeChatIsLoading,
  activePanel,
  onSelectPanel,
  pendingSwapCount = 0,
}, ref) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [chatsCollapsed, setChatsCollapsed] = useState(false);
  const [searchModalOpen, setSearchModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
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
    if (searchModalOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 50);
    } else {
      setSearchQuery('');
    }
  }, [searchModalOpen]);

  useEffect(() => {
    if (!searchModalOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setSearchModalOpen(false); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [searchModalOpen]);

  const filteredChats = searchQuery
    ? chats.filter(c => (c.title || 'New Chat').toLowerCase().includes(searchQuery.toLowerCase()))
    : chats;

  const groupChatsByDate = (chatList: Chat[]) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
    const week = new Date(today); week.setDate(today.getDate() - 7);
    const month = new Date(today); month.setDate(today.getDate() - 30);

    const groups: { label: string; chats: Chat[] }[] = [];
    const buckets: Record<string, Chat[]> = { Today: [], Yesterday: [], 'Previous 7 days': [], 'Previous 30 days': [], Older: [] };

    for (const chat of chatList) {
      const d = new Date(chat.updated_at);
      const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      if (day >= today) buckets['Today'].push(chat);
      else if (day >= yesterday) buckets['Yesterday'].push(chat);
      else if (d >= week) buckets['Previous 7 days'].push(chat);
      else if (d >= month) buckets['Previous 30 days'].push(chat);
      else buckets['Older'].push(chat);
    }

    for (const label of ['Today', 'Yesterday', 'Previous 7 days', 'Previous 30 days', 'Older']) {
      if (buckets[label].length > 0) groups.push({ label, chats: buckets[label] });
    }
    return groups;
  };

  return (
    <div className={`h-full bg-gray-50 border-r border-gray-200 flex flex-col flex-shrink-0 transition-all duration-200 ${expanded ? 'w-64' : 'w-14'}`}>
      {/* Header */}
      <div className={`flex items-center py-3 px-3 flex-shrink-0 ${expanded ? 'justify-between' : 'justify-center'}`}>
        {expanded && (
          <span className="text-gray-800 font-semibold text-sm tracking-wide select-none">Finch</span>
        )}
        <button
          onClick={() => setExpanded(e => !e)}
          className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-400 hover:text-gray-600 transition-colors"
          title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
        >
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
          <button
            onClick={() => setSearchModalOpen(true)}
            className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors ${expanded ? '' : 'justify-center'}`}
            title={!expanded ? 'Search Chats' : undefined}
          >
            <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            {expanded && <span className="font-medium">Search chats</span>}
          </button>
        </div>

        {/* Portfolio */}
        <div className="px-2 mb-1">
          <button
            onClick={() => onSelectPanel('portfolio')}
            className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors ${
              activePanel === 'portfolio'
                ? 'bg-white shadow-sm border border-gray-200 text-gray-900'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
            } ${expanded ? '' : 'justify-center'}`}
            title={!expanded ? 'Portfolio' : undefined}
          >
            <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            {expanded && <span className="font-medium">Portfolio</span>}
          </button>
        </div>

        {/* Connections */}
        <div className="px-2 mb-1">
          <button
            onClick={() => onSelectPanel('connections')}
            className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors ${
              activePanel === 'connections'
                ? 'bg-white shadow-sm border border-gray-200 text-gray-900'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
            } ${expanded ? '' : 'justify-center'}`}
            title={!expanded ? 'Connections' : undefined}
          >
            <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
            </svg>
            {expanded && <span className="font-medium">Connections</span>}
          </button>
        </div>

        {/* Opportunities (Swap Cards) */}
        <div className="px-2 mb-1">
          <button
            onClick={() => onSelectPanel('swaps')}
            className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors ${
              activePanel === 'swaps'
                ? 'bg-white shadow-sm border border-gray-200 text-gray-900'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
            } ${expanded ? '' : 'justify-center'}`}
            title={!expanded ? 'Opportunities' : undefined}
          >
            <div className="relative flex-shrink-0">
              <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" />
              </svg>
              {pendingSwapCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                  {pendingSwapCount > 9 ? '9+' : pendingSwapCount}
                </span>
              )}
            </div>
            {expanded && (
              <span className="font-medium flex-1 text-left">Opportunities</span>
            )}
            {expanded && pendingSwapCount > 0 && (
              <span className="text-xs bg-emerald-100 text-emerald-700 font-semibold px-1.5 py-0.5 rounded-full">
                {pendingSwapCount}
              </span>
            )}
          </button>
        </div>

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
                  {chats.map(chat => {
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

      {/* Search Modal */}
      {searchModalOpen && typeof document !== 'undefined' && createPortal(
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh] px-4"
          onClick={(e) => { if (e.target === e.currentTarget) setSearchModalOpen(false); }}
          style={{ background: 'rgba(0,0,0,0.5)' }}
        >
          <div className="w-full max-w-2xl bg-[#2f2f2f] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[75vh]">
            <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
              <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search chats..."
                className="flex-1 bg-transparent outline-none text-white placeholder-gray-500 text-base"
              />
              <button onClick={() => setSearchModalOpen(false)} className="text-gray-500 hover:text-gray-300 transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="overflow-y-auto flex-1">
              {!searchQuery && (
                <button
                  onClick={() => { setSearchModalOpen(false); onNewChat(); }}
                  className="w-full flex items-center gap-3 px-4 py-3 text-gray-200 hover:bg-white/10 transition-colors text-sm"
                >
                  <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  <span>New chat</span>
                </button>
              )}

              {groupChatsByDate(filteredChats).map(group => (
                <div key={group.label}>
                  <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {group.label}
                  </div>
                  {group.chats.map(chat => (
                    <button
                      key={chat.chat_id}
                      onClick={() => { setSearchModalOpen(false); onSelectChat(chat.chat_id); }}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors text-left ${
                        chat.chat_id === currentChatId ? 'bg-white/15 text-white' : 'text-gray-300 hover:bg-white/10'
                      }`}
                    >
                      <svg className="w-4 h-4 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                      </svg>
                      <span className="truncate">{chat.title || 'New Chat'}</span>
                    </button>
                  ))}
                </div>
              ))}

              {filteredChats.length === 0 && searchQuery && (
                <p className="text-sm text-gray-500 text-center py-8">No chats match &ldquo;{searchQuery}&rdquo;</p>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
});

AppSidebar.displayName = 'AppSidebar';
export default AppSidebar;
