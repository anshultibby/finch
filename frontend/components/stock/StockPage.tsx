'use client';

import React, { useEffect, useState } from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import { marketApi, alpacaBrokerApi, watchlistApi } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import PriceRangeChart from '@/components/ui/PriceRangeChart';
import type { AlpacaBrokerPosition } from '@/lib/types';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function formatCurrency(n: number) {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function formatNumber(n: number) {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString();
}

function formatPct(n: number) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Trade modal (inline, simple)
// ─────────────────────────────────────────────────────────────────────────────

function QuickTradeModal({ symbol, side, price, userId, onClose, onSuccess }: {
  symbol: string; side: 'buy' | 'sell'; price: number; userId: string;
  onClose: () => void; onSuccess: () => void;
}) {
  const [qty, setQty] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const estimatedCost = parseFloat(qty || '0') * price;

  const handleSubmit = async () => {
    if (!qty || parseFloat(qty) <= 0) { setError('Enter a valid quantity'); return; }
    setLoading(true); setError('');
    try {
      await alpacaBrokerApi.placeOrder(userId, { symbol, side, qty: parseFloat(qty), order_type: 'market', time_in_force: 'day' });
      setDone(true);
      setTimeout(() => { onSuccess(); onClose(); }, 1000);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Order failed');
    } finally { setLoading(false); }
  };

  if (done) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.4)' }}>
        <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm text-center">
          <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center mx-auto mb-3">
            <svg className="w-6 h-6 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div className="font-semibold text-gray-900">Order placed!</div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center px-4 pb-4 sm:pb-0" style={{ background: 'rgba(0,0,0,0.4)' }} onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-center justify-between mb-4">
            <div className="font-bold text-gray-900">{side === 'buy' ? 'Buy' : 'Sell'} {symbol}</div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-gray-500 mb-1">Shares</label>
            <input type="number" value={qty} onChange={e => setQty(e.target.value)} placeholder="0"
              min="0" step="1" autoFocus
              className="w-full px-3 py-3 text-lg font-bold border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 tabular-nums" />
          </div>

          {parseFloat(qty) > 0 && (
            <div className="flex items-center justify-between text-sm text-gray-500 mb-4 px-1">
              <span>Estimated {side === 'buy' ? 'cost' : 'proceeds'}</span>
              <span className="font-semibold text-gray-900 tabular-nums">{formatCurrency(estimatedCost)}</span>
            </div>
          )}

          {error && <div className="text-xs text-red-500 font-medium mb-3">{error}</div>}
        </div>

        <div className="px-5 pb-5">
          <button onClick={handleSubmit} disabled={loading}
            className="w-full py-3 text-sm font-bold text-white rounded-xl disabled:opacity-40 transition-opacity"
            style={{ background: side === 'buy' ? 'linear-gradient(135deg, #059669, #10b981)' : 'linear-gradient(135deg, #dc2626, #ef4444)' }}>
            {loading ? 'Placing...' : `${side === 'buy' ? 'Buy' : 'Sell'} ${symbol}`}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Stat cell
// ─────────────────────────────────────────────────────────────────────────────

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="py-2.5">
      <div className="text-[11px] text-gray-400 mb-0.5">{label}</div>
      <div className="text-sm font-semibold text-gray-900 tabular-nums">{value}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// News item
// ─────────────────────────────────────────────────────────────────────────────

function NewsItem({ item }: { item: any }) {
  return (
    <a href={item.url} target="_blank" rel="noopener noreferrer"
      className="block px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0">
      <div className="text-sm font-medium text-gray-900 leading-snug mb-1 line-clamp-2">{item.title}</div>
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span>{item.site || item.publishedDate?.split(' ')[0]}</span>
        {item.publishedDate && (
          <span>{new Date(item.publishedDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
        )}
      </div>
    </a>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main stock page
// ─────────────────────────────────────────────────────────────────────────────

export default function StockPage({ symbol }: { symbol: string }) {
  const { goBack, canGoBack, openChatAbout } = useNavigation();
  const { user } = useAuth();
  const [quote, setQuote] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [news, setNews] = useState<any[]>([]);
  const [position, setPosition] = useState<AlpacaBrokerPosition | null>(null);
  const [loading, setLoading] = useState(true);
  const [tradeModal, setTradeModal] = useState<'buy' | 'sell' | null>(null);
  const [watchlisted, setWatchlisted] = useState(false);
  const [watchlistLoading, setWatchlistLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      marketApi.getQuote(symbol).catch(() => null),
      marketApi.getProfile(symbol).catch(() => null),
      marketApi.getNews(symbol, 5).catch(() => []),
      user ? alpacaBrokerApi.getPortfolio(user.id).catch(() => null) : null,
      user ? watchlistApi.getWatchlist(user.id).catch(() => ({ symbols: [] })) : null,
    ]).then(([q, p, n, portfolio, wl]) => {
      setQuote(q);
      setProfile(p);
      setNews(Array.isArray(n) ? n : []);
      if (portfolio?.positions) {
        const pos = portfolio.positions.find((p: any) => p.symbol === symbol);
        if (pos) setPosition(pos);
      }
      if (wl?.symbols) {
        setWatchlisted(wl.symbols.some((s: any) => s.symbol === symbol));
      }
    }).finally(() => setLoading(false));
  }, [symbol, user]);

  const price = quote?.price || 0;
  const change = quote?.change || 0;
  const changePct = quote?.changesPercentage || 0;
  const isUp = change >= 0;
  const name = profile?.companyName || quote?.name || symbol;

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Trade modal */}
      {tradeModal && user && (
        <QuickTradeModal
          symbol={symbol}
          side={tradeModal}
          price={price}
          userId={user.id}
          onClose={() => setTradeModal(null)}
          onSuccess={() => {
            setTradeModal(null);
            // Refresh position
            if (user) alpacaBrokerApi.getPortfolio(user.id).then(p => {
              const pos = p?.positions?.find((p: any) => p.symbol === symbol);
              setPosition(pos || null);
            }).catch(() => {});
          }}
        />
      )}

      {/* Header */}
      <div className="shrink-0 px-4 pt-4 pb-2">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {canGoBack && (
              <button onClick={goBack} className="p-1 -ml-1 text-gray-400 hover:text-gray-600 transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                </svg>
              </button>
            )}
            <div>
              <div className="font-bold text-gray-900 text-lg">{symbol}</div>
              <div className="text-xs text-gray-400">{name}</div>
            </div>
          </div>
          <button onClick={async () => {
              if (!user || watchlistLoading) return;
              setWatchlistLoading(true);
              try {
                if (watchlisted) {
                  await watchlistApi.removeSymbol(user.id, symbol);
                  setWatchlisted(false);
                } else {
                  await watchlistApi.addSymbol(user.id, symbol);
                  setWatchlisted(true);
                }
              } catch { /* ignore */ }
              finally { setWatchlistLoading(false); }
            }}
            disabled={watchlistLoading}
            className={`p-2 rounded-lg transition-colors ${watchlisted ? 'text-amber-500' : 'text-gray-300 hover:text-gray-500'}`}>
            <svg className="w-5 h-5" fill={watchlisted ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
            </svg>
          </button>
        </div>

        {/* Price */}
        <div className="mb-1">
          <span className="text-3xl font-bold text-gray-900 tabular-nums">{formatCurrency(price)}</span>
        </div>
        <div className={`text-sm font-medium tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
          {isUp ? '+' : ''}{formatCurrency(change)} ({formatPct(changePct)}) today
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        {/* Chart */}
        <div className="px-2">
          <PriceRangeChart
            series={[{ symbol, color: isUp ? '#10b981' : '#ef4444' }]}
            defaultDays={365}
            ranges={[
              { label: '1M', days: 30 },
              { label: '3M', days: 90 },
              { label: '6M', days: 180 },
              { label: '1Y', days: 365 },
              { label: '5Y', days: 1825 },
            ]}
            height={220}
          />
        </div>

        {/* Action buttons */}
        <div className="px-4 py-3 flex gap-2">
          <button onClick={() => setTradeModal('buy')}
            className="flex-1 py-3 text-sm font-bold text-white rounded-xl transition-opacity hover:opacity-90"
            style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
            Buy
          </button>
          <button onClick={() => setTradeModal('sell')}
            className="flex-1 py-3 text-sm font-bold text-white rounded-xl transition-opacity hover:opacity-90"
            style={{ background: 'linear-gradient(135deg, #dc2626, #ef4444)' }}>
            Sell
          </button>
          <button onClick={() => openChatAbout(symbol)}
            className="px-4 py-3 text-sm font-bold text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 0 1 .778-.332 48.294 48.294 0 0 0 5.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
            </svg>
            Ask AI
          </button>
        </div>

        {/* Your position */}
        {position && (
          <div className="mx-4 mb-4 rounded-xl border border-emerald-100 bg-emerald-50/40 p-4">
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Your Position</div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold text-gray-900 tabular-nums">
                  {formatCurrency(parseFloat(position.market_value || '0'))}
                </div>
                <div className="text-xs text-gray-400">
                  {parseFloat(position.qty || '0')} shares @ {formatCurrency(parseFloat(position.avg_entry_price || '0'))}
                </div>
              </div>
              <div className="text-right">
                <div className={`text-sm font-bold tabular-nums ${parseFloat(position.unrealized_pl || '0') >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {parseFloat(position.unrealized_pl || '0') >= 0 ? '+' : ''}{formatCurrency(parseFloat(position.unrealized_pl || '0'))}
                </div>
                <div className={`text-xs tabular-nums ${parseFloat(position.unrealized_plpc || '0') >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {formatPct(parseFloat(position.unrealized_plpc || '0') * 100)}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Key stats */}
        {quote && (
          <div className="px-4 mb-4">
            <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Key Statistics</div>
            <div className="grid grid-cols-2 gap-x-6 divide-y divide-gray-100">
              <Stat label="Market Cap" value={formatCurrency(quote.marketCap || 0)} />
              <Stat label="P/E Ratio" value={quote.pe ? quote.pe.toFixed(2) : '--'} />
              <Stat label="EPS" value={quote.eps ? `$${quote.eps.toFixed(2)}` : '--'} />
              <Stat label="Volume" value={formatNumber(quote.volume || 0)} />
              <Stat label="Avg Volume" value={formatNumber(quote.avgVolume || 0)} />
              <Stat label="52W High" value={formatCurrency(quote.yearHigh || 0)} />
              <Stat label="52W Low" value={formatCurrency(quote.yearLow || 0)} />
              <Stat label="Open" value={formatCurrency(quote.open || 0)} />
            </div>
          </div>
        )}

        {/* About */}
        {profile?.description && (
          <div className="px-4 mb-4">
            <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">About</div>
            <div className="text-sm text-gray-600 leading-relaxed line-clamp-4">{profile.description}</div>
            {profile.sector && (
              <div className="flex gap-2 mt-2">
                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{profile.sector}</span>
                {profile.industry && <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{profile.industry}</span>}
              </div>
            )}
          </div>
        )}

        {/* News */}
        {news.length > 0 && (
          <div className="mb-4">
            <div className="px-4 text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">News</div>
            {news.map((item, i) => <NewsItem key={i} item={item} />)}
          </div>
        )}

        {/* Spacer for mobile bottom nav */}
        <div className="h-20 md:h-4" />
      </div>
    </div>
  );
}
