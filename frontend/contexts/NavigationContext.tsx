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
  | { type: 'search'; query?: string };

// ─────────────────────────────────────────────────────────────────────────────
// Context
// ─────────────────────────────────────────────────────────────────────────────

interface NavigationContextType {
  currentView: View;
  navigateTo: (view: View) => void;
  goBack: () => void;
  canGoBack: boolean;

  // Chat drawer
  chatDrawerOpen: boolean;
  setChatDrawerOpen: (open: boolean) => void;
  chatContext?: { symbol?: string; prefill?: string; prefillLabel?: string };
  openChatAbout: (symbol: string, prefill?: string) => void;
  openChatWithPrompt: (prompt: string, label?: string) => void;

  // Helpers
  openStock: (symbol: string) => void;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

export function NavigationProvider({ children }: { children: ReactNode }) {
  const [history, setHistory] = useState<View[]>([{ type: 'home' }]);
  const [chatDrawerOpen, setChatDrawerOpen] = useState(false);
  const [chatContext, setChatContext] = useState<{ symbol?: string; prefill?: string; prefillLabel?: string }>();

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

  const openChatWithPrompt = useCallback((prompt: string, label?: string) => {
    setChatContext({ prefill: prompt, prefillLabel: label });
    setChatDrawerOpen(true);
  }, []);

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
      openChatWithPrompt,
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
