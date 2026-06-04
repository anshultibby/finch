'use client';

import React, { forwardRef, useImperativeHandle, useState, useEffect, useCallback, useRef } from 'react';
import { chatApi } from '@/lib/api';
import ProfileDropdown from '../ProfileDropdown';
import ChatItemMenu from '@/components/chat/ChatItemMenu';
import FinchLogo from '@/components/shared/FinchLogo';
import type { View } from '@/contexts/NavigationContext';
import { useCredits } from '@/contexts/CreditsContext';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface Chat {
  chat_id: string;
  title: string | null;
  icon: string | null;
  created_at: string;
  updated_at: string;
  is_public?: boolean;
  share_token?: string | null;
}

interface AppSidebarProps {
  userId: string;
  currentView: View;
  onNavigate: (view: View) => void;
  currentChatId: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  refreshTrigger?: number;
  isCreatingChat?: boolean;
  isStreamingChat?: boolean;
}

export interface AppSidebarRef {
  updateChatTitle: (chatId: string, title: string, icon: string) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Nav items config
// ─────────────────────────────────────────────────────────────────────────────

interface NavItem {
  id: string;
  label: string;
  view: View;
  icon: React.ReactNode;
  mobileNav?: boolean; // show in bottom nav on mobile
}

const HomeIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
  </svg>
);

const SearchIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const AgentPortfolioIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 0 0 2.25-2.25V6.75a2.25 2.25 0 0 0-2.25-2.25H6.75A2.25 2.25 0 0 0 4.5 6.75v10.5a2.25 2.25 0 0 0 2.25 2.25Z" />
  </svg>
);

const WatchlistIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
  </svg>
);

const ScheduledIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 6v6l4 2m6-2a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z" />
  </svg>
);

const ChartsIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
  </svg>
);

const ChatIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 0 1 .778-.332 48.294 48.294 0 0 0 5.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
  </svg>
);

const LinkedAccountsIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Z" />
  </svg>
);

const MemoryStoreIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75m16.5 3.75v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75" />
  </svg>
);

function viewMatch(a: View, b: View): boolean {
  return a.type === b.type;
}

// ─────────────────────────────────────────────────────────────────────────────
// Desktop sidebar
// ─────────────────────────────────────────────────────────────────────────────

const AppSidebar = forwardRef<AppSidebarRef, AppSidebarProps>(({
  userId,
  currentView,
  onNavigate,
  currentChatId,
  onSelectChat,
  onNewChat,
  refreshTrigger,
  isCreatingChat,
  isStreamingChat,
}, ref) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [chatsCollapsed, setChatsCollapsed] = useState(false);
  const { credits, loading: creditsLoading, openModal: openCreditsModal } = useCredits();
  const [searchQuery, setSearchQuery] = useState('');
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const chatListRef = useRef<HTMLDivElement>(null);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const PAGE_SIZE = 30;
  const navItems: NavItem[] = [
    { id: 'home', label: 'Dashboard', view: { type: 'home' }, icon: <HomeIcon /> },
    { id: 'jobs', label: 'Automations', view: { type: 'jobs' }, icon: <ScheduledIcon /> },
    { id: 'visualizations', label: 'Visualizations', view: { type: 'visualizations' }, icon: <ChartsIcon /> },
    { id: 'memory-store', label: 'Memory Store', view: { type: 'memory-store' }, icon: <MemoryStoreIcon /> },
  ];

  const mobileNavItems: NavItem[] = [
    { id: 'home', label: 'Dashboard', view: { type: 'home' }, icon: <HomeIcon />, mobileNav: true },
    { id: 'chat', label: 'Chat', view: { type: 'chat' }, icon: <ChatIcon />, mobileNav: true },
  ];

  const loadChats = useCallback(async (search?: string) => {
    if (!userId) return;
    setIsLoading(true);
    try {
      const response = await chatApi.getUserChats(userId, {
        search: search || undefined,
        limit: PAGE_SIZE,
        offset: 0,
      });
      const fetched = response.chats || [];
      setHasMore(!!response.has_more);
      setChats(prev => {
        const localTitles = new Map(
          prev.filter(c => c.title).map(c => [c.chat_id, c])
        );
        return fetched.map(c =>
          !c.title && localTitles.has(c.chat_id)
            ? { ...c, title: localTitles.get(c.chat_id)!.title, icon: localTitles.get(c.chat_id)!.icon }
            : c
        );
      });
    } catch { /* ignore */ } finally { setIsLoading(false); }
  }, [userId]);

  const loadMoreChats = useCallback(async () => {
    if (!userId || isLoadingMore || !hasMore) return;
    setIsLoadingMore(true);
    try {
      const response = await chatApi.getUserChats(userId, {
        search: searchQuery || undefined,
        limit: PAGE_SIZE,
        offset: chats.length,
      });
      const fetched = response.chats || [];
      setHasMore(!!response.has_more);
      setChats(prev => [...prev, ...fetched]);
    } catch { /* ignore */ } finally { setIsLoadingMore(false); }
  }, [userId, isLoadingMore, hasMore, searchQuery, chats.length]);

  const updateChatTitle = useCallback((chatId: string, title: string, icon: string) => {
    setChats(prev => {
      const exists = prev.find(c => c.chat_id === chatId);
      if (exists) return prev.map(c => c.chat_id === chatId ? { ...c, title, icon } : c);
      return [{ chat_id: chatId, title, icon, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, ...prev];
    });
  }, []);

  const handleRenamed = useCallback((chatId: string, title: string) => {
    setChats(prev => prev.map(c => c.chat_id === chatId ? { ...c, title } : c));
  }, []);

  const handleDeleted = useCallback((chatId: string) => {
    setChats(prev => prev.filter(c => c.chat_id !== chatId));
    // If the active chat was deleted, start a fresh chat so the view isn't stale.
    if (chatId === currentChatId) onNewChat();
  }, [currentChatId, onNewChat]);

  const handleShareChange = useCallback((chatId: string, isPublic: boolean, shareToken: string | null) => {
    setChats(prev => prev.map(c => c.chat_id === chatId ? { ...c, is_public: isPublic, share_token: shareToken } : c));
  }, []);

  useImperativeHandle(ref, () => ({ updateChatTitle }), [updateChatTitle]);

  useEffect(() => { loadChats(searchQuery); }, [loadChats, refreshTrigger]);
  useEffect(() => {
    if (currentChatId) {
      const timer = setTimeout(() => loadChats(searchQuery), 100);
      return () => clearTimeout(timer);
    }
  }, [currentChatId, loadChats]);

  const searchMountRef = useRef(true);
  useEffect(() => {
    if (searchMountRef.current) { searchMountRef.current = false; return; }
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => loadChats(searchQuery), 300);
    return () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current); };
  }, [searchQuery]);

  const handleChatListScroll = useCallback(() => {
    const el = chatListRef.current;
    if (!el || !hasMore || isLoadingMore) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
      loadMoreChats();
    }
  }, [hasMore, isLoadingMore, loadMoreChats]);

  return (
    <>
      {/* Desktop sidebar */}
      <div className={`hidden md:flex h-full bg-gray-50 border-r border-gray-200 flex-col flex-shrink-0 transition-all duration-200 ${expanded ? 'w-52' : 'w-14'}`}>
        {/* Header */}
        <div className={`group/header flex items-center py-3 px-3 flex-shrink-0 ${expanded ? 'justify-between' : 'justify-center'}`}>
          {expanded ? (
            <>
              <FinchLogo size={22} />
              <div className="flex items-center gap-1.5">
                {!creditsLoading && (
                  <button
                    onClick={openCreditsModal}
                    className="flex items-center gap-1 px-2 py-1 rounded-full border border-gray-200 hover:bg-gray-100 transition-colors"
                    title="Credits"
                  >
                    <svg className="w-3.5 h-3.5 text-amber-500" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M6 0L7.2 4.8 12 6 7.2 7.2 6 12 4.8 7.2 0 6 4.8 4.8z" />
                      <path d="M12 9l.7 2.3L15 12l-2.3.7L12 15l-.7-2.3L9 12l2.3-.7z" />
                    </svg>
                    <span className="text-xs font-medium text-gray-700">{credits.toLocaleString()}</span>
                  </button>
                )}
                <button onClick={() => setExpanded(false)}
                  className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-600 hover:text-gray-900 transition-colors"
                  title="Collapse">
                  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <rect x="3" y="3" width="18" height="18" rx="2" strokeWidth={1.8} />
                    <path strokeLinecap="round" strokeWidth={1.8} d="M9 3v18" />
                  </svg>
                </button>
              </div>
            </>
          ) : (
            <button onClick={() => setExpanded(true)} className="relative w-[22px] h-[22px] group/logo">
              <span className="absolute inset-0 flex items-center justify-center group-hover/logo:opacity-0 transition-opacity">
                <FinchLogo size={22} />
              </span>
              <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover/logo:opacity-100 transition-opacity text-gray-600">
                <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <rect x="3" y="3" width="18" height="18" rx="2" strokeWidth={1.8} />
                  <path strokeLinecap="round" strokeWidth={1.8} d="M9 3v18" />
                </svg>
              </span>
            </button>
          )}
        </div>

        {/* Main nav */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="px-2 space-y-0.5 flex-shrink-0">
            {/* New Chat */}
            <button
              onClick={onNewChat}
              className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors ${
                currentView.type === 'chat' ? 'bg-white shadow-sm border border-gray-200 text-gray-900' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              } ${expanded ? '' : 'justify-center'}`}
              title={!expanded ? 'New chat' : undefined}
            >
              <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}>
                <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z" />
              </svg>
              {expanded && <span className="font-medium">New chat</span>}
            </button>

            {navItems.map(item => {
              const active = viewMatch(currentView, item.view);
              return (
                <button key={item.id} onClick={() => onNavigate(item.view)}
                  className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors ${
                    active ? 'bg-white shadow-sm border border-gray-200 text-gray-900' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  } ${expanded ? '' : 'justify-center'}`}
                  title={!expanded ? item.label : undefined}>
                  {item.icon}
                  {expanded && <span className="font-medium">{item.label}</span>}
                </button>
              );
            })}
          </div>

          {/* Divider */}
          <div className="mx-3 my-2 border-t border-gray-200 flex-shrink-0" />

          {/* Chats section — scrollable with search */}
          {expanded && (
            <div className="flex flex-col min-h-0 flex-1 pb-2">
              <button onClick={() => setChatsCollapsed(c => !c)}
                className="w-full flex items-center justify-between px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-600 transition-colors flex-shrink-0">
                <span>Chats</span>
                <svg className={`w-3 h-3 transition-transform ${chatsCollapsed ? '' : 'rotate-90'}`}
                  fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M7.293 4.707a1 1 0 010 1.414L3.414 10l3.879 3.879a1 1 0 01-1.414 1.414l-4.586-4.586a1 1 0 010-1.414l4.586-4.586a1 1 0 011.414 0z" clipRule="evenodd" transform="rotate(180 10 10)" />
                </svg>
              </button>
              {!chatsCollapsed && (
                <>
                  {/* Search input */}
                  <div className="px-2 mb-1 flex-shrink-0">
                    <div className="relative">
                      <svg className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Search chats..."
                        className="w-full pl-7 pr-7 py-1.5 text-xs rounded-md border border-gray-200 bg-white focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 placeholder-gray-400"
                      />
                      {searchQuery && (
                        <button
                          onClick={() => setSearchQuery('')}
                          className="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                        >
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                  {/* Scrollable chat list */}
                  <div
                    ref={chatListRef}
                    onScroll={handleChatListScroll}
                    className="overflow-y-auto min-h-0 flex-1 px-2 space-y-0.5"
                  >
                    {isCreatingChat && (
                      <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg bg-blue-50/50 border border-blue-100">
                        <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin flex-shrink-0" />
                        <span className="text-xs text-blue-600">Creating chat...</span>
                      </div>
                    )}
                    {chats.length === 0 && !isCreatingChat && !isLoading && (
                      <div className="px-2 py-2 text-xs text-gray-400">
                        {searchQuery ? 'No matching chats' : 'No chats yet'}
                      </div>
                    )}
                    {chats.map(chat => {
                      const isActive = chat.chat_id === currentChatId && currentView.type === 'chat';
                      const isChatStreaming = chat.chat_id === currentChatId && isStreamingChat;
                      return (
                        <div key={chat.chat_id}
                          className={`group relative flex items-center gap-1 rounded-lg text-sm transition-colors ${
                            isActive ? 'bg-white shadow-sm border border-gray-200 text-gray-900 font-medium' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                          }`}>
                          <button onClick={() => onSelectChat(chat.chat_id)}
                            className="flex items-center gap-2.5 pl-2 pr-1 py-1.5 flex-1 min-w-0 text-left">
                            {isChatStreaming && (
                              <span className="relative flex-shrink-0 w-2 h-2">
                                <span className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-75" />
                                <span className="relative block w-2 h-2 rounded-full bg-emerald-500" />
                              </span>
                            )}
                            <span className="truncate flex-1">{chat.title || 'New Chat'}</span>
                          </button>
                          <ChatItemMenu
                            chatId={chat.chat_id}
                            title={chat.title}
                            isPublic={chat.is_public}
                            shareToken={chat.share_token}
                            onRenamed={handleRenamed}
                            onDeleted={handleDeleted}
                            onShareChange={handleShareChange}
                            buttonClassName={`mr-1 ${isActive ? '' : 'opacity-0 group-hover:opacity-100'}`}
                          />
                        </div>
                      );
                    })}
                    {isLoadingMore && (
                      <div className="flex justify-center py-2">
                        <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Profile */}
        <div className={`flex-shrink-0 border-t border-gray-200 px-2 py-2 ${expanded ? '' : 'flex justify-center'}`}>
          <ProfileDropdown collapsed={!expanded} />
        </div>
      </div>

      {/* Mobile bottom nav */}
      <div className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-gray-200 safe-area-bottom">
        <div className="flex items-center justify-around px-2 py-1">
          {mobileNavItems.map(item => {
            const active = viewMatch(currentView, item.view);
            const isHome = item.id === 'home';
            return (
              <button key={item.id} onClick={() => item.id === 'chat' ? onNewChat() : onNavigate(item.view)}
                className={`relative flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg transition-colors min-w-[56px] ${
                  active ? 'text-emerald-600' : 'text-gray-400'
                }`}>
                {item.icon}
                <span className="text-[10px] font-medium">{item.label}</span>
                {isHome && isStreamingChat && !active && (
                  <span className="absolute top-1 right-2 w-2 h-2">
                    <span className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-75" />
                    <span className="relative block w-2 h-2 rounded-full bg-emerald-500" />
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
});

AppSidebar.displayName = 'AppSidebar';
export default AppSidebar;
