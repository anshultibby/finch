'use client';

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useCredits } from '@/contexts/CreditsContext';
import { NavigationProvider, useNavigation } from '@/contexts/NavigationContext';
import type { View } from '@/contexts/NavigationContext';
import AppSidebar, { type AppSidebarRef } from './AppSidebar';
import ChatDrawer from '@/components/chat/ChatDrawer';
import { ChatModeProvider } from '@/contexts/ChatModeContext';
import TickerLogo from '@/components/ui/TickerLogo';
import StockPage from '@/components/stock/StockPage';
import OrdersPage from '@/components/orders/OrdersPage';
import PortfolioPanel from '@/components/PortfolioPanel';
import SwapsPanel, { type StoredSwap } from '@/components/SwapsPanel';
import ChatPage from '@/components/chat/ChatPage';
import HomePage from '@/components/home/HomePage';
import VisualizationsPanel from '@/components/VisualizationsPanel';
import MemoryStorePanel from '@/components/memory/MemoryStorePanel';
import ScreenerPanel from '@/components/ScreenerPanel';
import AnalyticsPanel from '@/components/AnalyticsPanel';
import CreditsModal from '@/components/CreditsModal';
import { marketApi } from '@/lib/api';
import type { SwapData } from '@/lib/types';

// ─────────────────────────────────────────────────────────────────────────────
// Top Bar — breadcrumbs + search
// ─────────────────────────────────────────────────────────────────────────────

function viewLabel(view: View): string {
  switch (view.type) {
    case 'home': return 'Dashboard';
    case 'stock': return view.symbol;
    case 'portfolio': return 'Portfolio';
    case 'orders': return 'Orders';
    case 'swaps': return 'Swaps';
    case 'chat': return 'Chat';
    case 'visualizations': return 'Visualizations';
    case 'memory-store': return 'Memory Store';
    case 'screener': return 'Screener';
    case 'analytics': return 'Analytics';
    default: return '';
  }
}

const TRENDING_STOCKS = [
  { symbol: 'NVDA', name: 'NVIDIA Corporation', exchange: 'NASDAQ' },
  { symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' },
  { symbol: 'TSLA', name: 'Tesla Inc.', exchange: 'NASDAQ' },
  { symbol: 'MSFT', name: 'Microsoft Corporation', exchange: 'NASDAQ' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', exchange: 'NASDAQ' },
];

function TopBar() {
  const { currentView, goBack, canGoBack, openStock, navigateTo } = useNavigation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const search = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); return; }
    setLoading(true);
    try {
      const data = await marketApi.searchStocks(q, 8);
      const arr = Array.isArray(data) ? data : [];
      // Collapse duplicates: same ticker, and same-company cross-listings
      // (e.g. NVDA/NASDAQ vs NVDA.NE/NEO show identical "NVIDIA Corporation").
      // The API returns the primary US listing first, so first-wins is correct.
      const seenSym = new Set<string>();
      const seenName = new Set<string>();
      const deduped = arr.filter((it: any) => {
        const sym = it?.symbol;
        if (!sym || seenSym.has(sym)) return false;
        const name = (it?.name || '').trim().toLowerCase();
        if (name && seenName.has(name)) return false;
        seenSym.add(sym);
        if (name) seenName.add(name);
        return true;
      });
      setResults(deduped);
    } catch { setResults([]); }
    finally { setLoading(false); }
  }, []);

  const handleChange = (val: string) => {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(val), 250);
  };

  const handleSelect = (symbol: string) => {
    openStock(symbol);
    setQuery('');
    setResults([]);
    setOpen(false);
  };

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Reset the search box whenever the user navigates — stale query text
  // shouldn't linger in the top bar across views.
  useEffect(() => {
    setQuery('');
    setResults([]);
    setOpen(false);
  }, [currentView.type, (currentView as any).symbol]);

  const showTrending = open && !query.trim();
  const showResults = open && query.trim() && results.length > 0;
  const showEmpty = open && query.trim() && !loading && results.length === 0;

  return (
    <div className="shrink-0 flex items-center gap-3 px-4 py-2 border-b border-gray-100 bg-white z-20">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-1.5 text-sm min-w-0 flex-shrink-0">
        <button onClick={() => navigateTo({ type: 'home' })}
          className={`font-semibold transition-colors ${currentView.type === 'home' ? 'text-gray-900' : 'text-gray-400 hover:text-gray-600'}`}>
          Finch
        </button>
        {currentView.type !== 'home' && (
          <>
            {currentView.type === 'stock' && currentView.tab === 'earnings' ? (
              <>
                <svg className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
                <button onClick={() => { navigateTo({ type: 'home' }); /* could navigate to earnings tab */ }}
                  className="font-semibold text-gray-400 hover:text-gray-600 transition-colors">
                  Earnings
                </button>
                <svg className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
                <span className="font-semibold text-gray-900 truncate">{currentView.symbol}</span>
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
                <span className="font-semibold text-gray-900 truncate">{viewLabel(currentView)}</span>
              </>
            )}
          </>
        )}
      </div>

      {/* Search */}
      <div ref={containerRef} className="flex-1 max-w-lg mx-auto relative">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            value={query}
            onChange={e => handleChange(e.target.value)}
            onFocus={() => setOpen(true)}
            onKeyDown={e => {
              if (e.key === 'Escape') {
                setQuery(''); setResults([]); setOpen(false);
                (e.target as HTMLInputElement).blur();
              }
            }}
            placeholder="Search for stocks, crypto, and more..."
            className="w-full pl-10 pr-4 py-2 text-sm bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-gray-300 focus:bg-white focus:border-gray-300 transition-all"
          />
          {query && (
            <button onClick={() => { setQuery(''); setResults([]); setOpen(false); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Dropdown */}
        {(showTrending || showResults || showEmpty) && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden z-40 max-h-[400px] overflow-y-auto">
            {showTrending && (
              <>
                <div className="px-4 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">Trending</div>
                {TRENDING_STOCKS.map(item => (
                  <button key={item.symbol} onClick={() => handleSelect(item.symbol)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 last:border-b-0">
                    <TickerLogo symbol={item.symbol} size={32} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-gray-900">{item.name}</div>
                      <div className="text-xs text-gray-400">{item.symbol} &middot; {item.exchange}</div>
                    </div>
                    <svg className="w-4 h-4 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                    </svg>
                  </button>
                ))}
              </>
            )}

            {showResults && results.map((item, i) => (
              <button key={i} onClick={() => handleSelect(item.symbol)}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 last:border-b-0">
                <TickerLogo symbol={item.symbol} size={32} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-gray-900">{item.name}</div>
                  <div className="text-xs text-gray-400">{item.symbol} &middot; {item.exchangeShortName}</div>
                </div>
                <svg className="w-4 h-4 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            ))}

            {showEmpty && (
              <div className="px-4 py-6 text-sm text-gray-400 text-center">No results for &ldquo;{query}&rdquo;</div>
            )}

            {loading && query.trim() && results.length === 0 && (
              <div className="flex justify-center py-4">
                <div className="w-4 h-4 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right spacer for symmetry */}
      <div className="w-[80px] flex-shrink-0" />
    </div>
  );
}

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

function StripeReturnBanner() {
  const searchParams = useSearchParams();
  const { refresh } = useCredits();
  const [show, setShow] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const upgraded = searchParams.get('upgraded') === 'true';
    const topup = searchParams.get('topup') === 'success';
    if (upgraded) {
      setMessage('Welcome to Finch Pro! 1,000 bonus credits added.');
      setShow(true);
    } else if (topup) {
      setMessage('Credits added to your account.');
      setShow(true);
    }
    if (upgraded || topup) {
      window.history.replaceState({}, '', window.location.pathname);
      refresh();
      setTimeout(() => refresh(), 3000);
    }
  }, [searchParams, refresh]);

  useEffect(() => {
    if (show) {
      const t = setTimeout(() => setShow(false), 5000);
      return () => clearTimeout(t);
    }
  }, [show]);

  if (!show) return null;

  return (
    <div className="absolute top-14 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-2 duration-300">
      <div className="flex items-center gap-2 bg-green-50 border border-green-200 text-green-800 text-sm px-4 py-2 rounded-full shadow-sm">
        <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        {message}
        <button onClick={() => setShow(false)} className="ml-1 text-green-600 hover:text-green-800">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

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
        return <HomePage />;
      case 'stock':
        return <StockPage symbol={currentView.symbol} initialTab={currentView.tab} />;
      case 'portfolio':
        return <PortfolioPanel />;
      case 'orders':
        return <OrdersPage />;
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
      case 'visualizations':
        return <VisualizationsPanel vizId={currentView.vizId} />;
      case 'memory-store':
        return <MemoryStorePanel />;
      case 'screener':
        return <ScreenerPanel />;
      case 'analytics':
        return <AnalyticsPanel />;
      case 'chat':
        return null;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-dvh bg-white overflow-hidden">
      <CreditsModal />
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
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden relative pb-14 md:pb-0">
        <TopBar />
        <StripeReturnBanner />

        <ChatModeProvider>
          {currentView.type !== 'chat' && (
            <div className="flex-1 overflow-hidden">
              {renderNonChatView()}
            </div>
          )}

          {/* ChatPage always mounted so streams survive navigation */}
          <div className={currentView.type === 'chat' ? 'flex-1 min-h-0 overflow-hidden' : 'hidden'}>
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
