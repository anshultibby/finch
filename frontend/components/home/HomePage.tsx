'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { alpacaBrokerApi, marketApi } from '@/lib/api';
import SandboxBadge from '@/components/shared/SandboxBadge';
import type { AlpacaPortfolioResponse } from '@/lib/types';

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function formatPct(n: number) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

function num(v: string | null | undefined): number {
  return parseFloat(v || '0') || 0;
}

// ─────────────────────────────────────────────────────────────────────────────
// Mover row
// ─────────────────────────────────────────────────────────────────────────────

function MoverRow({ item, onClick }: { item: any; onClick: () => void }) {
  const isUp = (item.changesPercentage || item.change || 0) >= 0;
  return (
    <button onClick={onClick}
      className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors w-full text-left">
      <div className="min-w-[52px]">
        <div className="text-sm font-bold text-gray-900">{item.symbol}</div>
      </div>
      <div className="flex-1 truncate text-xs text-gray-400">{item.name}</div>
      <div className="text-right">
        <div className="text-sm font-semibold text-gray-900 tabular-nums">${item.price?.toFixed(2)}</div>
        <div className={`text-xs font-medium tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
          {formatPct(item.changesPercentage || 0)}
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Home page
// ─────────────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const { user } = useAuth();
  const { openStock, navigateTo, openChatAbout } = useNavigation();
  const [portfolio, setPortfolio] = useState<AlpacaPortfolioResponse | null>(null);
  const [hasAccount, setHasAccount] = useState<boolean | null>(null);
  const [movers, setMovers] = useState<{ gainers: any[]; losers: any[] }>({ gainers: [], losers: [] });
  const [moversTab, setMoversTab] = useState<'gainers' | 'losers'>('gainers');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      alpacaBrokerApi.getAccountStatus(user.id).catch(() => ({ exists: false })),
      marketApi.getMovers().catch(() => ({ gainers: [], losers: [] })),
    ]).then(([status, m]) => {
      const s = status as any;
      setHasAccount(s.exists && s.status === 'ACTIVE');
      if (s.exists && s.status === 'ACTIVE') {
        alpacaBrokerApi.getPortfolio(user.id).then(setPortfolio).catch(() => {});
      }
      setMovers({ gainers: m.gainers || [], losers: m.losers || [] });
    }).finally(() => setLoading(false));
  }, [user]);

  const equity = num(portfolio?.account?.equity);
  const lastEquity = num(portfolio?.account?.last_equity);
  const dayChange = equity - lastEquity;
  const dayChangePct = lastEquity > 0 ? (dayChange / lastEquity) * 100 : 0;

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  })();

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex-1 overflow-y-auto">
        {/* Hero */}
        <div className="px-4 sm:px-6 pt-6 pb-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm text-gray-500">{greeting}</span>
            <SandboxBadge />
          </div>

          {hasAccount && portfolio ? (
            <div>
              <div className="text-3xl sm:text-4xl font-bold text-gray-900 tabular-nums mb-1">
                {formatCurrency(equity)}
              </div>
              {lastEquity > 0 && dayChange !== 0 && (
                <div className={`text-sm font-medium tabular-nums ${dayChange >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {dayChange >= 0 ? '+' : ''}{formatCurrency(dayChange)} ({formatPct(dayChangePct)}) today
                </div>
              )}
            </div>
          ) : (
            <div>
              <div className="text-2xl font-bold text-gray-900 mb-2">Welcome to Finch</div>
              <div className="text-sm text-gray-500 mb-4">Your AI-powered brokerage. Browse stocks, get insights, and trade — all with your AI agent.</div>
              {!hasAccount && (
                <button onClick={() => navigateTo({ type: 'portfolio' })}
                  className="px-5 py-2.5 text-sm font-bold text-white rounded-xl hover:opacity-90 transition-opacity"
                  style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
                  Open an account
                </button>
              )}
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="px-4 sm:px-6 pb-4">
          <div className="flex gap-2">
            <button onClick={() => navigateTo({ type: 'search' })}
              className="flex-1 flex items-center gap-2 px-4 py-3 rounded-xl border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all">
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span className="text-sm text-gray-400">Search stocks...</span>
            </button>
            <button onClick={() => openChatAbout('')}
              className="flex items-center gap-2 px-4 py-3 rounded-xl bg-gray-900 text-white hover:bg-gray-800 transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375" />
              </svg>
              <span className="text-sm font-medium">Ask AI</span>
            </button>
          </div>
        </div>

        {/* Positions preview */}
        {portfolio && portfolio.positions.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center justify-between px-4 sm:px-6 mb-1">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Positions</span>
              <button onClick={() => navigateTo({ type: 'portfolio' })}
                className="text-xs text-emerald-600 font-semibold hover:underline">See all</button>
            </div>
            {portfolio.positions.slice(0, 5).map(p => (
              <button key={p.symbol} onClick={() => openStock(p.symbol)}
                className="w-full flex items-center gap-3 px-4 sm:px-6 py-2.5 hover:bg-gray-50 transition-colors">
                <div className="min-w-[52px] text-left">
                  <div className="text-sm font-bold text-gray-900">{p.symbol}</div>
                  <div className="text-[11px] text-gray-400">{parseFloat(p.qty || '0')} sh</div>
                </div>
                <div className="flex-1" />
                <div className="text-right">
                  <div className="text-sm font-semibold text-gray-900 tabular-nums">{formatCurrency(parseFloat(p.current_price || '0'))}</div>
                  <div className={`text-xs font-medium tabular-nums ${parseFloat(p.unrealized_pl || '0') >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {parseFloat(p.unrealized_pl || '0') >= 0 ? '+' : ''}{formatCurrency(parseFloat(p.unrealized_pl || '0'))}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Market movers */}
        <div className="mb-4">
          <div className="flex items-center gap-3 px-4 sm:px-6 mb-2">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Market Movers</span>
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
          </div>
          {(moversTab === 'gainers' ? movers.gainers : movers.losers).slice(0, 8).map((item, i) => (
            <MoverRow key={i} item={item} onClick={() => openStock(item.symbol)} />
          ))}
          {movers.gainers.length === 0 && movers.losers.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-gray-400">Market data loading...</div>
          )}
        </div>

        {/* Spacer for mobile bottom nav */}
        <div className="h-20 md:h-8" />
      </div>
    </div>
  );
}
