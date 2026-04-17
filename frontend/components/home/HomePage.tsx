'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { alpacaBrokerApi, marketApi, snaptradeApi } from '@/lib/api';
import { TLH_PROMPT, PORTFOLIO_REVIEW_PROMPT } from '@/lib/aiPrompts';
import SandboxBadge from '@/components/shared/SandboxBadge';
import MiniSparkline from '@/components/shared/MiniSparkline';
import type { AlpacaPortfolioResponse } from '@/lib/types';

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

// ─────────────────────────────────────────────────────────────────────────────
// AI Action card (TLH, Portfolio Review, Trading Agent)
// ─────────────────────────────────────────────────────────────────────────────

type ActionAccent = 'emerald' | 'violet' | 'amber';

const ACCENT_STYLES: Record<ActionAccent, { bg: string; iconBg: string; iconText: string; hover: string; ring: string }> = {
  emerald: { bg: 'bg-emerald-50', iconBg: 'bg-emerald-500/15', iconText: 'text-emerald-600', hover: 'hover:bg-emerald-100/70', ring: 'hover:ring-emerald-200' },
  violet:  { bg: 'bg-violet-50',  iconBg: 'bg-violet-500/15',  iconText: 'text-violet-600',  hover: 'hover:bg-violet-100/70',  ring: 'hover:ring-violet-200' },
  amber:   { bg: 'bg-amber-50',   iconBg: 'bg-amber-500/15',   iconText: 'text-amber-700',   hover: 'hover:bg-amber-100/70',   ring: 'hover:ring-amber-200' },
};

function ActionCard({
  title,
  subtitle,
  icon,
  accent,
  requires,
  onClick,
}: {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  accent: ActionAccent;
  requires?: 'brokerage' | 'account';
  onClick: () => void;
}) {
  const s = ACCENT_STYLES[accent];
  const requiresLabel = requires === 'brokerage' ? 'Connect brokerage' : requires === 'account' ? 'Open account' : null;

  return (
    <button
      onClick={onClick}
      className={`group text-left rounded-2xl p-4 transition-all ring-1 ring-transparent ${s.bg} ${s.hover} ${s.ring}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl ${s.iconBg} flex items-center justify-center ${s.iconText}`}>
          {icon}
        </div>
        {requiresLabel && (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-gray-600 bg-white/80 backdrop-blur px-2 py-0.5 rounded-full ring-1 ring-gray-200/70">
            <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            {requiresLabel}
          </span>
        )}
      </div>
      <div className="text-sm font-bold text-gray-900 mb-0.5">{title}</div>
      <div className="text-xs text-gray-500 leading-relaxed">{subtitle}</div>
    </button>
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
      setHasBrokerage(Boolean((brokerage as any)?.is_connected));
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
        {/* AI Actions — the three core flows */}
        <div className="px-4 sm:px-6 pt-3 pb-5">
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2.5">What your AI can do</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <ActionCard
              title="Tax-loss harvesting"
              subtitle="Find tax savings hiding in your holdings"
              accent="emerald"
              requires={!hasBrokerage ? 'brokerage' : undefined}
              icon={
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
                </svg>
              }
              onClick={() => {
                if (!hasBrokerage) navigateTo({ type: 'connections' });
                else openChatWithPrompt(TLH_PROMPT, 'Scan portfolio for tax losses');
              }}
            />
            <ActionCard
              title="Portfolio review"
              subtitle="Get an AI analysis of your holdings"
              accent="violet"
              requires={!hasBrokerage ? 'brokerage' : undefined}
              icon={
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5V6Z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13.5 10.5H21A7.5 7.5 0 0 0 13.5 3v7.5Z" />
                </svg>
              }
              onClick={() => {
                if (!hasBrokerage) navigateTo({ type: 'connections' });
                else openChatWithPrompt(PORTFOLIO_REVIEW_PROMPT, 'Review my portfolio');
              }}
            />
            <ActionCard
              title="Trading agent"
              subtitle="Let AI trade stocks on your behalf"
              accent="amber"
              requires={!hasAccount ? 'account' : undefined}
              icon={
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
                </svg>
              }
              onClick={() => navigateTo({ type: 'portfolio' })}
            />
          </div>
        </div>

        {/* Portfolio hero (only if account exists) */}
        {hasAccount && portfolio && (
          <div className="px-4 sm:px-6 pt-3 pb-3">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-gray-400 font-medium">Portfolio</span>
              <SandboxBadge className="sm:hidden" />
            </div>
            <div className="text-3xl sm:text-4xl font-bold text-gray-900 tabular-nums mb-0.5">
              {formatCurrency(equity)}
            </div>
            {lastEquity > 0 && dayChange !== 0 && (
              <div className={`text-sm font-medium tabular-nums ${dayChange >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                {dayChange >= 0 ? '+' : ''}{formatCurrency(dayChange)} ({formatPct(dayChangePct)}) today
              </div>
            )}
          </div>
        )}

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

        {/* Positions preview (if account active) */}
        {portfolio && portfolio.positions.length > 0 && (
          <div className="mb-5">
            <SectionHeader title="Your Positions">
              <button onClick={() => navigateTo({ type: 'portfolio' })} className="text-xs text-emerald-600 font-semibold hover:underline">See all</button>
            </SectionHeader>
            <HorizontalScroll>
              {portfolio.positions.map(p => {
                const pl = parseFloat(p.unrealized_pl || '0');
                const isUp = pl >= 0;
                return (
                  <button key={p.symbol} onClick={() => openStock(p.symbol)}
                    className="flex-shrink-0 w-[140px] p-3 rounded-xl border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all text-left bg-white">
                    <div className="text-sm font-bold text-gray-900 mb-1">{p.symbol}</div>
                    <div className="text-base font-bold text-gray-900 tabular-nums mb-0.5">
                      {formatCurrency(parseFloat(p.current_price || '0'))}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-gray-400">{parseFloat(p.qty || '0')} sh</span>
                      <span className={`text-[11px] font-bold ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
                        {isUp ? '+' : ''}{formatCurrency(pl)}
                      </span>
                    </div>
                  </button>
                );
              })}
            </HorizontalScroll>
          </div>
        )}

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
