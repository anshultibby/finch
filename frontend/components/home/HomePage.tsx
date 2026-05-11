'use client';

import React, { useEffect, useState, useRef, useCallback, KeyboardEvent } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { alpacaBrokerApi, marketApi, snaptradeApi, watchlistApi } from '@/lib/api';
import { PORTFOLIO_REVIEW_PROMPT } from '@/lib/aiPrompts';
import MiniSparkline from '@/components/shared/MiniSparkline';
import { SnapTradeReact } from 'snaptrade-react';
import type { AlpacaPortfolioResponse, Brokerage, PortfolioResponse } from '@/lib/types';

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}
function fmtPct(n: number) { return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`; }
function num(v: string | null | undefined): number { return parseFloat(v || '0') || 0; }

type Market = 'us' | 'india';
type HomeTab = 'markets' | 'earnings' | 'watchlist' | 'portfolio';

const MARKET_OPTIONS: { key: Market; label: string; flag: string }[] = [
  { key: 'us', label: 'US Markets', flag: '\u{1F1FA}\u{1F1F8}' },
  { key: 'india', label: 'India Markets', flag: '\u{1F1EE}\u{1F1F3}' },
];

const US_INDICES = [
  { symbol: 'SPY', label: 'S&P 500' },
  { symbol: 'QQQ', label: 'NASDAQ' },
  { symbol: 'DIA', label: 'Dow Jones' },
  { symbol: 'VIXY', label: 'VIX' },
];

const INDIA_INDICES = [
  { symbol: '^NSEI', label: 'NIFTY 50' },
  { symbol: '^BSESN', label: 'S&P BSE Sensex' },
  { symbol: '^NSEBANK', label: 'Nifty Bank Index' },
  { symbol: 'BTCUSD', label: 'Bitcoin' },
];

// ── Market Dropdown ──────────────────────────────────────────────────────────

function MarketDropdown({ market, onChange }: { market: Market; onChange: (m: Market) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = MARKET_OPTIONS.find(o => o.key === market)!;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-1 py-1 text-sm font-semibold text-gray-900 hover:text-gray-700 transition-colors">
        <span className="text-base leading-none">{current.flag}</span>
        <span>{current.label}</span>
        <svg className={`w-3.5 h-3.5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 bg-white rounded-xl shadow-lg border border-gray-200 py-1 z-30 min-w-[180px]">
          {MARKET_OPTIONS.map(opt => (
            <button key={opt.key} onClick={() => { onChange(opt.key); setOpen(false); }}
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-gray-50 transition-colors ${
                market === opt.key ? 'font-semibold text-gray-900' : 'text-gray-600'
              }`}>
              <span className="text-base">{opt.flag}</span>
              {opt.label}
              {market === opt.key && (
                <svg className="w-4 h-4 text-gray-900 ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="m4.5 12.75 6 6 9-13.5" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Top Nav Bar ──────────────────────────────────────────────────────────────

const NAV_TABS: { key: HomeTab; label: string }[] = [
  { key: 'markets', label: 'Markets' },
  { key: 'earnings', label: 'Earnings' },
  { key: 'watchlist', label: 'Watchlist' },
  { key: 'portfolio', label: 'Portfolio' },
];

function TopNavBar({ market, onMarketChange, activeTab, onTabChange }: {
  market: Market; onMarketChange: (m: Market) => void;
  activeTab: HomeTab; onTabChange: (tab: HomeTab) => void;
}) {
  return (
    <div className="shrink-0 border-b border-gray-100 bg-white px-5">
      <div className="flex items-center gap-6 h-11">
        <MarketDropdown market={market} onChange={onMarketChange} />
        {NAV_TABS.map(tab => (
          <button key={tab.key} onClick={() => onTabChange(tab.key)}
            className={`relative h-full flex items-center text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'text-gray-900'
                : 'text-gray-400 hover:text-gray-600'
            }`}>
            {tab.label}
            {activeTab === tab.key && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-gray-900 rounded-full" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Index Card ───────────────────────────────────────────────────────────────

function IndexCard({ symbol, label, quote, onClick }: {
  symbol: string; label: string; quote: any; onClick: () => void;
}) {
  const price = quote?.price;
  const change = quote?.change || 0;
  const changePct = quote?.changesPercentage || 0;
  const isUp = changePct >= 0;

  return (
    <button onClick={onClick}
      className="text-left p-4 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all bg-white group">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-sm font-semibold text-gray-900">{label}</div>
          <div className="text-lg font-bold text-gray-900 tabular-nums mt-0.5">
            {price != null ? `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '--'}
          </div>
        </div>
        <div className="text-right">
          <div className={`text-sm font-bold tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
            <span className="mr-0.5">{isUp ? '↗' : '↘'}</span>
            {fmtPct(changePct)}
          </div>
          <div className={`text-xs tabular-nums mt-0.5 ${isUp ? 'text-emerald-500' : 'text-red-400'}`}>
            {change >= 0 ? '+' : ''}{fmt(change)}
          </div>
        </div>
      </div>
      <div className="w-full">
        <MiniSparkline symbol={symbol} width={220} height={48} days={1} />
      </div>
    </button>
  );
}

// ── Watchlist Item ────────────────────────────────────────────────────────────

function WatchlistItem({ item, onClick }: { item: any; onClick: () => void }) {
  const isUp = (item.changesPercentage || 0) >= 0;
  return (
    <button onClick={onClick}
      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left">
      <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
        <span className="text-xs font-bold text-gray-500">{item.symbol?.slice(0, 2)}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-gray-900 truncate">{item.name || item.symbol}</div>
        <div className="text-xs text-gray-400">{item.symbol}</div>
      </div>
      <div className="text-right flex-shrink-0">
        <div className="text-sm font-semibold text-gray-900 tabular-nums">
          {item.price != null ? fmt(item.price) : '--'}
        </div>
        <div className={`text-xs font-medium tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
          {fmtPct(item.changesPercentage || 0)}
        </div>
      </div>
    </button>
  );
}

// ── Earnings Calendar ────────────────────────────────────────────────────────

function EarningsCalendar({ onStockClick, market }: { onStockClick: (s: string) => void; market: Market }) {
  const [weekOffset, setWeekOffset] = useState(0);
  const [earnings, setEarnings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [quotes, setQuotes] = useState<Record<string, any>>({});

  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay() + 1 + weekOffset * 7);

  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(startOfWeek);
    d.setDate(startOfWeek.getDate() + i);
    return d;
  });

  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  useEffect(() => {
    setLoading(true);
    setQuotes({});
    const fromDate = days[0].toISOString().split('T')[0];
    const toDate = days[6].toISOString().split('T')[0];
    marketApi.getEarnings(fromDate, toDate, market)
      .then(data => setEarnings(Array.isArray(data) ? data : []))
      .catch(() => setEarnings([]))
      .finally(() => setLoading(false));
  }, [weekOffset, market]);

  const earningsByDate: Record<string, any[]> = {};
  earnings.forEach(e => {
    const key = e.date;
    if (!earningsByDate[key]) earningsByDate[key] = [];
    earningsByDate[key].push(e);
  });

  const isToday = (d: Date) => d.toDateString() === today.toDateString();
  const [activeDay, setActiveDay] = useState<string>(days[0].toISOString().split('T')[0]);

  useEffect(() => {
    const todayDay = days.find(isToday);
    setActiveDay((todayDay || days[0]).toISOString().split('T')[0]);
  }, [weekOffset]);

  const activeDayEarnings = earningsByDate[activeDay] || [];

  useEffect(() => {
    if (!activeDayEarnings.length) return;
    const syms = activeDayEarnings.map((e: any) => e.symbol).filter(Boolean);
    const missing = syms.filter((s: string) => !quotes[s]);
    if (!missing.length) return;
    marketApi.getBatchQuotes(missing)
      .then((data: any[]) => {
        const map: Record<string, any> = {};
        data.forEach((q: any) => { map[q.symbol] = q; });
        setQuotes(prev => ({ ...prev, ...map }));
      })
      .catch(() => {});
  }, [activeDay, earnings]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Earnings Calendar</h2>
        <div className="flex items-center gap-3">
          <button onClick={() => setWeekOffset(w => w - 1)} className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
          </button>
          <button onClick={() => setWeekOffset(0)} className="text-xs font-medium text-gray-600 hover:text-gray-900 transition-colors">
            Today
          </button>
          <button onClick={() => setWeekOffset(w => w + 1)} className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m8.25 4.5 7.5 7.5-7.5 7.5" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto scrollbar-none pb-3">
        {days.map((d, i) => {
          const key = d.toISOString().split('T')[0];
          const count = earningsByDate[key]?.length || 0;
          const active = activeDay === key;
          return (
            <button key={i} onClick={() => setActiveDay(key)}
              className={`flex-shrink-0 w-[120px] p-3 rounded-xl border text-center transition-all ${
                active
                  ? 'border-gray-300 bg-gray-50 shadow-sm'
                  : 'border-gray-100 hover:border-gray-200'
              }`}>
              <div className="text-xs text-gray-400 font-medium">{dayNames[i]}</div>
              <div className={`text-lg font-bold mt-0.5 ${isToday(d) ? 'text-gray-900' : 'text-gray-700'}`}>
                {d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {count > 0 ? `${count} Calls` : 'No Calls'}
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-3 rounded-xl border border-gray-100 bg-gray-50 min-h-[200px]">
        {loading ? (
          <div className="flex items-center justify-center h-[200px]">
            <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
          </div>
        ) : activeDayEarnings.length > 0 ? (
          <div className="divide-y divide-gray-100">
            {activeDayEarnings.map((e, i) => {
              const q = quotes[e.symbol];
              const mcap = q?.marketCap;
              const mcapStr = mcap ? (mcap >= 1e12 ? `${(mcap/1e12).toFixed(1)}T` : mcap >= 1e9 ? `${(mcap/1e9).toFixed(1)}B` : mcap >= 1e6 ? `${(mcap/1e6).toFixed(0)}M` : '') : '';
              const chg = q?.changePercent;
              return (
                <button key={i} onClick={() => onStockClick(e.symbol)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white transition-colors text-left">
                  <div className="w-9 h-9 rounded-lg bg-white border border-gray-200 flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-bold text-gray-600">{e.symbol?.slice(0, 2)}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900">{e.symbol}</span>
                      {q?.price != null && chg != null && (
                        <span className={`text-xs font-medium ${chg >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                          {market === 'india' ? '₹' : '$'}{q.price.toFixed(2)} ({chg >= 0 ? '+' : ''}{chg.toFixed(2)}%)
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-600 truncate">
                      {q?.name || e.name || ''}
                      {mcapStr && <span className="text-gray-500"> · {mcapStr}</span>}
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-xs font-medium text-gray-700">
                      {e.time === 'bmo' ? 'Before open' : e.time === 'amc' ? 'After close' : e.time || ''}
                    </div>
                    {e.eps != null ? (
                      <div className="text-xs text-gray-600">
                        EPS: <span className={`font-semibold ${e.epsEstimated != null && e.eps >= e.epsEstimated ? 'text-emerald-600' : e.epsEstimated != null && e.eps < e.epsEstimated ? 'text-red-500' : 'text-gray-900'}`}>
                          {market === 'india' ? '₹' : '$'}{e.eps?.toFixed(2)}
                        </span>
                        {e.epsEstimated != null && (
                          <span className="text-gray-500"> / est {market === 'india' ? '₹' : '$'}{e.epsEstimated?.toFixed(2)}</span>
                        )}
                      </div>
                    ) : e.epsEstimated != null ? (
                      <div className="text-xs text-gray-600">
                        EPS est: <span className="font-semibold text-gray-900">{market === 'india' ? '₹' : '$'}{e.epsEstimated?.toFixed(2)}</span>
                      </div>
                    ) : null}
                  </div>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="flex items-center justify-center h-[200px] text-sm text-gray-400">
            No Earnings Calls
          </div>
        )}
      </div>
    </div>
  );
}

// ── Accounts Sidebar ─────────────────────────────────────────────────────────

const INSTITUTION_DOMAINS: Record<string, string> = {
  robinhood: 'robinhood.com',
  fidelity: 'fidelity.com',
  schwab: 'schwab.com',
  vanguard: 'vanguard.com',
  'td ameritrade': 'tdameritrade.com',
  etrade: 'etrade.com',
  'e*trade': 'etrade.com',
  interactive: 'interactivebrokers.com',
  'interactive brokers': 'interactivebrokers.com',
  webull: 'webull.com',
  sofi: 'sofi.com',
  merrill: 'merrilledge.com',
  'merrill lynch': 'merrilledge.com',
  'jp morgan': 'jpmorgan.com',
  jpmorgan: 'jpmorgan.com',
  chase: 'chase.com',
  wealthfront: 'wealthfront.com',
  betterment: 'betterment.com',
  coinbase: 'coinbase.com',
  'wells fargo': 'wellsfargo.com',
  ally: 'ally.com',
};

function institutionLogo(institution: string) {
  const key = institution.toLowerCase();
  const domain = Object.entries(INSTITUTION_DOMAINS).find(([k]) => key.includes(k))?.[1];
  if (!domain) return null;
  return `https://logo.clearbit.com/${domain}`;
}

function institutionLogoFallback(institution: string) {
  const key = institution.toLowerCase();
  const domain = Object.entries(INSTITUTION_DOMAINS).find(([k]) => key.includes(k))?.[1];
  if (!domain) return null;
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
}

function InstitutionLogo({ institution }: { institution: string }) {
  const logoUrl = institutionLogo(institution);
  const fallbackUrl = institutionLogoFallback(institution);
  const [src, setSrc] = useState(logoUrl);
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 text-xs font-bold text-gray-500">
        {institution.charAt(0).toUpperCase()}
      </div>
    );
  }

  return (
    <img src={src} alt={institution} className="w-7 h-7 rounded-lg object-contain flex-shrink-0 bg-white"
      onError={() => {
        if (src === logoUrl && fallbackUrl) setSrc(fallbackUrl);
        else setFailed(true);
      }} />
  );
}

function InstitutionGroup({ institution, accounts, groupValue, expanded, editing, onToggle, onSelectAccount, onDisconnect, selectedAccountId }: {
  institution: string; accounts: any[]; groupValue: number; expanded: boolean; editing?: boolean;
  onToggle: () => void; onSelectAccount: (id: string) => void; onDisconnect?: (accountId: string, accountName: string) => void; selectedAccountId?: string | null;
}) {
  return (
    <>
      <div className="flex items-center">
        <button onClick={onToggle}
          className="group flex-1 flex items-center gap-3 px-3.5 py-3 hover:bg-gray-50 transition-colors text-left">
          <div className="relative w-7 h-7 flex-shrink-0">
            <div className="group-hover:opacity-0 transition-opacity">
              <InstitutionLogo institution={institution} />
            </div>
            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <svg className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? '' : '-rotate-90'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19.5 8.25-7.5 7.5-7.5-7.5" />
              </svg>
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[13px] font-semibold text-gray-900">{institution}</div>
            <div className="text-xs text-gray-400">
              {accounts.length} account{accounts.length !== 1 ? 's' : ''}
            </div>
          </div>
          {!editing && (
            <div className="text-sm font-semibold text-gray-900 tabular-nums flex-shrink-0">
              {fmt(groupValue)}
            </div>
          )}
        </button>
        {editing && onDisconnect && (
          <button
            onClick={() => {
              for (const acct of accounts) onDisconnect(acct.id, acct.name);
            }}
            className="mr-4 p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors flex-shrink-0"
            title={`Remove ${institution}`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
          </button>
        )}
      </div>

      {expanded && accounts.map((acct, i) => (
        <div key={acct.id || i} className={`flex items-center border-t border-gray-100 ${
          selectedAccountId === acct.id ? 'bg-gray-50' : 'hover:bg-gray-50'
        }`}>
          <button onClick={() => !editing && onSelectAccount(acct.id)}
            className={`flex-1 flex items-center gap-2.5 pl-6 pr-5 py-2.5 text-left transition-colors ${editing ? 'cursor-default' : ''}`}>
            <div className="w-4 flex items-center justify-center flex-shrink-0">
              {accountTypeIcon(acct.type)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[13px] text-gray-700">{acct.name}</div>
              <div className="text-[11px] text-gray-400 capitalize">{acct.type.replace(/_/g, ' ').toLowerCase()}</div>
            </div>
            {!editing && (
              <div className="text-[13px] text-gray-600 tabular-nums flex-shrink-0">
                {fmt(acct.total_value)}
              </div>
            )}
          </button>
          {editing && onDisconnect && (
            <button
              onClick={() => onDisconnect(acct.id, acct.name)}
              className="mr-4 p-1 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 transition-colors flex-shrink-0"
              title={`Remove ${acct.name}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
              </svg>
            </button>
          )}
        </div>
      ))}
    </>
  );
}

function accountTypeIcon(type: string) {
  const t = type.toLowerCase();
  if (t.includes('roth')) return (
    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
  if (t.includes('ira')) return (
    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
    </svg>
  );
  if (t.includes('saving')) return (
    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 11.25v8.25a1.5 1.5 0 0 1-1.5 1.5H5.25a1.5 1.5 0 0 1-1.5-1.5v-8.25M12 4.875A2.625 2.625 0 1 0 9.375 7.5H12m0-2.625V7.5m0-2.625A2.625 2.625 0 1 1 14.625 7.5H12m0 0V21m-8.625-9.75h18c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125h-18c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />
    </svg>
  );
  if (t.includes('check')) return (
    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Z" />
    </svg>
  );
  // Default: brokerage
  return (
    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
    </svg>
  );
}

function AccountsSidebar({ hasBrokerage, externalPortfolio, hasAccount, portfolio, equity, onConnect, onDisconnect, onViewPortfolio, onSelectAccount, selectedAccountId }: {
  hasBrokerage: boolean; externalPortfolio: PortfolioResponse | null;
  hasAccount: boolean; portfolio: AlpacaPortfolioResponse | null;
  equity: number; onConnect: () => void; onDisconnect: (accountId: string, accountName: string) => void; onViewPortfolio: () => void;
  onSelectAccount: (id: string) => void; selectedAccountId?: string | null;
}) {
  const [expandedInstitutions, setExpandedInstitutions] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState(false);
  const toggleInstitution = (inst: string) => {
    setExpandedInstitutions(prev => {
      const next = new Set(prev);
      if (next.has(inst)) next.delete(inst); else next.add(inst);
      return next;
    });
  };

  if (!hasBrokerage && !hasAccount) {
    return (
      <div className="p-5 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-900 mb-3">Connect your accounts</h2>
        <div className="rounded-xl border border-gray-200 overflow-hidden">
          <div className="divide-y divide-gray-100">
            <div className="flex items-center gap-3 px-3.5 py-3">
              <div className="w-7 h-7 rounded-lg bg-amber-50 flex items-center justify-center flex-shrink-0">
                <svg className="w-3.5 h-3.5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-gray-900">Real-time sync</div>
                <div className="text-xs text-gray-400">Holdings, transactions, and liabilities</div>
              </div>
            </div>
            <div className="flex items-center gap-3 px-3.5 py-3">
              <div className="w-7 h-7 rounded-lg bg-violet-50 flex items-center justify-center flex-shrink-0">
                <svg className="w-3.5 h-3.5 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-gray-900">AI insights</div>
                <div className="text-xs text-gray-400">Portfolio, spending, and loans</div>
              </div>
            </div>
            <div className="flex items-center gap-3 px-3.5 py-3">
              <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-gray-900">Bank-level security</div>
                <div className="text-xs text-gray-400">SnapTrade · 256-bit encryption</div>
              </div>
            </div>
          </div>
          <button onClick={onConnect}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 border-t border-gray-100 text-[13px] font-medium text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Connect Accounts
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-5 border-b border-gray-100">
      <div className="flex items-center justify-between mb-3">
        <button onClick={onViewPortfolio} className="group flex items-center gap-1 text-sm font-semibold text-gray-900 hover:text-gray-700 transition-colors">
          Accounts
          <svg className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19.5 8.25-7.5 7.5-7.5-7.5" />
          </svg>
        </button>
        <button onClick={() => setEditing(e => !e)} className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors">
          {editing ? (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m4.5 12.75 6 6 9-13.5" />
              </svg>
              Done
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
              </svg>
              Edit
            </>
          )}
        </button>
      </div>

      <div className="rounded-xl border border-gray-200 overflow-hidden">
        {/* Brokerage accounts grouped by institution */}
        {hasBrokerage && externalPortfolio && (() => {
          const groups = new Map<string, typeof externalPortfolio.accounts>();
          for (const acct of externalPortfolio.accounts || []) {
            const inst = acct.institution || 'Brokerage';
            if (!groups.has(inst)) groups.set(inst, []);
            groups.get(inst)!.push(acct);
          }
          return Array.from(groups.entries()).map(([institution, accounts]) => {
            const groupValue = accounts.reduce((s, a) => s + a.total_value, 0);
            return (
              <InstitutionGroup key={institution}
                institution={institution}
                accounts={accounts}
                groupValue={groupValue}
                expanded={expandedInstitutions.has(institution)}
                editing={editing}
                onToggle={() => toggleInstitution(institution)}
                onSelectAccount={onSelectAccount}
                onDisconnect={onDisconnect}
                selectedAccountId={selectedAccountId}
              />
            );
          });
        })()}

        {/* Add Account button */}
        <button onClick={onConnect}
          className="w-full py-3 border-t border-gray-100 text-sm font-medium text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors text-center">
          + Add Account
        </button>
      </div>
    </div>
  );
}

// ── Watchlist Tab View ───────────────────────────────────────────────────────

function WatchlistTabView({ userId, watchlist, onWatchlistChange, onStockClick }: {
  userId: string; watchlist: any[]; onWatchlistChange: (wl: any[]) => void; onStockClick: (s: string) => void;
}) {
  const [addSymbol, setAddSymbol] = useState('');
  const [adding, setAdding] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showSearch, setShowSearch] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const searchRef = useRef<HTMLDivElement>(null);

  const handleSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setSearchResults([]); setShowSearch(false); return; }
    try {
      const data = await marketApi.searchStocks(q, 6);
      setSearchResults(Array.isArray(data) ? data : []);
      setShowSearch(true);
    } catch { setSearchResults([]); }
  }, []);

  const handleInputChange = (val: string) => {
    setAddSymbol(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => handleSearch(val), 250);
  };

  const handleAdd = async (symbol: string) => {
    setAdding(true);
    try {
      await watchlistApi.addSymbol(userId, symbol.toUpperCase());
      const data = await watchlistApi.getWatchlist(userId);
      onWatchlistChange(data.symbols || []);
      setAddSymbol('');
      setShowSearch(false);
    } catch { /* ignore */ }
    finally { setAdding(false); }
  };

  const handleRemove = async (symbol: string) => {
    onWatchlistChange(watchlist.filter(w => w.symbol !== symbol));
    try { await watchlistApi.removeSymbol(userId, symbol); }
    catch {
      const data = await watchlistApi.getWatchlist(userId);
      onWatchlistChange(data.symbols || []);
    }
  };

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setShowSearch(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Watchlist</h2>
      </div>

      {/* Add stock search */}
      <div ref={searchRef} className="relative mb-4">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              value={addSymbol}
              onChange={e => handleInputChange(e.target.value)}
              onFocus={() => addSymbol.trim() && setShowSearch(true)}
              onKeyDown={e => e.key === 'Enter' && addSymbol.trim() && handleAdd(addSymbol)}
              placeholder="Search & add stocks..."
              className="w-full pl-10 pr-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-gray-300 focus:bg-white transition-all"
            />
          </div>
        </div>

        {showSearch && searchResults.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden z-30 max-h-[280px] overflow-y-auto">
            {searchResults.map((item, i) => {
              const alreadyAdded = watchlist.some(w => w.symbol === item.symbol);
              return (
                <button key={i} disabled={alreadyAdded || adding}
                  onClick={() => handleAdd(item.symbol)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 last:border-b-0 disabled:opacity-50">
                  <div className="min-w-[52px]">
                    <span className="text-sm font-bold text-gray-900">{item.symbol}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-gray-500 truncate block">{item.name}</span>
                  </div>
                  <span className="text-xs text-gray-300">{alreadyAdded ? 'Added' : item.exchangeShortName}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Stock cards grid */}
      {watchlist.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {watchlist.map((item, i) => {
            const isUp = (item.changesPercentage || 0) >= 0;
            return (
              <div key={item.symbol || i}
                className="relative group p-4 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all bg-white">
                <button onClick={() => onStockClick(item.symbol)} className="w-full text-left">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="text-sm font-bold text-gray-900">{item.symbol}</div>
                      <div className="text-xs text-gray-400 truncate max-w-[140px]">{item.name || ''}</div>
                    </div>
                    <div className="text-right">
                      <div className={`text-sm font-bold tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
                        {fmtPct(item.changesPercentage || 0)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-end justify-between">
                    <div className="text-lg font-bold text-gray-900 tabular-nums">
                      {item.price != null ? fmt(item.price) : '--'}
                    </div>
                    <MiniSparkline symbol={item.symbol} width={80} height={32} days={30} />
                  </div>
                </button>
                {/* Remove button */}
                <button onClick={() => handleRemove(item.symbol)}
                  className="absolute top-2 right-2 p-1 rounded-lg text-gray-300 hover:text-red-400 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-xl border border-gray-100 bg-gray-50 flex flex-col items-center justify-center h-[200px] text-sm text-gray-400">
          <div className="mb-1">No stocks in your watchlist</div>
          <div className="text-xs">Search above to add stocks</div>
        </div>
      )}
    </div>
  );
}

// ── Portfolio Tab View ───────────────────────────────────────────────────────

function AccountDropdown({ accounts, selectedAccountId, accountCount, onSelect }: {
  accounts: any[]; selectedAccountId?: string | null; accountCount: number; onSelect: (id: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = selectedAccountId ? accounts.find(a => a.id === selectedAccountId) : null;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <span>{selected ? selected.name : `All accounts · ${accountCount}`}</span>
        <svg className={`w-3.5 h-3.5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1.5 bg-white rounded-xl shadow-lg border border-gray-200 py-1 z-30 min-w-[220px]">
          <button onClick={() => { onSelect(null); setOpen(false); }}
            className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left transition-colors ${
              !selectedAccountId ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'
            }`}>
            {!selectedAccountId && (
              <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z" clipRule="evenodd" />
              </svg>
            )}
            {selectedAccountId && <div className="w-4" />}
            All accounts &middot; {accountCount}
          </button>
          <div className="h-px bg-gray-100 my-1" />
          {accounts.map(a => (
            <button key={a.id} onClick={() => { onSelect(a.id); setOpen(false); }}
              className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left transition-colors ${
                selectedAccountId === a.id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'
              }`}>
              {selectedAccountId === a.id ? (
                <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z" clipRule="evenodd" />
                </svg>
              ) : <div className="w-4" />}
              {a.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function PortfolioTabView({ portfolio, externalPortfolio, hasBrokerage, onStockClick, selectedAccountId, onClearAccount, onSelectAccount }: {
  portfolio: AlpacaPortfolioResponse | null;
  externalPortfolio: PortfolioResponse | null;
  hasBrokerage: boolean;
  onStockClick: (s: string) => void;
  selectedAccountId?: string | null;
  onClearAccount?: () => void;
  onSelectAccount?: (id: string | null) => void;
}) {
  const selectedAccount = selectedAccountId
    ? externalPortfolio?.accounts?.find(a => a.id === selectedAccountId)
    : null;

  const positions = selectedAccount
    ? selectedAccount.positions
    : externalPortfolio?.accounts?.flatMap(a => a.positions) || [];
  const alpacaPositions = selectedAccount ? [] : (portfolio?.positions || []);
  const allPositions = [...positions, ...alpacaPositions.map(p => ({
    symbol: p.symbol,
    quantity: num(p.qty),
    price: num(p.current_price),
    value: num(p.market_value),
    average_purchase_price: num(p.avg_entry_price),
    total_cost: num(p.cost_basis),
    gain_loss: num(p.unrealized_pl),
    gain_loss_percent: num(p.unrealized_plpc) * 100,
  }))];

  const totalValue = selectedAccount
    ? selectedAccount.total_value
    : (externalPortfolio?.total_value || 0) + num(portfolio?.account?.equity);
  const totalCost = allPositions.reduce((sum, p) => sum + (p.total_cost || p.value), 0);
  const totalGainLoss = allPositions.reduce((sum, p) => sum + (p.gain_loss || 0), 0);
  const totalGainLossPct = totalCost > 0 ? (totalGainLoss / totalCost) * 100 : 0;
  const upCount = allPositions.filter(p => (p.gain_loss || 0) >= 0).length;
  const downCount = allPositions.length - upCount;

  const equity = num(portfolio?.account?.equity);
  const cash = num(portfolio?.account?.cash);
  const buyingPower = num(portfolio?.account?.buying_power);
  const longValue = num(portfolio?.account?.long_market_value);

  const accountCount = (externalPortfolio?.account_count || 0) + (portfolio ? 1 : 0);
  const headerLabel = selectedAccount ? selectedAccount.name : 'Net Worth';

  if (!hasBrokerage && !portfolio) {
    return (
      <div className="flex items-center justify-center h-[300px] text-sm text-gray-400">
        No portfolio connected. Link a brokerage account to see your holdings.
      </div>
    );
  }

  return (
    <div>
      {/* Net Worth / Account card */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm p-5 mb-5">
        {externalPortfolio && externalPortfolio.accounts && externalPortfolio.accounts.length > 1 ? (
          <div className="mb-1">
            <AccountDropdown
              accounts={externalPortfolio.accounts}
              selectedAccountId={selectedAccountId}
              accountCount={accountCount}
              onSelect={onSelectAccount!}
            />
          </div>
        ) : (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm text-gray-500">{headerLabel}</span>
            <span className="text-xs text-gray-400 bg-white px-2 py-0.5 rounded-full border border-gray-100">
              {accountCount} account{accountCount !== 1 ? 's' : ''}
            </span>
          </div>
        )}

        <div className="text-3xl font-bold text-gray-900 tabular-nums">{fmt(totalValue)}</div>
      </div>

      {/* Stats row */}
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Investment Holdings</h3>
      <div className="rounded-2xl border border-gray-200 shadow-sm p-4 mb-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-gray-400 mb-1">Total Gain/Loss</div>
            <div className={`text-lg font-bold tabular-nums ${totalGainLoss >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {totalGainLoss >= 0 ? '+' : ''}{fmt(totalGainLoss)}
            </div>
            <div className={`inline-flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded mt-1 ${
              totalGainLossPct >= 0 ? 'text-emerald-700 bg-emerald-50' : 'text-red-600 bg-red-50'
            }`}>
              <span>{totalGainLossPct >= 0 ? '↗' : '↘'}</span>
              {fmtPct(totalGainLossPct)}
            </div>
            <div className="text-xs text-gray-400 mt-1">{upCount} up, {downCount} down</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Total Value</div>
            <div className="text-lg font-bold text-gray-900 tabular-nums">{fmt(totalValue)}</div>
            <div className="text-xs text-gray-400 mt-1">{allPositions.length} holdings</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Cost Basis</div>
            <div className="text-lg font-bold text-gray-900 tabular-nums">{fmt(totalCost)}</div>
          </div>
          {(() => {
            const acctCash = selectedAccount
              ? selectedAccount.balance
              : externalPortfolio?.accounts?.reduce((sum, a) => sum + a.balance, 0) || 0;
            const showCash = selectedAccount ? acctCash > 0 : (hasBrokerage && acctCash > 0);
            return showCash ? (
              <div>
                <div className="text-xs text-gray-400 mb-1">Cash Balance</div>
                <div className="text-lg font-bold text-gray-900 tabular-nums">{fmt(acctCash)}</div>
              </div>
            ) : null;
          })()}
        </div>
      </div>

      {/* Holdings list */}
      {allPositions.length > 0 && (
        <div className="rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="divide-y divide-gray-100">
            {allPositions.sort((a, b) => b.value - a.value).map((p, i) => {
              const gl = p.gain_loss || 0;
              const glPct = p.gain_loss_percent || 0;
              const isUp = gl >= 0;
              return (
                <button key={`${p.symbol}-${i}`} onClick={() => onStockClick(p.symbol)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left">
                  <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-bold text-gray-500">{p.symbol.slice(0, 2)}</span>
                  </div>
                  <div className="min-w-[60px]">
                    <div className="text-sm font-semibold text-gray-900">{p.symbol}</div>
                    <div className="text-xs text-gray-400">
                      {p.quantity % 1 === 0 ? p.quantity : p.quantity.toFixed(2)} shares
                    </div>
                  </div>
                  <div className="flex-1 flex justify-center">
                    <MiniSparkline symbol={p.symbol} width={80} height={28} days={30} />
                  </div>
                  <div className="text-right min-w-[90px]">
                    <div className="text-sm font-semibold text-gray-900 tabular-nums">{fmt(p.price)}</div>
                    <div className={`text-xs font-medium tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
                      {gl >= 0 ? '+' : ''}{fmt(gl)} ({fmtPct(glPct)})
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Bottom Chat Bar ──────────────────────────────────────────────────────────

function BottomChatBar({ onSend }: { onSend: (msg: string) => void }) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (!message.trim()) return;
    onSend(message);
    setMessage('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="shrink-0 border-t border-gray-100 bg-white px-4 py-3">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2 focus-within:border-gray-300 focus-within:bg-white focus-within:shadow-sm transition-all">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={e => {
              setMessage(e.target.value);
              const t = e.target;
              t.style.height = 'auto';
              t.style.height = Math.min(t.scrollHeight, 120) + 'px';
            }}
            onKeyDown={handleKeyDown}
            placeholder="Ask about stocks, portfolio, markets..."
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-gray-900 placeholder-gray-400 focus:outline-none py-1.5 leading-relaxed"
            style={{ minHeight: '28px', maxHeight: '120px' }}
          />
          <button onClick={handleSubmit} disabled={!message.trim()}
            className="flex-shrink-0 p-2 rounded-xl bg-gray-900 text-white hover:bg-gray-800 disabled:bg-gray-200 disabled:text-gray-400 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Market Summary (news) ────────────────────────────────────────────────────

function MarketSummarySection({ news, onStockClick }: { news: any[]; onStockClick: (s: string) => void }) {
  if (news.length === 0) return null;
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-900">Market Summary</h2>
        <span className="text-xs text-gray-400">Updated just now</span>
      </div>
      <div className="space-y-3">
        {news.slice(0, 4).map((n, i) => (
          <a key={i} href={n.url} target="_blank" rel="noopener noreferrer"
            className="block p-3 rounded-xl border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all bg-white">
            <div className="text-sm font-medium text-gray-900 leading-snug line-clamp-2 mb-1">{n.title}</div>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              {n.symbol && (
                <button onClick={e => { e.preventDefault(); onStockClick(n.symbol); }}
                  className="font-semibold text-gray-600 hover:text-gray-900">{n.symbol}</button>
              )}
              <span>{n.site}</span>
              {n.publishedDate && (
                <span>{new Date(n.publishedDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

// ── Connect Modal (for homepage) ─────────────────────────────────────────────

function BrokerLogo({ logo, name }: { logo: string; name: string }) {
  const [failed, setFailed] = useState(false);
  if (logo?.startsWith('http') && !failed) {
    return <img src={logo} alt={name} width={40} height={40} className="w-10 h-10 rounded-lg object-contain bg-gray-50" onError={() => setFailed(true)} />;
  }
  return (
    <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-base font-bold text-gray-400">
      {name.charAt(0)}
    </div>
  );
}

function HomeConnectModal({ brokerages, connecting, selectedBroker, onConnect, onClose }: {
  brokerages: Brokerage[];
  connecting: boolean;
  selectedBroker: string | null;
  onConnect: (id: string) => void;
  onClose: () => void;
}) {
  const [search, setSearch] = useState('');
  const filtered = brokerages.filter(b => b.name.toLowerCase().startsWith(search.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full overflow-hidden transition-all max-w-xl max-h-[80vh]"
        onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 flex items-center justify-between border-b border-gray-100">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Connect a brokerage</h3>
            <p className="text-sm text-gray-500 mt-0.5">Select your broker to securely link your account</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg p-1.5 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-5 pt-4 pb-2">
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <input
              type="text"
              placeholder="Search brokerages..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-gray-300 focus:bg-white transition-colors"
              autoFocus
            />
          </div>
        </div>
        <div className="px-5 pb-5 overflow-y-auto max-h-[calc(80vh-140px)]">
          {brokerages.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-400">No brokerages match &ldquo;{search}&rdquo;</div>
          ) : (
            <div className="space-y-1">
              {filtered.map(broker => {
                const isThis = connecting && selectedBroker === broker.id;
                const isOther = connecting && selectedBroker !== broker.id;
                return (
                  <button key={broker.id} onClick={() => onConnect(broker.id)} disabled={isOther}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-left ${
                      isThis ? 'bg-emerald-50 ring-1 ring-emerald-200' : 'hover:bg-gray-50'
                    } ${isOther ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}>
                    <BrokerLogo logo={broker.logo} name={broker.name} />
                    <span className="text-sm font-medium text-gray-900 flex-1">{broker.name}</span>
                    {isThis ? (
                      <div className="flex items-center gap-1.5">
                        <div className="w-3.5 h-3.5 border-2 border-emerald-200 border-t-emerald-500 rounded-full animate-spin" />
                        <span className="text-xs text-emerald-600 font-medium">Connecting...</span>
                      </div>
                    ) : (
                      <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                      </svg>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function HomePage() {
  const { user } = useAuth();
  const { openStock, openChatWithPrompt, startNewChat, navigateTo } = useNavigation();

  const [market, setMarket] = useState<Market>('us');
  const [activeTab, setActiveTab] = useState<HomeTab>('markets');
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [indexQuotes, setIndexQuotes] = useState<Record<string, any>>({});
  const [movers, setMovers] = useState<{ gainers: any[]; losers: any[] }>({ gainers: [], losers: [] });
  const [news, setNews] = useState<any[]>([]);
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [portfolio, setPortfolio] = useState<AlpacaPortfolioResponse | null>(null);
  const [externalPortfolio, setExternalPortfolio] = useState<PortfolioResponse | null>(null);
  const [hasAccount, setHasAccount] = useState<boolean | null>(null);
  const [hasBrokerage, setHasBrokerage] = useState(false);
  const [loading, setLoading] = useState(true);

  const [showConnectModal, setShowConnectModal] = useState(false);
  const [brokerages, setBrokerages] = useState<Brokerage[]>([]);
  const [connectingBroker, setConnectingBroker] = useState(false);
  const [selectedBroker, setSelectedBroker] = useState<string | null>(null);
  const [iframeUrl, setIframeUrl] = useState<string | null>(null);

  const indices = market === 'us' ? US_INDICES : INDIA_INDICES;

  useEffect(() => {
    if (!user) return;
    const allSymbols = [...US_INDICES, ...INDIA_INDICES].map(i => i.symbol);

    Promise.all([
      marketApi.getBatchQuotes(allSymbols).catch(() => []),
      marketApi.getMovers().catch(() => ({ gainers: [], losers: [] })),
      marketApi.getGeneralNews(6).catch(() => []),
      watchlistApi.getWatchlist(user.id).catch(() => ({ symbols: [] })),
      alpacaBrokerApi.getAccountStatus(user.id).catch(() => ({ exists: false })),
      snaptradeApi.checkStatus(user.id).catch(() => ({ is_connected: false })),
    ]).then(([quotes, m, n, wl, status, brokerage]) => {
      const quoteMap: Record<string, any> = {};
      if (Array.isArray(quotes)) quotes.forEach((q: any) => { quoteMap[q.symbol] = q; });
      setIndexQuotes(quoteMap);
      setMovers({ gainers: m.gainers || [], losers: m.losers || [] });
      setNews(Array.isArray(n) ? n : []);
      setWatchlist(wl.symbols || []);

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
    }).finally(() => setLoading(false));
  }, [user]);

  const handleDisconnectAccount = useCallback(async (accountId: string, accountName: string) => {
    if (!user?.id) return;
    if (!confirm(`Disconnect ${accountName}? This will remove it from your portfolio.`)) return;

    setExternalPortfolio(prev => {
      if (!prev) return prev;
      const remaining = prev.accounts.filter(a => a.id !== accountId);
      if (!remaining.length) { setHasBrokerage(false); return null; }
      return { ...prev, accounts: remaining, account_count: remaining.length };
    });

    try {
      await snaptradeApi.disconnectAccount(user.id, accountId);
    } catch (e) {
      console.error('Failed to disconnect account:', e);
    }

    try {
      const res = await snaptradeApi.getPortfolio(user.id);
      if (res?.success) {
        setExternalPortfolio(res);
        if (!res.accounts?.length) setHasBrokerage(false);
      }
    } catch {}
  }, [user?.id]);

  const handleChatSend = useCallback((msg: string) => {
    openChatWithPrompt(msg, 'Your question');
  }, [openChatWithPrompt]);

  const handleTabChange = useCallback((tab: HomeTab) => {
    setActiveTab(tab);
  }, []);

  const openConnectModal = useCallback(async () => {
    setShowConnectModal(true);
    if (brokerages.length === 0) {
      const res = await snaptradeApi.getBrokerages().catch(() => null);
      if (res?.success) setBrokerages(res.brokerages);
    }
  }, [brokerages.length]);

  const handleConnectBroker = useCallback(async (brokerId: string) => {
    if (!user?.id) return;
    setConnectingBroker(true);
    setSelectedBroker(brokerId);
    try {
      const redirectUri = `${window.location.origin}/snaptrade/callback`;
      const response = await snaptradeApi.connectBroker(user.id, redirectUri, brokerId);
      if (response.success && response.redirect_uri) {
        setShowConnectModal(false);
        setIframeUrl(response.redirect_uri);
      } else {
        setConnectingBroker(false);
        setSelectedBroker(null);
      }
    } catch {
      setConnectingBroker(false);
      setSelectedBroker(null);
    }
  }, [user?.id]);

  const handleSnapTradeSuccess = useCallback(async () => {
    setIframeUrl(null);
    setConnectingBroker(false);
    setSelectedBroker(null);
    if (!user?.id) return;
    try {
      await snaptradeApi.handleCallback(user.id);
    } catch {}
    setHasBrokerage(true);
    snaptradeApi.getPortfolio(user.id).then(setExternalPortfolio).catch(() => {});
    snaptradeApi.buildPortfolioHistory(user.id, undefined, true).catch(() => {});
  }, [user?.id]);

  const handleSnapTradeClose = useCallback(() => {
    setIframeUrl(null);
    setConnectingBroker(false);
    setSelectedBroker(null);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  const equity = num(portfolio?.account?.equity);
  const lastEquity = num(portfolio?.account?.last_equity);
  const dayChange = equity - lastEquity;
  const dayChangePct = lastEquity > 0 ? (dayChange / lastEquity) * 100 : 0;

  return (
    <div className="flex flex-col h-full bg-white">
      {/* ── Top Nav Bar ─────────────────────────────────────────────── */}
      <TopNavBar market={market} onMarketChange={setMarket} activeTab={activeTab} onTabChange={handleTabChange} />

      <div className="flex-1 overflow-y-auto">
        <div className="flex gap-0 h-full">
          {/* ── Left: Main Content ─────────────────────────────────────── */}
          <div className="flex-1 min-w-0 px-5 py-4 overflow-y-auto">
            {activeTab === 'markets' && (
              <>
                {/* Top Assets — 2x2 grid */}
                <div className="mb-6">
                  <h2 className="text-sm font-semibold text-gray-900 mb-3">Top Assets</h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {indices.map(idx => (
                      <IndexCard
                        key={idx.symbol}
                        symbol={idx.symbol}
                        label={idx.label}
                        quote={indexQuotes[idx.symbol]}
                        onClick={() => openStock(idx.symbol)}
                      />
                    ))}
                  </div>
                </div>

                {/* Market movers — compact horizontal list */}
                {movers.gainers.length > 0 && market === 'us' && (
                  <div className="mb-6">
                    <h2 className="text-sm font-semibold text-gray-900 mb-3">Top Movers</h2>
                    <div className="flex gap-2 overflow-x-auto scrollbar-none pb-1">
                      {movers.gainers.slice(0, 6).map((item, i) => {
                        const isUp = (item.changesPercentage || 0) >= 0;
                        return (
                          <button key={i} onClick={() => openStock(item.symbol)}
                            className="flex-shrink-0 flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-100 hover:border-gray-200 transition-all bg-white">
                            <span className="text-sm font-bold text-gray-900">{item.symbol}</span>
                            <span className={`text-xs font-semibold tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
                              {fmtPct(item.changesPercentage || 0)}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Market Summary / News */}
                <MarketSummarySection news={news} onStockClick={openStock} />
              </>
            )}

            {activeTab === 'earnings' && (
              <EarningsCalendar onStockClick={(s) => openStock(s, 'earnings')} market={market} />
            )}

            {activeTab === 'watchlist' && (
              <WatchlistTabView
                userId={user!.id}
                watchlist={watchlist}
                onWatchlistChange={setWatchlist}
                onStockClick={openStock}
              />
            )}

            {activeTab === 'portfolio' && (
              <PortfolioTabView
                portfolio={portfolio}
                externalPortfolio={externalPortfolio}
                hasBrokerage={hasBrokerage}
                onStockClick={openStock}
                selectedAccountId={selectedAccountId}
                onClearAccount={() => setSelectedAccountId(null)}
                onSelectAccount={setSelectedAccountId}
              />
            )}
          </div>

          {/* ── Right: Sidebar ──────────────────────────────────────────── */}
          <div className="hidden lg:block w-[340px] border-l border-gray-100 overflow-y-auto flex-shrink-0 pr-2">
            {/* Accounts */}
            <AccountsSidebar
              hasBrokerage={hasBrokerage}
              externalPortfolio={externalPortfolio}
              hasAccount={!!hasAccount}
              portfolio={portfolio}
              equity={equity}
              onConnect={openConnectModal}
              onDisconnect={handleDisconnectAccount}
              onViewPortfolio={() => { setSelectedAccountId(null); setActiveTab('portfolio'); }}
              onSelectAccount={(id) => { setSelectedAccountId(id); setActiveTab('portfolio'); }}
              selectedAccountId={selectedAccountId}
            />

            {/* Watchlist */}
            <div className="p-4 border-b border-gray-100">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-semibold text-gray-900">Watchlist</h2>
                <button onClick={() => navigateTo({ type: 'watchlist' })}
                  className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" />
                  </svg>
                </button>
              </div>

              {watchlist.length > 0 ? (
                <div className="-mx-4">
                  {watchlist.slice(0, 8).map((item, i) => (
                    <WatchlistItem key={item.symbol || i} item={item} onClick={() => openStock(item.symbol)} />
                  ))}
                  {watchlist.length > 8 && (
                    <button onClick={() => navigateTo({ type: 'watchlist' })}
                      className="w-full py-2 text-xs text-gray-400 hover:text-gray-600 text-center transition-colors">
                      View all ({watchlist.length})
                    </button>
                  )}
                </div>
              ) : (
                <div className="text-center py-6">
                  <div className="text-xs text-gray-400 mb-2">No stocks in watchlist</div>
                  <button onClick={() => navigateTo({ type: 'watchlist' })}
                    className="text-xs font-medium text-gray-600 hover:text-gray-900 transition-colors">
                    Add stocks
                  </button>
                </div>
              )}
            </div>

            {/* Quick Actions */}
            <div className="p-4">
              <h2 className="text-sm font-semibold text-gray-900 mb-3">Quick Actions</h2>
              <div className="space-y-2">
                {hasBrokerage && (
                  <button onClick={() => openChatWithPrompt(PORTFOLIO_REVIEW_PROMPT, 'Review my portfolio')}
                    className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-gray-100 hover:border-gray-200 hover:bg-gray-50 transition-all text-left text-sm text-gray-700">
                    <svg className="w-4 h-4 text-violet-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
                    </svg>
                    Review portfolio
                  </button>
                )}
                <button onClick={() => openChatWithPrompt('What are the top stock picks for today? Analyze current market conditions and suggest 3-5 actionable trades.', 'Find trades')}
                  className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-gray-100 hover:border-gray-200 hover:bg-gray-50 transition-all text-left text-sm text-gray-700">
                  <svg className="w-4 h-4 text-emerald-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
                  </svg>
                  Find trade ideas
                </button>
                <button onClick={() => openChatWithPrompt('Give me a market overview. What are the major indices doing? Any notable earnings, economic data, or news moving the market today?', 'Market overview')}
                  className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-gray-100 hover:border-gray-200 hover:bg-gray-50 transition-all text-left text-sm text-gray-700">
                  <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
                  </svg>
                  Market overview
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom Chat Bar ──────────────────────────────────────────── */}
      <BottomChatBar onSend={handleChatSend} />

      {showConnectModal && <HomeConnectModal
        brokerages={brokerages}
        connecting={connectingBroker}
        selectedBroker={selectedBroker}
        onConnect={handleConnectBroker}
        onClose={() => { setShowConnectModal(false); setConnectingBroker(false); setSelectedBroker(null); }}
      />}

      <SnapTradeReact
        loginLink={iframeUrl || ''}
        isOpen={!!iframeUrl}
        close={handleSnapTradeClose}
        onSuccess={handleSnapTradeSuccess}
        onError={() => handleSnapTradeClose()}
        onExit={() => handleSnapTradeClose()}
      />
    </div>
  );
}
