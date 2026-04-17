'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// ─────────────────────────────────────────────────────────────────────────────
// View types
// ─────────────────────────────────────────────────────────────────────────────

export type View =
  | { type: 'home' }
  | { type: 'stock'; symbol: string }
  | { type: 'watchlist' }
  | { type: 'portfolio' }
  | { type: 'orders' }
  | { type: 'connections' }
  | { type: 'swaps' }
  | { type: 'chat' }
  | { type: 'search'; query?: string };

// ─────────────────────────────────────────────────────────────────────────────
// Context
// ─────────────────────────────────────────────────────────────────────────────

interface NavigationContextType {
  currentView: View;
  navigateTo: (view: View) => void;
  goBack: () => void;
  canGoBack: boolean;

  // Chat drawer (for contextual chats anchored to a stock page)
  chatDrawerOpen: boolean;
  setChatDrawerOpen: (open: boolean) => void;
  chatContext?: { symbol?: string; prefill?: string; prefillLabel?: string };
  openChatAbout: (symbol: string, prefill?: string) => void;

  // Chat page (full-page AI workspace)
  currentChatId: string | null;
  setCurrentChatId: (id: string | null) => void;
  startNewChat: () => void;
  openChatWithPrompt: (prompt: string, label?: string) => void;
  loadChat: (chatId: string) => void;

  // Helpers
  openStock: (symbol: string) => void;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

export function NavigationProvider({ children }: { children: ReactNode }) {
  const [history, setHistory] = useState<View[]>([{ type: 'home' }]);
  const [chatDrawerOpen, setChatDrawerOpen] = useState(false);
  const [chatContext, setChatContext] = useState<{ symbol?: string; prefill?: string; prefillLabel?: string }>();
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);

  const currentView = history[history.length - 1];

  const navigateTo = useCallback((view: View) => {
    setHistory(prev => {
      const next = [...prev, view];
      // Cap history to prevent unbounded growth in long sessions
      return next.length > 50 ? next.slice(-50) : next;
    });
  }, []);

  const goBack = useCallback(() => {
    setHistory(prev => prev.length > 1 ? prev.slice(0, -1) : prev);
  }, []);

  const openStock = useCallback((symbol: string) => {
    navigateTo({ type: 'stock', symbol: symbol.toUpperCase() });
  }, [navigateTo]);

  const openChatAbout = useCallback((symbol: string, prefill?: string) => {
    setChatContext({ symbol: symbol.toUpperCase(), prefill: prefill || `What do you think about ${symbol.toUpperCase()}?` });
    setChatDrawerOpen(true);
  }, []);

  const startNewChat = useCallback(() => {
    setCurrentChatId(null);
    setChatContext(undefined);
    navigateTo({ type: 'chat' });
  }, [navigateTo]);

  const openChatWithPrompt = useCallback((prompt: string, label?: string) => {
    setCurrentChatId(null);
    setChatContext({ prefill: prompt, prefillLabel: label });
    navigateTo({ type: 'chat' });
  }, [navigateTo]);

  const loadChat = useCallback((chatId: string) => {
    setCurrentChatId(chatId);
    setChatContext(undefined);
    navigateTo({ type: 'chat' });
  }, [navigateTo]);

  return (
    <NavigationContext.Provider value={{
      currentView,
      navigateTo,
      goBack,
      canGoBack: history.length > 1,
      chatDrawerOpen,
      setChatDrawerOpen,
      chatContext,
      openChatAbout,
      currentChatId,
      setCurrentChatId,
      startNewChat,
      openChatWithPrompt,
      loadChat,
      openStock,
    }}>
      {children}
    </NavigationContext.Provider>
  );
}

export function useNavigation() {
  const context = useContext(NavigationContext);
  if (context === undefined) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
}
