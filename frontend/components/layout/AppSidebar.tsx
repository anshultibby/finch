'use client';

import React, { forwardRef, useImperativeHandle, useState, useEffect, useCallback } from 'react';
import { chatApi } from '@/lib/api';
import ProfileDropdown from '../ProfileDropdown';
import FinchLogo from '@/components/shared/FinchLogo';
import type { View } from '@/contexts/NavigationContext';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface Chat {
  chat_id: string;
  title: string | null;
  icon: string | null;
  created_at: string;
  updated_at: string;
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
  pendingSwapCount?: number;
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

const ChatIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 0 1 .778-.332 48.294 48.294 0 0 0 5.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
  </svg>
);

const SwapsIcon = ({ count }: { count: number }) => (
  <div className="relative">
    <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" />
    </svg>
    {count > 0 && (
      <span className="absolute -top-1 -right-1.5 w-4 h-4 bg-emerald-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
        {count > 9 ? '9+' : count}
      </span>
    )}
  </div>
);

const LinkedAccountsIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Z" />
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
  pendingSwapCount = 0,
}, ref) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [chatsCollapsed, setChatsCollapsed] = useState(false);
  const navItems: NavItem[] = [
    { id: 'home', label: 'Home', view: { type: 'home' }, icon: <HomeIcon />, mobileNav: true },
    { id: 'search', label: 'Search', view: { type: 'search' }, icon: <SearchIcon />, mobileNav: true },
    { id: 'portfolio', label: 'Agent Portfolio', view: { type: 'portfolio' }, icon: <AgentPortfolioIcon />, mobileNav: true },
    { id: 'watchlist', label: 'Watchlist', view: { type: 'watchlist' }, icon: <WatchlistIcon />, mobileNav: true },
  ];

  const secondaryItems: NavItem[] = [
    { id: 'orders', label: 'Orders', view: { type: 'orders' }, icon: <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" /></svg> },
    { id: 'swaps', label: 'Opportunities', view: { type: 'swaps' }, icon: <SwapsIcon count={pendingSwapCount} /> },
    { id: 'connections', label: 'Linked Accounts', view: { type: 'connections' }, icon: <LinkedAccountsIcon /> },
  ];

  const loadChats = useCallback(async () => {
    if (!userId) return;
    setIsLoading(true);
    try {
      const response = await chatApi.getUserChats(userId);
      const fetched = response.chats || [];
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

  const updateChatTitle = useCallback((chatId: string, title: string, icon: string) => {
    setChats(prev => {
      const exists = prev.find(c => c.chat_id === chatId);
      if (exists) return prev.map(c => c.chat_id === chatId ? { ...c, title, icon } : c);
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
    <>
      {/* Desktop sidebar */}
      <div className={`hidden md:flex h-full bg-gray-50 border-r border-gray-200 flex-col flex-shrink-0 transition-all duration-200 ${expanded ? 'w-60' : 'w-14'}`}>
        {/* Header */}
        <div className={`group/header flex items-center py-3 px-3 flex-shrink-0 ${expanded ? 'justify-between' : 'justify-center'}`}>
          {expanded ? (
            <>
              <FinchLogo size={22} showText />
              <button onClick={() => setExpanded(false)}
                className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-600 hover:text-gray-900 transition-colors"
                title="Collapse">
                <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <rect x="3" y="3" width="18" height="18" rx="2" strokeWidth={1.8} />
                  <path strokeLinecap="round" strokeWidth={1.8} d="M9 3v18" />
                </svg>
              </button>
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

        {/* New Chat — pen-in-square compose icon, ChatGPT-style */}
        <div className="px-2 pb-1 flex-shrink-0">
          <button
            onClick={onNewChat}
            className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors ${
              expanded ? '' : 'justify-center'
            }`}
            title={!expanded ? 'New chat' : undefined}
          >
            <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}>
              <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z" />
            </svg>
            {expanded && <span className="font-medium">New chat</span>}
          </button>
        </div>

        {/* Main nav */}
        <div className="flex-1 overflow-y-auto min-h-0">
          <div className="px-2 space-y-0.5">
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
          <div className="mx-3 my-2 border-t border-gray-200" />

          {/* Secondary nav */}
          <div className="px-2 space-y-0.5">
            {secondaryItems.map(item => {
              const active = viewMatch(currentView, item.view);
              return (
                <button key={item.id} onClick={() => onNavigate(item.view)}
                  className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors ${
                    active ? 'bg-white shadow-sm border border-gray-200 text-gray-900' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  } ${expanded ? '' : 'justify-center'}`}
                  title={!expanded ? item.label : undefined}>
                  {item.icon}
                  {expanded && <span className="font-medium">{item.label}</span>}
                  {expanded && item.id === 'swaps' && pendingSwapCount > 0 && (
                    <span className="ml-auto text-xs bg-emerald-100 text-emerald-700 font-semibold px-1.5 py-0.5 rounded-full">
                      {pendingSwapCount}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Divider */}
          <div className="mx-3 my-2 border-t border-gray-200" />

          {/* Recent chats — always visible when sidebar is expanded */}
          {expanded && (
            <div className="pb-2">
              <button onClick={() => setChatsCollapsed(c => !c)}
                className="w-full flex items-center justify-between px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-600 transition-colors">
                <span>Recent Chats</span>
                <svg className={`w-3 h-3 transition-transform ${chatsCollapsed ? '' : 'rotate-90'}`}
                  fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M7.293 4.707a1 1 0 010 1.414L3.414 10l3.879 3.879a1 1 0 01-1.414 1.414l-4.586-4.586a1 1 0 010-1.414l4.586-4.586a1 1 0 011.414 0z" clipRule="evenodd" transform="rotate(180 10 10)" />
                </svg>
              </button>
              {!chatsCollapsed && (
                <div className="px-2 space-y-0.5 mt-0.5">
                  {isCreatingChat && (
                    <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg bg-blue-50/50 border border-blue-100">
                      <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin flex-shrink-0" />
                      <span className="text-xs text-blue-600">Creating chat...</span>
                    </div>
                  )}
                  {chats.length === 0 && !isCreatingChat && !isLoading && (
                    <div className="px-2 py-2 text-xs text-gray-400">No chats yet</div>
                  )}
                  {chats.slice(0, 12).map(chat => {
                    const isActive = chat.chat_id === currentChatId && currentView.type === 'chat';
                    const isChatStreaming = chat.chat_id === currentChatId && isStreamingChat;
                    return (
                      <button key={chat.chat_id} onClick={() => onSelectChat(chat.chat_id)}
                        className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-sm transition-colors text-left ${
                          isActive ? 'bg-white shadow-sm border border-gray-200 text-gray-900 font-medium' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                        }`}>
                        {isChatStreaming && (
                          <span className="relative flex-shrink-0 w-2 h-2">
                            <span className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-75" />
                            <span className="relative block w-2 h-2 rounded-full bg-emerald-500" />
                          </span>
                        )}
                        <span className="truncate flex-1">{chat.title || 'New Chat'}</span>
                      </button>
                    );
                  })}
                </div>
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
          {navItems.filter(i => i.mobileNav).map(item => {
            const active = viewMatch(currentView, item.view);
            return (
              <button key={item.id} onClick={() => onNavigate(item.view)}
                className={`flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg transition-colors min-w-[56px] ${
                  active ? 'text-emerald-600' : 'text-gray-400'
                }`}>
                {item.icon}
                <span className="text-[10px] font-medium">{item.label}</span>
              </button>
            );
          })}
          <button onClick={onNewChat}
            className={`relative flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg transition-colors min-w-[56px] ${
              currentView.type === 'chat' ? 'text-emerald-600' : 'text-gray-400'
            }`}>
            <ChatIcon />
            <span className="text-[10px] font-medium">AI</span>
            {isStreamingChat && currentView.type !== 'chat' && (
              <span className="absolute top-1 right-2 w-2 h-2">
                <span className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-75" />
                <span className="relative block w-2 h-2 rounded-full bg-emerald-500" />
              </span>
            )}
          </button>
        </div>
      </div>
    </>
  );
});

AppSidebar.displayName = 'AppSidebar';
export default AppSidebar;
