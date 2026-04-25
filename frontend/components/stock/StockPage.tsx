'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import { marketApi, alpacaBrokerApi, watchlistApi, memoryApi } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import PriceRangeChart, { getStockRanges } from '@/components/ui/PriceRangeChart';
import type { AlpacaBrokerPosition } from '@/lib/types';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}
function fmtB(n: number) {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  return fmt(n);
}
function fmtN(n: number) {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString();
}
function pct(n: number) { return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`; }

// ─── Trade Panel (inline on desktop, modal on mobile) ────────────────────────

function TradePanel({ symbol, price, userId, onSuccess }: {
  symbol: string; price: number; userId: string; onSuccess: () => void;
}) {
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [qty, setQty] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const est = parseFloat(qty || '0') * price;

  const submit = async () => {
    if (!qty || parseFloat(qty) <= 0) { setError('Enter shares'); return; }
    setLoading(true); setError('');
    try {
      await alpacaBrokerApi.placeOrder(userId, { symbol, side, qty: parseFloat(qty), order_type: 'market', time_in_force: 'day' });
      setDone(true);
      setTimeout(() => { setDone(false); setQty(''); onSuccess(); }, 1500);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Order failed'); }
    finally { setLoading(false); }
  };

  return (
    <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
      {/* Buy / Sell tabs */}
      <div className="flex border-b border-gray-100">
        {(['buy', 'sell'] as const).map(s => (
          <button key={s} onClick={() => setSide(s)}
            className={`flex-1 py-2.5 text-sm font-bold transition-colors ${
              side === s
                ? s === 'buy' ? 'text-emerald-600 border-b-2 border-emerald-500' : 'text-red-500 border-b-2 border-red-500'
                : 'text-gray-400'
            }`}>
            {s === 'buy' ? `Buy ${symbol}` : `Sell ${symbol}`}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">Order type</span>
          <span className="text-sm font-medium text-gray-900">Market</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">Shares</span>
          <input type="number" value={qty} onChange={e => setQty(e.target.value)} placeholder="0"
            min="0" step="1"
            className="w-20 text-right text-sm font-medium border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-300 tabular-nums" />
        </div>
        <div className="flex items-center justify-between pt-1 border-t border-gray-100">
          <span className="text-sm text-emerald-600 font-medium">Market price</span>
          <span className="text-sm font-bold text-gray-900 tabular-nums">{fmt(price)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">Estimated {side === 'buy' ? 'cost' : 'credit'}</span>
          <span className="text-sm font-bold text-gray-900 tabular-nums">{fmt(est)}</span>
        </div>

        {error && <div className="text-xs text-red-500 font-medium">{error}</div>}

        <button onClick={submit} disabled={loading || done}
          className={`w-full py-2.5 text-sm font-bold text-white rounded-xl transition-all disabled:opacity-50 ${
            done ? 'bg-emerald-500' : ''
          }`}
          style={!done ? { background: side === 'buy' ? 'linear-gradient(135deg, #059669, #10b981)' : 'linear-gradient(135deg, #dc2626, #ef4444)' } : {}}>
          {done ? 'Order placed!' : loading ? 'Placing...' : 'Trade now'}
        </button>
      </div>
    </div>
  );
}

// ─── Stat cell ───────────────────────────────────────────────────────────────

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="py-3 border-b border-gray-100">
      <div className="text-xs text-gray-400 mb-0.5">{label}</div>
      <div className="text-sm font-semibold text-gray-900 tabular-nums">{value}</div>
    </div>
  );
}

// ─── News card ───────────────────────────────────────────────────────────────

function NewsCard({ item }: { item: any }) {
  const title = item.title || '';
  const url = item.url || '#';
  const site = item.site || item.source || '';
  const date = item.publishedDate || item.date || '';
  const snippet = item.text || '';
  if (!title) return null;

  const timeAgo = (() => {
    if (!date) return '';
    const diff = Date.now() - new Date(date).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
  })();

  return (
    <a href={url} target="_blank" rel="noopener noreferrer"
      className="flex gap-4 px-4 sm:px-0 py-4 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 text-xs text-gray-400 mb-1.5">
          {site && <span className="font-medium">{site}</span>}
          {timeAgo && <span>{timeAgo}</span>}
        </div>
        <div className="text-sm font-semibold text-gray-900 leading-snug mb-1.5 line-clamp-2">{title}</div>
        {snippet && <div className="text-xs text-gray-400 line-clamp-2 leading-relaxed">{snippet}</div>}
      </div>
      {item.image && (
        <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-xl bg-gray-100 overflow-hidden flex-shrink-0">
          <img src={item.image} alt="" className="w-full h-full object-cover" onError={e => (e.currentTarget.style.display = 'none')} />
        </div>
      )}
    </a>
  );
}

// ─── Main ────────────────────────────────────────────────────────────────────

export default function StockPage({ symbol }: { symbol: string }) {
  const { goBack, canGoBack, openChatAbout, openStock } = useNavigation();
  const { user } = useAuth();
  const [quote, setQuote] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [news, setNews] = useState<any[]>([]);
  const [peers, setPeers] = useState<any[]>([]);
  const [position, setPosition] = useState<AlpacaBrokerPosition | null>(null);
  const [loading, setLoading] = useState(true);
  const [watchlisted, setWatchlisted] = useState(false);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [hasAccount, setHasAccount] = useState(false);
  const [showMobileTrade, setShowMobileTrade] = useState(false);
  const [hoverPct, setHoverPct] = useState<number | null>(null);
  const [periodPct, setPeriodPct] = useState<number | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setPosition(null);
    Promise.all([
      marketApi.getQuote(symbol).catch(() => null),
      marketApi.getProfile(symbol).catch(() => null),
      marketApi.getNews(symbol, 8).catch(() => []),
      marketApi.getPeers(symbol, 6).catch(() => []),
      user ? alpacaBrokerApi.getPortfolio(user.id).catch(() => null) : null,
      user ? watchlistApi.getWatchlist(user.id).catch(() => ({ symbols: [] })) : null,
      user ? alpacaBrokerApi.getAccountStatus(user.id).catch(() => ({ exists: false })) : null,
    ]).then(([q, p, n, pe, portfolio, wl, status]) => {
      setQuote(q);
      setProfile(p);
      setNews(Array.isArray(n) ? n : []);
      setPeers(Array.isArray(pe) ? pe : []);
      if (portfolio?.positions) {
        const pos = portfolio.positions.find((x: any) => x.symbol === symbol);
        if (pos) setPosition(pos);
      }
      if (wl?.symbols) setWatchlisted(wl.symbols.some((s: any) => s.symbol === symbol));
      const st = status as any;
      setHasAccount(st?.exists && st?.status === 'ACTIVE');
    }).finally(() => setLoading(false));
  }, [symbol, user]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (user && symbol) {
      memoryApi.seedStock(symbol).catch(() => {});
    }
  }, [symbol, user]);

  const price = quote?.price || profile?.price || 0;
  const change = quote?.change || profile?.changes || 0;
  const changePct = quote?.changesPercentage || 0;
  const name = profile?.companyName || quote?.name || symbol;

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-full bg-white">
      {/* Main content (scrollable) */}
      <div className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="px-4 sm:px-6 pt-4 pb-2">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {canGoBack && (
                <button onClick={goBack} className="p-1 -ml-1 text-gray-400 hover:text-gray-600 transition-colors">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                  </svg>
                </button>
              )}
              <div>
                <div className="text-lg sm:text-xl font-bold text-gray-900">{name}</div>
                <div className="text-xs text-gray-400">{symbol}{profile?.exchange ? ` · ${profile.exchange}` : ''}</div>
              </div>
            </div>
            <button onClick={async () => {
              if (!user || watchlistLoading) return;
              setWatchlistLoading(true);
              try {
                if (watchlisted) { await watchlistApi.removeSymbol(user.id, symbol); setWatchlisted(false); }
                else { await watchlistApi.addSymbol(user.id, symbol); setWatchlisted(true); }
              } catch {} finally { setWatchlistLoading(false); }
            }}
              className={`p-2 rounded-lg transition-colors ${watchlisted ? 'text-amber-500' : 'text-gray-300 hover:text-gray-500'}`}>
              <svg className="w-5 h-5" fill={watchlisted ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
              </svg>
            </button>
          </div>

          {/* Price — updates on chart hover like Robinhood */}
          {(() => {
            // Period start price derived from current price and period's total % change
            const endPct = periodPct ?? changePct;
            const periodStart = price / (1 + endPct / 100 || 1);
            const activePct = hoverPct ?? endPct;
            const displayPrice = hoverPct !== null
              ? periodStart * (1 + hoverPct / 100)
              : price;
            const displayDollar = periodStart * (activePct / 100);
            const up = displayDollar >= 0;
            return (
              <>
                <div className="mb-1">
                  <span className="text-3xl sm:text-4xl font-bold text-gray-900 tabular-nums">{fmt(displayPrice)}</span>
                </div>
                <div className={`text-sm font-medium tabular-nums mb-1 ${up ? 'text-emerald-600' : 'text-red-500'}`}>
                  {up ? '+' : '-'}{fmt(Math.abs(displayDollar))} ({pct(activePct)})
                </div>
              </>
            );
          })()}
        </div>

        {/* Chart */}
        <div className="px-2 sm:px-4">
          <PriceRangeChart
            series={[{ symbol, color: '#10b981' }]}
            currentPrice={price}
            defaultDays={1}
            ranges={getStockRanges()}
            height={280}
            hideHeader
            onHoverChange={info => {
              setHoverPct(info?.value ?? null);
            }}
            onPeriodChange={setPeriodPct}
          />
        </div>

        {/* Mobile trade buttons */}
        <div className="lg:hidden px-4 py-3 flex gap-2">
          <button onClick={() => setShowMobileTrade(true)}
            className="flex-1 py-3 text-sm font-bold text-white rounded-xl"
            style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
            Buy
          </button>
          <button onClick={() => setShowMobileTrade(true)}
            className="flex-1 py-3 text-sm font-bold text-white rounded-xl"
            style={{ background: 'linear-gradient(135deg, #dc2626, #ef4444)' }}>
            Sell
          </button>
          <button onClick={() => openChatAbout(symbol)}
            className="px-4 py-3 text-sm font-bold text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors">
            Ask AI
          </button>
        </div>

        {/* Your position */}
        {position && (
          <div className="mx-4 sm:mx-6 mb-5 rounded-xl border border-emerald-100 bg-emerald-50/30 p-4">
            <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Your Position</div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold text-gray-900 tabular-nums">{fmt(parseFloat(position.market_value || '0'))}</div>
                <div className="text-xs text-gray-400">
                  {parseFloat(position.qty || '0')} shares @ {fmt(parseFloat(position.avg_entry_price || '0'))}
                </div>
              </div>
              <div className="text-right">
                <div className={`text-sm font-bold tabular-nums ${parseFloat(position.unrealized_pl || '0') >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {parseFloat(position.unrealized_pl || '0') >= 0 ? '+' : ''}{fmt(parseFloat(position.unrealized_pl || '0'))}
                </div>
                <div className={`text-xs tabular-nums ${parseFloat(position.unrealized_plpc || '0') >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {pct(parseFloat(position.unrealized_plpc || '0') * 100)}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* About */}
        {profile && (
          <div className="px-4 sm:px-6 mb-5">
            <div className="text-base font-bold text-gray-900 mb-3">About</div>
            <div className="border-t border-gray-100" />
            {profile.description && (
              <div className="text-sm text-gray-600 leading-relaxed py-3 border-b border-gray-100">
                {profile.description}
              </div>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 py-2">
              {profile.ceo && <Stat label="CEO" value={profile.ceo} />}
              {profile.fullTimeEmployees && <Stat label="Employees" value={fmtN(profile.fullTimeEmployees)} />}
              {(profile.city || profile.state) && <Stat label="Headquarters" value={[profile.city, profile.state].filter(Boolean).join(', ')} />}
              {profile.ipoDate && <Stat label="IPO Date" value={profile.ipoDate} />}
            </div>
            {profile.sector && (
              <div className="flex flex-wrap gap-2 pt-2">
                <span className="text-xs bg-gray-100 text-gray-500 px-2.5 py-1 rounded-full">{profile.sector}</span>
                {profile.industry && <span className="text-xs bg-gray-100 text-gray-500 px-2.5 py-1 rounded-full">{profile.industry}</span>}
              </div>
            )}
          </div>
        )}

        {/* Key Statistics */}
        {quote && (
          <div className="px-4 sm:px-6 mb-5">
            <div className="text-base font-bold text-gray-900 mb-3">Key Statistics</div>
            <div className="border-t border-gray-100" />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6">
              <Stat label="Market Cap" value={fmtB(quote.marketCap || profile?.mktCap || 0)} />
              <Stat label="P/E Ratio" value={quote.pe ? quote.pe.toFixed(2) : '--'} />
              {(quote.dividendYielPercentageTTM || profile?.lastDiv) && (
                <Stat label="Dividend Yield" value={quote.dividendYielPercentageTTM ? `${quote.dividendYielPercentageTTM.toFixed(2)}%` : profile?.lastDiv ? `$${profile.lastDiv.toFixed(2)}` : '--'} />
              )}
              <Stat label="Avg Volume" value={fmtN(quote.avgVolume || 0)} />
              <Stat label="High Today" value={fmt(quote.dayHigh || 0)} />
              <Stat label="Low Today" value={fmt(quote.dayLow || 0)} />
              <Stat label="Open" value={fmt(quote.open || 0)} />
              <Stat label="Volume" value={fmtN(quote.volume || 0)} />
              <Stat label="52 Week High" value={fmt(quote.yearHigh || 0)} />
              <Stat label="52 Week Low" value={fmt(quote.yearLow || 0)} />
              <Stat label="EPS" value={quote.eps ? `$${quote.eps.toFixed(2)}` : '--'} />
              {profile?.beta && <Stat label="Beta" value={profile.beta.toFixed(2)} />}
            </div>
          </div>
        )}

        {/* Related */}
        {peers.length > 0 && (
          <div className="px-4 sm:px-6 mb-5">
            <div className="text-base font-bold text-gray-900 mb-3">Related Stocks</div>
            <div className="border-t border-gray-100 mb-3" />
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {peers.map(p => (
                <button key={p.symbol} onClick={() => openStock(p.symbol)}
                  className="text-left rounded-xl border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/30 p-3 transition-colors">
                  <div className="text-sm font-bold text-gray-900">{p.symbol}</div>
                  {p.name && <div className="text-xs text-gray-400 truncate mb-1.5">{p.name}</div>}
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm font-semibold text-gray-900 tabular-nums">{p.price != null ? fmt(p.price) : '--'}</span>
                    {p.marketCap != null && (
                      <span className="text-xs font-medium text-gray-400 tabular-nums">{fmtB(p.marketCap)}</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* News */}
        {news.length > 0 && (
          <div className="px-4 sm:px-6 mb-5">
            <div className="text-base font-bold text-gray-900 mb-3">News</div>
            <div className="border-t border-gray-100" />
            {news.map((item, i) => <NewsCard key={i} item={item} />)}
          </div>
        )}

        <div className="h-20 md:h-8" />
      </div>

      {/* Desktop right sidebar */}
      {user && (
        <aside className="hidden lg:flex flex-col w-[320px] shrink-0 border-l border-gray-100 overflow-y-auto">
          {hasAccount && (
            <div className="p-5 border-b border-gray-100">
              <TradePanel symbol={symbol} price={price} userId={user.id} onSuccess={fetchData} />
            </div>
          )}

          <div className="p-5 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                style={{ background: 'linear-gradient(135deg, #ecfdf5, #d1fae5)' }}>
                <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
                </svg>
              </div>
              <div className="text-sm font-bold text-gray-900 tracking-tight">AI Analyst</div>
            </div>
            <p className="text-xs text-gray-500 leading-relaxed mb-4">
              Ask anything about {symbol} — fundamentals, price action, news, or peers.
            </p>

            <div className="space-y-1.5 mb-4">
              {[
                `What's moving ${symbol} today?`,
                `Summarize the latest news on ${symbol}`,
                `How does ${symbol} compare to its peers?`,
                `What are the key risks for ${symbol}?`,
              ].map(prompt => (
                <button key={prompt} onClick={() => openChatAbout(symbol, prompt)}
                  className="group w-full text-left text-[13px] text-gray-600 hover:text-gray-900 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-between gap-2">
                  <span className="line-clamp-1">{prompt}</span>
                  <svg className="w-3.5 h-3.5 text-gray-300 group-hover:text-emerald-500 shrink-0 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                  </svg>
                </button>
              ))}
            </div>

            <button onClick={() => openChatAbout(symbol)}
              className="w-full py-2.5 text-sm font-semibold text-white rounded-xl transition-all hover:shadow-md flex items-center justify-center gap-2"
              style={{ background: 'linear-gradient(135deg, #0f172a, #1f2937)' }}>
              Start analysis
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </button>
          </div>
        </aside>
      )}

      {/* Mobile trade modal */}
      {showMobileTrade && user && (
        <div className="fixed inset-0 z-50 flex items-end justify-center" style={{ background: 'rgba(0,0,0,0.4)' }} onClick={() => setShowMobileTrade(false)}>
          <div className="w-full max-w-md bg-white rounded-t-2xl shadow-2xl p-4 pb-8 safe-area-bottom" onClick={e => e.stopPropagation()}>
            <div className="w-8 h-1 bg-gray-300 rounded-full mx-auto mb-3" />
            <TradePanel symbol={symbol} price={price} userId={user.id} onSuccess={() => { setShowMobileTrade(false); fetchData(); }} />
          </div>
        </div>
      )}
    </div>
  );
}
