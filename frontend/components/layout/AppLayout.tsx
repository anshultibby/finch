'use client';

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { NavigationProvider, useNavigation } from '@/contexts/NavigationContext';
import AppSidebar, { type AppSidebarRef } from './AppSidebar';
import ChatDrawer from '@/components/chat/ChatDrawer';
import { ChatModeProvider } from '@/contexts/ChatModeContext';
import HomePage from '@/components/home/HomePage';
import StockPage from '@/components/stock/StockPage';
import SearchPage from '@/components/search/SearchPage';
import WatchlistPage from '@/components/watchlist/WatchlistPage';
import OrdersPage from '@/components/orders/OrdersPage';
import PortfolioPanel from '@/components/PortfolioPanel';
import ConnectionsPanel from '@/components/ConnectionsPanel';
import SwapsPanel, { type StoredSwap } from '@/components/SwapsPanel';
import ChatPage from '@/components/chat/ChatPage';
import type { SwapData } from '@/lib/types';

// ─────────────────────────────────────────────────────────────────────────────
// Swap persistence
// ─────────────────────────────────────────────────────────────────────────────

const SWAPS_STORAGE_KEY = 'finch_swap_opportunities';

function loadStoredSwaps(userId: string): StoredSwap[] {
  try {
    const raw = localStorage.getItem(`${SWAPS_STORAGE_KEY}_${userId}`);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveStoredSwaps(userId: string, swaps: StoredSwap[]) {
  try {
    localStorage.setItem(`${SWAPS_STORAGE_KEY}_${userId}`, JSON.stringify(swaps.slice(-50)));
  } catch { /* ignore */ }
}

// ─────────────────────────────────────────────────────────────────────────────
// Inner layout (uses navigation context)
// ─────────────────────────────────────────────────────────────────────────────

function AppLayoutInner() {
  const { user } = useAuth();
  const {
    currentView,
    navigateTo,
    chatDrawerOpen,
    setChatDrawerOpen,
    currentChatId,
    setCurrentChatId,
    startNewChat,
    loadChat,
  } = useNavigation();

  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [activeChatIsLoading, setActiveChatIsLoading] = useState(false);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);
  const [storedSwaps, setStoredSwaps] = useState<StoredSwap[]>([]);

  const sidebarRef = useRef<AppSidebarRef>(null);

  // Load persisted swaps
  useEffect(() => {
    if (user?.id) setStoredSwaps(loadStoredSwaps(user.id));
  }, [user?.id]);

  const pendingSwapCount = storedSwaps.filter(s => s.status === 'pending').length;

  const handleSwapsReceived = useCallback((chatId: string, swaps: SwapData[]) => {
    if (!user?.id) return;
    setStoredSwaps(prev => {
      const next = [...prev];
      for (const swap of swaps) {
        const existingIdx = next.findIndex(s => s.sell_symbol === swap.sell_symbol && s.status !== 'dismissed');
        if (existingIdx >= 0) {
          next[existingIdx] = { ...next[existingIdx], ...swap, id: next[existingIdx].id, chatId, receivedAt: new Date().toISOString(), status: next[existingIdx].status };
        } else {
          const id = `${swap.sell_symbol}-${swap.buy_symbol}-${Date.now()}`;
          next.push({ ...swap, id, chatId, receivedAt: new Date().toISOString(), status: 'pending' });
        }
      }
      saveStoredSwaps(user.id, next);
      return next;
    });
  }, [user?.id]);

  const updateSwapStatus = useCallback((swap: StoredSwap, status: StoredSwap['status']) => {
    if (!user?.id) return;
    setStoredSwaps(prev => {
      const next = prev.map(s => s.id === swap.id ? { ...s, status } : s);
      saveStoredSwaps(user.id, next);
      return next;
    });
  }, [user?.id]);

  const handleApprove = useCallback((swap: StoredSwap) => updateSwapStatus(swap, 'approved'), [updateSwapStatus]);
  const handleReject = useCallback((swap: StoredSwap) => updateSwapStatus(swap, 'rejected'), [updateSwapStatus]);
  const handleDismiss = useCallback((swap: StoredSwap) => updateSwapStatus(swap, 'dismissed'), [updateSwapStatus]);

  const handleSelectCandidate = useCallback((swap: StoredSwap, buySymbol: string) => {
    if (!user?.id) return;
    setStoredSwaps(prev => {
      const next = prev.map(s => s.id === swap.id ? { ...s, selected_buy_symbol: buySymbol } : s);
      saveStoredSwaps(user.id, next);
      return next;
    });
  }, [user?.id]);

  const handleChatAboutSwap = useCallback((_message: string) => {
    setCurrentChatId(null);
    setChatDrawerOpen(true);
  }, [setChatDrawerOpen]);

  if (!user) return null;

  // Render current view (excluding chat — chat is always mounted for stream persistence)
  const renderNonChatView = () => {
    switch (currentView.type) {
      case 'home':
        return null;
      case 'stock':
        return <StockPage symbol={currentView.symbol} />;
      case 'search':
        return <HomePage />;
      case 'portfolio':
        return <PortfolioPanel />;
      case 'orders':
        return <OrdersPage />;
      case 'watchlist':
        return <WatchlistPage />;
      case 'connections':
        return <ConnectionsPanel />;
      case 'swaps':
        return (
          <SwapsPanel
            swaps={storedSwaps.filter(s => s.status !== 'dismissed')}
            userId={user.id}
            onApprove={handleApprove}
            onReject={handleReject}
            onDismiss={handleDismiss}
            onChatAboutSwap={handleChatAboutSwap}
            onSelectCandidate={handleSelectCandidate}
          />
        );
      case 'chat':
        return null;
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="flex h-dvh bg-white overflow-hidden">
      <AppSidebar
        ref={sidebarRef}
        userId={user.id}
        currentView={currentView}
        onNavigate={navigateTo}
        currentChatId={currentChatId}
        onSelectChat={loadChat}
        onNewChat={startNewChat}
        refreshTrigger={chatHistoryRefresh}
        isCreatingChat={isCreatingChat}
        isStreamingChat={activeChatIsLoading}
        pendingSwapCount={pendingSwapCount}
      />

      {/* Main content */}
      <div className="flex-1 overflow-hidden relative pb-14 md:pb-0">
        <ChatModeProvider>
          {renderNonChatView()}

          {/* ChatPage always mounted so streams survive navigation */}
          <div className={['chat', 'home'].includes(currentView.type) ? 'h-full' : 'hidden'}>
            <ChatPage
              sidebarRef={sidebarRef}
              onCreatingChatChange={setIsCreatingChat}
              onLoadingChange={setActiveChatIsLoading}
              onHistoryRefresh={() => setChatHistoryRefresh(p => p + 1)}
              onSwapsReceived={handleSwapsReceived}
            />
          </div>

          {/* Chat drawer overlay */}
          <ChatDrawer
            sidebarRef={sidebarRef}
            currentChatId={currentChatId}
            onChatIdChange={setCurrentChatId}
            onCreatingChatChange={setIsCreatingChat}
            onLoadingChange={setActiveChatIsLoading}
            onHistoryRefresh={() => setChatHistoryRefresh(p => p + 1)}
            onSwapsReceived={handleSwapsReceived}
          />
        </ChatModeProvider>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Outer wrapper with providers
// ─────────────────────────────────────────────────────────────────────────────

export default function AppLayout() {
  return (
    <NavigationProvider>
      <AppLayoutInner />
    </NavigationProvider>
  );
}
