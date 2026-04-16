'use client';

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import AppSidebar, { type AppSidebarRef } from './AppSidebar';
import ChatView from '@/components/chat/ChatView';
import PortfolioPanel from '@/components/PortfolioPanel';
import ConnectionsPanel from '@/components/ConnectionsPanel';
import SwapsPanel, { type StoredSwap } from '@/components/SwapsPanel';
import { ChatModeProvider } from '@/contexts/ChatModeContext';
import { NavigationProvider } from '@/contexts/NavigationContext';
import type { SwapData } from '@/lib/types';

const SWAPS_STORAGE_KEY = 'finch_swap_opportunities';

function loadStoredSwaps(userId: string): StoredSwap[] {
  try {
    const raw = localStorage.getItem(`${SWAPS_STORAGE_KEY}_${userId}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveStoredSwaps(userId: string, swaps: StoredSwap[]) {
  try {
    // Keep last 50 swaps to avoid unbounded growth
    const trimmed = swaps.slice(-50);
    localStorage.setItem(`${SWAPS_STORAGE_KEY}_${userId}`, JSON.stringify(trimmed));
  } catch {
    // ignore storage errors
  }
}

export default function AppLayout() {
  const { user } = useAuth();
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [activeChatIsLoading, setActiveChatIsLoading] = useState(false);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);
  const [chatPrefill, setChatPrefill] = useState<string | undefined>();
  const [activePanel, setActivePanel] = useState<'chat' | 'portfolio' | 'connections' | 'swaps'>('chat');
  const [storedSwaps, setStoredSwaps] = useState<StoredSwap[]>([]);

  const sidebarRef = useRef<AppSidebarRef>(null);

  // Load persisted swaps on mount
  useEffect(() => {
    if (user?.id) {
      setStoredSwaps(loadStoredSwaps(user.id));
    }
  }, [user?.id]);

  const pendingSwapCount = storedSwaps.filter(s => s.status === 'pending').length;

  const handleSwapsReceived = useCallback((chatId: string, swaps: SwapData[]) => {
    if (!user?.id) return;
    setStoredSwaps(prev => {
      const next = [...prev];
      for (const swap of swaps) {
        // Deduplicate by sell_symbol — same position shouldn't appear twice
        const existingIdx = next.findIndex(s => s.sell_symbol === swap.sell_symbol && s.status !== 'dismissed');
        if (existingIdx >= 0) {
          // Update with fresh data from the latest analysis, preserve user's decision
          next[existingIdx] = {
            ...next[existingIdx],
            ...swap,
            id: next[existingIdx].id,
            chatId,
            receivedAt: new Date().toISOString(),
            status: next[existingIdx].status,
          };
        } else {
          const id = `${swap.sell_symbol}-${swap.buy_symbol}-${Date.now()}`;
          next.push({ ...swap, id, chatId, receivedAt: new Date().toISOString(), status: 'pending' });
        }
      }
      saveStoredSwaps(user.id, next);
      return next;
    });
  }, [user?.id]);

  const handleChatAboutSwap = useCallback((message: string) => {
    setCurrentChatId(null);
    setChatPrefill(message);
    setActivePanel('chat');
  }, []);

  const updateSwapStatus = useCallback((swap: StoredSwap, status: StoredSwap['status']) => {
    if (!user?.id) return;
    setStoredSwaps(prev => {
      const next = prev.map(s => s.id === swap.id ? { ...s, status } : s);
      saveStoredSwaps(user.id, next);
      return next;
    });
  }, [user?.id]);

  const handleApprove = useCallback((swap: StoredSwap) => {
    updateSwapStatus(swap, 'approved');
  }, [updateSwapStatus]);

  const handleReject = useCallback((swap: StoredSwap) => {
    updateSwapStatus(swap, 'rejected');
  }, [updateSwapStatus]);

  const handleDismiss = useCallback((swap: StoredSwap) => {
    updateSwapStatus(swap, 'dismissed');
  }, [updateSwapStatus]);

  const handleSelectCandidate = useCallback((swap: StoredSwap, buySymbol: string) => {
    if (!user?.id) return;
    setStoredSwaps(prev => {
      const next = prev.map(s => s.id === swap.id ? { ...s, selected_buy_symbol: buySymbol } : s);
      saveStoredSwaps(user.id, next);
      return next;
    });
  }, [user?.id]);

  if (!user) return null;

  return (
    <div className="flex h-dvh bg-white overflow-hidden">
      <AppSidebar
        ref={sidebarRef}
        userId={user.id}
        currentChatId={currentChatId}
        onSelectChat={(chatId) => {
          setCurrentChatId(chatId);
          setChatPrefill(undefined);
          setActivePanel('chat');
        }}
        onNewChat={() => {
          setCurrentChatId(null);
          setChatPrefill(undefined);
          setActivePanel('chat');
        }}
        refreshTrigger={chatHistoryRefresh}
        isCreatingChat={isCreatingChat}
        activeChatIsLoading={activeChatIsLoading}
        activePanel={activePanel}
        onSelectPanel={setActivePanel}
        pendingSwapCount={pendingSwapCount}
      />

      <div className="flex-1 overflow-hidden">
        {activePanel === 'portfolio' ? (
          <PortfolioPanel />
        ) : activePanel === 'connections' ? (
          <ConnectionsPanel />
        ) : activePanel === 'swaps' ? (
          <SwapsPanel
            swaps={storedSwaps.filter(s => s.status !== 'dismissed')}
            userId={user.id}
            onApprove={handleApprove}
            onReject={handleReject}
            onDismiss={handleDismiss}
            onChatAboutSwap={handleChatAboutSwap}
            onSelectCandidate={handleSelectCandidate}
          />
        ) : (
          <NavigationProvider>
            <ChatModeProvider>
              <ChatView
                externalChatId={currentChatId}
                onChatIdChange={(id) => { setCurrentChatId(id); if (id) setChatPrefill(undefined); }}
                onCreatingChatChange={setIsCreatingChat}
                onLoadingChange={setActiveChatIsLoading}
                onHistoryRefresh={() => setChatHistoryRefresh(p => p + 1)}
                onSwapsReceived={handleSwapsReceived}
                sidebarRef={sidebarRef}
                prefillMessage={chatPrefill}
                onVisualizationClick={() => {}}
              />
            </ChatModeProvider>
          </NavigationProvider>
        )}
      </div>
    </div>
  );
}
