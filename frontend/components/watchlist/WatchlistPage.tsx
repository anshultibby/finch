'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { watchlistApi, marketApi } from '@/lib/api';

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function formatPct(n: number) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

interface WatchlistItem {
  symbol: string;
  name?: string;
  price?: number;
  change?: number;
  changesPercentage?: number;
  added_at?: string;
}

export default function WatchlistPage() {
  const { user } = useAuth();
  const { openStock } = useNavigation();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [addSymbol, setAddSymbol] = useState('');
  const [adding, setAdding] = useState(false);

  const fetchWatchlist = useCallback(async () => {
    if (!user) return;
    try {
      const data = await watchlistApi.getWatchlist(user.id);
      setItems(data.symbols || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchWatchlist(); }, [fetchWatchlist]);

  const handleAdd = async () => {
    if (!user || !addSymbol.trim()) return;
    setAdding(true);
    try {
      await watchlistApi.addSymbol(user.id, addSymbol.toUpperCase());
      setAddSymbol('');
      fetchWatchlist();
    } catch { /* ignore */ }
    finally { setAdding(false); }
  };

  const handleRemove = async (symbol: string) => {
    if (!user) return;
    // Optimistic remove
    setItems(prev => prev.filter(i => i.symbol !== symbol));
    try {
      await watchlistApi.removeSymbol(user.id, symbol);
    } catch {
      fetchWatchlist(); // Revert on error
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="shrink-0 px-4 sm:px-6 pt-5 pb-3">
        <div className="text-lg font-bold text-gray-900 mb-3">Watchlist</div>

        {/* Add symbol */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              value={addSymbol}
              onChange={e => setAddSymbol(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && handleAdd()}
              placeholder="Add symbol (e.g. AAPL)"
              className="w-full pl-3 pr-3 py-2.5 text-sm bg-gray-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:bg-white transition-all font-mono uppercase"
            />
          </div>
          <button onClick={handleAdd} disabled={adding || !addSymbol.trim()}
            className="px-4 py-2.5 text-sm font-bold text-white rounded-xl disabled:opacity-40 transition-opacity"
            style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
            {adding ? '...' : 'Add'}
          </button>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center py-8">
            <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <div className="w-14 h-14 rounded-2xl bg-gray-50 border border-gray-100 flex items-center justify-center mx-auto mb-4">
              <svg className="w-7 h-7 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
              </svg>
            </div>
            <div className="text-sm font-semibold text-gray-700 mb-1">No stocks in your watchlist</div>
            <div className="text-xs text-gray-400 max-w-[200px] mx-auto">
              Add symbols above or star stocks from their detail pages.
            </div>
          </div>
        ) : (
          items.map(item => {
            const isUp = (item.changesPercentage || 0) >= 0;
            return (
              <div key={item.symbol} className="flex items-center border-b border-gray-100 last:border-b-0">
                <button
                  onClick={() => openStock(item.symbol)}
                  className="flex-1 flex items-center gap-3 px-4 sm:px-6 py-3.5 hover:bg-gray-50 transition-colors text-left"
                >
                  <div className="min-w-[56px]">
                    <div className="text-sm font-bold text-gray-900">{item.symbol}</div>
                    {item.name && <div className="text-[11px] text-gray-400 truncate max-w-[120px]">{item.name}</div>}
                  </div>

                  <div className="flex-1 flex items-center justify-center">
                    <div className="w-full max-w-[80px] flex items-center gap-0.5">
                      <div className={`flex-1 border-t-2 border-dotted ${isUp ? 'border-emerald-300' : 'border-red-300'}`} />
                      <div className={`w-2 h-2 rounded-full ${isUp ? 'bg-emerald-500' : 'bg-red-500'}`} />
                    </div>
                  </div>

                  <div className="text-right min-w-[80px]">
                    {item.price != null ? (
                      <>
                        <div className="text-sm font-semibold text-gray-900 tabular-nums">{formatCurrency(item.price)}</div>
                        <div className={`text-xs font-medium tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
                          {formatPct(item.changesPercentage || 0)}
                        </div>
                      </>
                    ) : (
                      <div className="text-xs text-gray-300">--</div>
                    )}
                  </div>
                </button>

                {/* Remove */}
                <button onClick={() => handleRemove(item.symbol)}
                  className="px-3 py-3 text-gray-300 hover:text-red-400 transition-colors flex-shrink-0">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            );
          })
        )}

        <div className="h-20 md:h-4" />
      </div>
    </div>
  );
}
