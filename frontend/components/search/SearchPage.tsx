'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import { marketApi } from '@/lib/api';

// ─────────────────────────────────────────────────────────────────────────────
// Popular stocks (shown when search is empty)
// ─────────────────────────────────────────────────────────────────────────────

const POPULAR = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'MSFT', name: 'Microsoft Corporation' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation' },
  { symbol: 'TSLA', name: 'Tesla Inc.' },
  { symbol: 'META', name: 'Meta Platforms Inc.' },
  { symbol: 'JPM', name: 'JPMorgan Chase & Co.' },
  { symbol: 'V', name: 'Visa Inc.' },
  { symbol: 'QQQ', name: 'Invesco QQQ Trust' },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF' },
  { symbol: 'VOO', name: 'Vanguard S&P 500 ETF' },
];

export default function SearchPage() {
  const { openStock, goBack, canGoBack } = useNavigation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); return; }
    setLoading(true);
    try {
      const data = await marketApi.searchStocks(q, 12);
      setResults(Array.isArray(data) ? data : []);
    } catch { setResults([]); }
    finally { setLoading(false); }
  }, []);

  const handleChange = (val: string) => {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(val), 300);
  };

  const displayList = query.trim() ? results : POPULAR;
  const isPopular = !query.trim();

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Search header */}
      <div className="shrink-0 px-4 pt-4 pb-2">
        <div className="flex items-center gap-3">
          {canGoBack && (
            <button onClick={goBack} className="p-1 -ml-1 text-gray-400 hover:text-gray-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
          )}
          <div className="flex-1 relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              value={query}
              onChange={e => handleChange(e.target.value)}
              placeholder="Search stocks, ETFs..."
              className="w-full pl-10 pr-4 py-2.5 text-sm bg-gray-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:bg-white transition-all"
            />
            {query && (
              <button onClick={() => { setQuery(''); setResults([]); }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        {isPopular && (
          <div className="px-4 pt-2 pb-1">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Popular</span>
          </div>
        )}

        {loading && (
          <div className="flex justify-center py-6">
            <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
          </div>
        )}

        {!loading && displayList.map((item, i) => (
          <button key={i} onClick={() => openStock(item.symbol)}
            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 last:border-b-0">
            <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-bold text-gray-500">{item.symbol?.slice(0, 2)}</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-gray-900">{item.symbol}</div>
              <div className="text-xs text-gray-400 truncate">{item.name || item.companyName}</div>
            </div>
            {item.exchangeShortName && (
              <span className="text-[10px] text-gray-300 flex-shrink-0">{item.exchangeShortName}</span>
            )}
          </button>
        ))}

        {!loading && query.trim() && results.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-gray-400">No results for &ldquo;{query}&rdquo;</div>
        )}

        <div className="h-20 md:h-4" />
      </div>
    </div>
  );
}
