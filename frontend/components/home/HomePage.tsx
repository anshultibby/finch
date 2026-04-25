'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { alpacaBrokerApi, marketApi, snaptradeApi } from '@/lib/api';
import { TLH_PROMPT, PORTFOLIO_REVIEW_PROMPT } from '@/lib/aiPrompts';
import SandboxBadge from '@/components/shared/SandboxBadge';
import MiniSparkline from '@/components/shared/MiniSparkline';
import type { AlpacaPortfolioResponse, PortfolioResponse } from '@/lib/types';

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function formatPct(n: number) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

function formatLargeCurrency(n: number) {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(1)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  return formatCurrency(n);
}

function num(v: string | null | undefined): number {
  return parseFloat(v || '0') || 0;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function StockCard({ item, onClick }: { item: any; onClick: () => void }) {
  const isUp = (item.changesPercentage || item.change || 0) >= 0;
  return (
    <button onClick={onClick}
      className="flex-shrink-0 w-[150px] p-3 rounded-xl border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all text-left bg-white">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-bold text-gray-900">{item.symbol}</span>
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
          isUp ? 'text-emerald-700 bg-emerald-50' : 'text-red-600 bg-red-50'
        }`}>
          {formatPct(item.changesPercentage || 0)}
        </span>
      </div>
      <div className="mb-1.5">
        <MiniSparkline symbol={item.symbol} width={120} height={32} days={30} />
      </div>
      <div className="text-sm font-bold text-gray-900 tabular-nums">
        ${item.price?.toFixed(2) || '--'}
      </div>
      <div className="text-[11px] text-gray-400 truncate">{item.name}</div>
    </button>
  );
}

function NewsCard({ item, onClick }: { item: any; onClick?: () => void }) {
  return (
    <a href={item.url} target="_blank" rel="noopener noreferrer"
      className="flex-shrink-0 w-[260px] sm:w-[280px] rounded-xl border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all overflow-hidden bg-white">
      {item.image && (
        <div className="h-[120px] bg-gray-100 overflow-hidden">
          <img src={item.image} alt="" className="w-full h-full object-cover" onError={e => (e.currentTarget.style.display = 'none')} />
        </div>
      )}
      <div className="p-3">
        <div className="text-sm font-semibold text-gray-900 leading-snug line-clamp-2 mb-1.5">{item.title}</div>
        <div className="flex items-center gap-2 text-[11px] text-gray-400">
          {item.symbol && (
            <span className="font-bold text-gray-500" onClick={e => { e.preventDefault(); onClick?.(); }}>{item.symbol}</span>
          )}
          <span>{item.site}</span>
          {item.publishedDate && (
            <span>{new Date(item.publishedDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
          )}
        </div>
      </div>
    </a>
  );
}

function EarningsCard({ item, onClick }: { item: any; onClick: () => void }) {
  const timeLabel = item.time === 'bmo' ? 'Before open' : item.time === 'amc' ? 'After close' : '';
  return (
    <button onClick={onClick}
      className="flex-shrink-0 w-[120px] p-3 rounded-xl border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all text-left bg-white">
      <div className="text-sm font-bold text-gray-900 mb-1">{item.symbol}</div>
      <div className="text-[11px] text-gray-400">
        {item.date ? new Date(item.date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}
      </div>
      {timeLabel && <div className="text-[10px] text-gray-300 mt-0.5">{timeLabel}</div>}
      {item.epsEstimated != null && (
        <div className="text-[10px] text-gray-400 mt-1">
          EPS est: <span className="font-semibold text-gray-600">${item.epsEstimated?.toFixed(2)}</span>
        </div>
      )}
    </button>
  );
}

function InlineSearch({ onSelect }: { onSelect: (symbol: string) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const containerRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); setOpen(false); return; }
    setLoading(true);
    try {
      const data = await marketApi.searchStocks(q, 8);
      setResults(Array.isArray(data) ? data : []);
      setOpen(true);
    } catch { setResults([]); }
    finally { setLoading(false); }
  }, []);

  const handleChange = (val: string) => {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(val), 250);
  };

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={containerRef} className="relative flex-1">
      <div className="relative">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          value={query}
          onChange={e => handleChange(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder="Search stocks..."
          className="w-full pl-10 pr-4 py-3 text-sm bg-gray-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:bg-white transition-all"
        />
        {query && (
          <button onClick={() => { setQuery(''); setResults([]); setOpen(false); }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden z-30 max-h-[380px] overflow-y-auto">
          {/* Empty state — suggestions */}
          {!query.trim() && (
            <>
              <div className="px-4 pt-3 pb-1.5">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Quick access</span>
              </div>
              <div className="px-3 pb-2 flex flex-wrap gap-1.5">
                {[
                  { label: 'Top gainers', emoji: '📈' },
                  { label: 'Top losers', emoji: '📉' },
                  { label: 'Upcoming earnings', emoji: '📅' },
                  { label: 'Most active', emoji: '🔥' },
                ].map(item => (
                  <button key={item.label}
                    onClick={() => { setOpen(false); /* Could navigate to filtered view */ }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-gray-200 hover:bg-gray-50 transition-colors text-xs font-medium text-gray-600">
                    <span>{item.emoji}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
              <div className="px-4 pt-2 pb-1.5 border-t border-gray-100">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Popular</span>
              </div>
              {[
                { symbol: 'AAPL', name: 'Apple Inc.' },
                { symbol: 'MSFT', name: 'Microsoft Corporation' },
                { symbol: 'NVDA', name: 'NVIDIA Corporation' },
                { symbol: 'TSLA', name: 'Tesla Inc.' },
                { symbol: 'AMZN', name: 'Amazon.com Inc.' },
              ].map(item => (
                <button key={item.symbol} onClick={() => { onSelect(item.symbol); setOpen(false); setQuery(''); }}
                  className="w-full flex items-center gap-3 px-4 py-2 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 last:border-b-0">
                  <span className="text-sm font-bold text-gray-900 min-w-[48px]">{item.symbol}</span>
                  <span className="text-sm text-gray-400 truncate">{item.name}</span>
                </button>
              ))}
            </>
          )}

          {/* Loading */}
          {loading && query.trim() && results.length === 0 && (
            <div className="flex justify-center py-4">
              <div className="w-4 h-4 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
            </div>
          )}

          {/* Search results */}
          {query.trim() && results.map((item, i) => (
            <button key={i} onClick={() => {
              onSelect(item.symbol);
              setQuery('');
              setResults([]);
              setOpen(false);
            }}
              className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 last:border-b-0">
              <div className="min-w-[52px]">
                <span className="text-sm font-bold text-gray-900">{item.symbol}</span>
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-sm text-gray-500 truncate block">{item.name}</span>
              </div>
              <span className="text-[10px] text-gray-300 flex-shrink-0">{item.exchangeShortName}</span>
            </button>
          ))}

          {/* No results */}
          {!loading && query.trim() && results.length === 0 && (
            <div className="px-4 py-4 text-sm text-gray-400 text-center">No results for &ldquo;{query}&rdquo;</div>
          )}
        </div>
      )}
    </div>
  );
}


function SectionHeader({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-4 sm:px-6 mb-2.5">
      <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">{title}</span>
      {children}
    </div>
  );
}

function HorizontalScroll({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto scrollbar-none">
      <div className="flex gap-2.5 px-4 sm:px-6 pb-1">
        {children}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Popular stocks (hardcoded blue chips)
// ─────────────────────────────────────────────────────────────────────────────

const POPULAR_SYMBOLS = 'SPY,QQQ,DIA,AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META';

// ─────────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const { user } = useAuth();
  const { openStock, navigateTo, openChatWithPrompt, startNewChat } = useNavigation();
  const [portfolio, setPortfolio] = useState<AlpacaPortfolioResponse | null>(null);
  const [externalPortfolio, setExternalPortfolio] = useState<PortfolioResponse | null>(null);
  const [hasAccount, setHasAccount] = useState<boolean | null>(null);
  const [hasBrokerage, setHasBrokerage] = useState<boolean>(false);
  const [movers, setMovers] = useState<{ gainers: any[]; losers: any[] }>({ gainers: [], losers: [] });
  const [moversTab, setMoversTab] = useState<'gainers' | 'losers'>('gainers');
  const [popularQuotes, setPopularQuotes] = useState<any[]>([]);
  const [earnings, setEarnings] = useState<any[]>([]);
  const [news, setNews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      alpacaBrokerApi.getAccountStatus(user.id).catch(() => ({ exists: false })),
      marketApi.getMovers().catch(() => ({ gainers: [], losers: [] })),
      marketApi.getBatchQuotes(POPULAR_SYMBOLS.split(',')).catch(() => []),
      marketApi.getEarnings().catch(() => []),
      marketApi.getGeneralNews(8).catch(() => []),
      snaptradeApi.checkStatus(user.id).catch(() => ({ is_connected: false })),
    ]).then(([status, m, popular, earn, n, brokerage]) => {
      const s = status as any;
      setHasAccount(s.exists && s.status === 'ACTIVE');
      if (s.exists && s.status === 'ACTIVE') {
        alpacaBrokerApi.getPortfolio(user.id).then(setPortfolio).catch(() => {});
      }
      const brokerageConnected = Boolean((brokerage as any)?.is_connected);
      setHasBrokerage(brokerageConnected);
      if (brokerageConnected) {
        snaptradeApi.getPortfolio(user.id).then(setExternalPortfolio).catch(() => {});
      }
      setMovers({ gainers: m.gainers || [], losers: m.losers || [] });
      setPopularQuotes(Array.isArray(popular) ? popular : []);
      setEarnings(Array.isArray(earn) ? earn : []);
      setNews(Array.isArray(n) ? n : []);
    }).finally(() => setLoading(false));
  }, [user]);

  const equity = num(portfolio?.account?.equity);
  const lastEquity = num(portfolio?.account?.last_equity);
  const dayChange = equity - lastEquity;
  const dayChangePct = lastEquity > 0 ? (dayChange / lastEquity) * 100 : 0;

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Sticky search bar */}
      <div className="shrink-0 px-4 sm:px-6 pt-3 pb-2 border-b border-gray-100 bg-white z-20">
        <div className="flex items-center gap-2">
          <InlineSearch onSelect={openStock} />
          <button onClick={startNewChat}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gray-900 text-white hover:bg-gray-800 transition-colors flex-shrink-0"
            title="Ask AI">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375" />
            </svg>
            <span className="text-sm font-medium hidden sm:inline">Ask AI</span>
          </button>
          <SandboxBadge className="hidden sm:inline-flex" />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* ── Linked Accounts section ─────────────────────────────────── */}
        <div className="px-4 sm:px-6 pt-4 pb-2">
          <div className="rounded-2xl border border-gray-100 bg-white overflow-hidden">
            <div className="p-4 pb-3">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center">
                    <svg className="w-4 h-4 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Z" />
                    </svg>
                  </div>
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Linked Accounts</span>
                </div>
                <button onClick={() => navigateTo({ type: 'connections' })}
                  className="text-[11px] text-gray-400 hover:text-gray-600 font-medium transition-colors">
                  Manage
                </button>
              </div>

              {hasBrokerage && externalPortfolio ? (
                <>
                  <div className="text-2xl font-bold text-gray-900 tabular-nums mb-0.5">
                    {formatCurrency(externalPortfolio.total_value)}
                  </div>
                  <div className="text-xs text-gray-400 mb-3">
                    {externalPortfolio.total_positions} position{externalPortfolio.total_positions !== 1 ? 's' : ''} across {externalPortfolio.account_count} account{externalPortfolio.account_count !== 1 ? 's' : ''}
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => openChatWithPrompt(PORTFOLIO_REVIEW_PROMPT, 'Review my portfolio')}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-semibold text-violet-700 bg-violet-50 rounded-xl hover:bg-violet-100 transition-colors">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375" />
                      </svg>
                      Review
                    </button>
                    <button onClick={() => openChatWithPrompt(TLH_PROMPT, 'Scan portfolio for tax losses')}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-semibold text-emerald-700 bg-emerald-50 rounded-xl hover:bg-emerald-100 transition-colors">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
                      </svg>
                      Tax-loss harvest
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="text-sm text-gray-400 mb-3">Connect your brokerage to see holdings and run AI analysis.</div>
                  <button onClick={() => navigateTo({ type: 'connections' })}
                    className="w-full py-2 text-xs font-semibold text-violet-700 bg-violet-50 rounded-xl hover:bg-violet-100 transition-colors">
                    Connect brokerage
                  </button>
                </>
              )}
            </div>

            {/* Inline holdings list */}
            {externalPortfolio?.accounts?.some(a => a.positions.length > 0) && (
              <div className="border-t border-gray-100">
                {externalPortfolio.accounts.flatMap(a => a.positions)
                  .sort((a, b) => b.value - a.value)
                  .map(p => {
                    const gl = p.gain_loss || 0;
                    const glPct = p.gain_loss_percent || 0;
                    const isUp = gl >= 0;
                    return (
                      <button key={p.symbol} onClick={() => openStock(p.symbol)}
                        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0">
                        <div className="min-w-[52px] text-left">
                          <div className="text-sm font-semibold text-gray-900">{p.symbol}</div>
                          <div className="text-[11px] text-gray-400">
                            {p.quantity % 1 === 0 ? p.quantity : p.quantity.toFixed(2)} sh
                          </div>
                        </div>
                        <div className="flex-1">
                          <MiniSparkline symbol={p.symbol} width={60} height={20} days={30} />
                        </div>
                        <div className="text-right min-w-[80px]">
                          <div className="text-sm font-medium text-gray-900 tabular-nums">{formatCurrency(p.price)}</div>
                          <div className={`text-[11px] font-medium tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
                            {gl >= 0 ? '+' : ''}{formatCurrency(gl)} ({formatPct(glPct)})
                          </div>
                        </div>
                      </button>
                    );
                  })}
              </div>
            )}
          </div>
        </div>

        {/* ── Agent Portfolio section ─────────────────────────────────── */}
        <div className="px-4 sm:px-6 pb-4">
          <div className="rounded-2xl border border-gray-100 bg-white overflow-hidden">
            <div className="p-4 pb-3">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
                    <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 0 0 2.25-2.25V6.75a2.25 2.25 0 0 0-2.25-2.25H6.75A2.25 2.25 0 0 0 4.5 6.75v10.5a2.25 2.25 0 0 0 2.25 2.25Z" />
                    </svg>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Agent Portfolio</span>
                    <SandboxBadge />
                  </div>
                </div>
                <button onClick={() => navigateTo({ type: 'portfolio' })}
                  className="text-[11px] text-gray-400 hover:text-gray-600 font-medium transition-colors">
                  Manage
                </button>
              </div>

              {hasAccount && portfolio ? (
                <>
                  <div className="text-2xl font-bold text-gray-900 tabular-nums mb-0.5">
                    {formatCurrency(equity)}
                  </div>
                  {lastEquity > 0 && dayChange !== 0 ? (
                    <div className={`text-xs font-medium tabular-nums mb-3 ${dayChange >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      {dayChange >= 0 ? '+' : ''}{formatCurrency(dayChange)} ({formatPct(dayChangePct)}) today
                    </div>
                  ) : (
                    <div className="text-xs text-gray-400 mb-3">
                      {portfolio.positions.length} position{portfolio.positions.length !== 1 ? 's' : ''} · {formatCurrency(num(portfolio.account?.cash))} cash
                    </div>
                  )}
                  <button onClick={() => openChatWithPrompt('Show me my agent portfolio positions, current P&L, and any pending orders. Suggest what trades to make next.', 'Chat about agent portfolio')}
                    className="w-full flex items-center justify-center gap-1.5 py-2 text-xs font-semibold text-amber-700 bg-amber-50 rounded-xl hover:bg-amber-100 transition-colors">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375" />
                    </svg>
                    Chat with agent
                  </button>
                </>
              ) : (
                <>
                  <div className="text-sm text-gray-400 mb-3">Open a sandbox account and let AI trade on your behalf.</div>
                  <button onClick={() => navigateTo({ type: 'portfolio' })}
                    className="w-full py-2 text-xs font-semibold text-amber-700 bg-amber-50 rounded-xl hover:bg-amber-100 transition-colors">
                    Open agent account
                  </button>
                </>
              )}
            </div>

            {/* Inline agent positions list */}
            {portfolio && portfolio.positions.length > 0 && (
              <div className="border-t border-gray-100">
                {portfolio.positions.map(p => {
                  const pl = num(p.unrealized_pl);
                  const plPct = num(p.unrealized_plpc) * 100;
                  const isUp = pl >= 0;
                  return (
                    <button key={p.symbol} onClick={() => openStock(p.symbol)}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0">
                      <div className="min-w-[52px] text-left">
                        <div className="text-sm font-semibold text-gray-900">{p.symbol}</div>
                        <div className="text-[11px] text-gray-400">
                          {num(p.qty) % 1 === 0 ? num(p.qty) : num(p.qty).toFixed(2)} sh
                        </div>
                      </div>
                      <div className="flex-1">
                        <MiniSparkline symbol={p.symbol} width={60} height={20} days={30} />
                      </div>
                      <div className="text-right min-w-[80px]">
                        <div className="text-sm font-medium text-gray-900 tabular-nums">{formatCurrency(num(p.current_price))}</div>
                        <div className={`text-[11px] font-medium tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
                          {pl >= 0 ? '+' : ''}{formatCurrency(pl)} ({formatPct(plPct)})
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Market indices */}
        <div className="px-4 sm:px-6 pb-4">
          <div className="grid grid-cols-3 gap-2">
            {[
              { symbol: 'SPY', label: 'S&P 500' },
              { symbol: 'QQQ', label: 'NASDAQ' },
              { symbol: 'DIA', label: 'DOW' },
            ].map(idx => {
              const q = popularQuotes.find((p: any) => p.symbol === idx.symbol);
              const pct = q?.changesPercentage || 0;
              const up = pct >= 0;
              return (
                <button key={idx.symbol} onClick={() => openStock(idx.symbol)}
                  className="p-3 rounded-xl border border-gray-100 hover:border-gray-200 transition-all bg-white text-left">
                  <div className="text-[11px] text-gray-400 font-medium mb-0.5">{idx.label}</div>
                  <div className="text-sm font-bold text-gray-900 tabular-nums mb-1">
                    {q ? `$${q.price?.toFixed(2)}` : '--'}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <MiniSparkline symbol={idx.symbol} width={48} height={20} days={1} />
                    <span className={`text-[11px] font-bold tabular-nums ${up ? 'text-emerald-600' : 'text-red-500'}`}>
                      {formatPct(pct)}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Popular stocks (exclude index ETFs already shown above) */}
        {popularQuotes.length > 0 && (
          <div className="mb-5">
            <SectionHeader title="Popular Stocks" />
            <HorizontalScroll>
              {popularQuotes
                .filter(q => !['SPY', 'QQQ', 'DIA'].includes(q.symbol))
                .map((q, i) => (
                  <StockCard key={i} item={q} onClick={() => openStock(q.symbol)} />
                ))}
            </HorizontalScroll>
          </div>
        )}

        {/* Top movers */}
        {(movers.gainers.length > 0 || movers.losers.length > 0) && (
          <div className="mb-5">
            <SectionHeader title="Market Movers">
              <div className="flex gap-1">
                {(['gainers', 'losers'] as const).map(tab => (
                  <button key={tab} onClick={() => setMoversTab(tab)}
                    className={`px-2.5 py-0.5 text-[10px] font-bold rounded-md transition-colors ${
                      moversTab === tab ? 'bg-gray-900 text-white' : 'text-gray-400 hover:text-gray-600'
                    }`}>
                    {tab === 'gainers' ? 'Gainers' : 'Losers'}
                  </button>
                ))}
              </div>
            </SectionHeader>
            <HorizontalScroll>
              {(moversTab === 'gainers' ? movers.gainers : movers.losers).slice(0, 10).map((item, i) => (
                <StockCard key={i} item={item} onClick={() => openStock(item.symbol)} />
              ))}
            </HorizontalScroll>
          </div>
        )}

        {/* Upcoming earnings */}
        {earnings.length > 0 && (
          <div className="mb-5">
            <SectionHeader title="Upcoming Earnings" />
            <HorizontalScroll>
              {earnings.map((e, i) => (
                <EarningsCard key={i} item={e} onClick={() => openStock(e.symbol)} />
              ))}
            </HorizontalScroll>
          </div>
        )}

        {/* Market news */}
        {news.length > 0 && (
          <div className="mb-5">
            <SectionHeader title="Market News" />
            <HorizontalScroll>
              {news.map((n, i) => (
                <NewsCard key={i} item={n} onClick={n.symbol ? () => openStock(n.symbol) : undefined} />
              ))}
            </HorizontalScroll>
          </div>
        )}

        {/* Spacer for mobile bottom nav */}
        <div className="h-20 md:h-8" />
      </div>
    </div>
  );
}
