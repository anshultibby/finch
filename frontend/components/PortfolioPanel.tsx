'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { alpacaBrokerApi } from '@/lib/api';
import AlpacaOnboarding from './AlpacaOnboarding';
import type { AlpacaPortfolioResponse, AlpacaBrokerPosition, AlpacaOrder } from '@/lib/types';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function SandboxBadge() {
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
      <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
      Sandbox
    </span>
  );
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function formatPct(n: number) {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${(n * 100).toFixed(2)}%`;
}

function num(v: string | null | undefined): number {
  return parseFloat(v || '0') || 0;
}

// ─────────────────────────────────────────────────────────────────────────────
// Trade modal
// ─────────────────────────────────────────────────────────────────────────────

function TradeModal({ userId, onClose, onSuccess, prefill }: {
  userId: string;
  onClose: () => void;
  onSuccess: () => void;
  prefill?: { symbol?: string; side?: string; qty?: number };
}) {
  const [symbol, setSymbol] = useState(prefill?.symbol || '');
  const [side, setSide] = useState<'buy' | 'sell'>(prefill?.side === 'sell' ? 'sell' : 'buy');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [qtyMode, setQtyMode] = useState<'shares' | 'dollars'>('shares');
  const [qty, setQty] = useState(prefill?.qty ? String(prefill.qty) : '');
  const [limitPrice, setLimitPrice] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async () => {
    if (!symbol.trim()) { setError('Symbol is required'); return; }
    if (!qty.trim() || parseFloat(qty) <= 0) { setError('Enter a valid quantity'); return; }
    setLoading(true);
    setError('');
    try {
      const order: Record<string, unknown> = {
        symbol: symbol.toUpperCase(),
        side,
        order_type: orderType,
        time_in_force: 'day',
      };
      if (qtyMode === 'shares') {
        order.qty = parseFloat(qty);
      } else {
        order.notional = parseFloat(qty);
      }
      if (orderType === 'limit' && limitPrice) {
        order.limit_price = parseFloat(limitPrice);
      }
      await alpacaBrokerApi.placeOrder(userId, order as any);
      setSuccess(true);
      setTimeout(() => { onSuccess(); onClose(); }, 1200);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Order failed');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.45)' }}>
        <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm text-center">
          <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-3">
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
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center px-4 pb-4 sm:pb-0" style={{ background: 'rgba(0,0,0,0.45)' }} onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-center justify-between mb-4">
            <div className="font-bold text-gray-900 text-base">Place order</div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 -mr-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Buy/Sell toggle */}
          <div className="flex gap-1 p-1 bg-gray-100 rounded-xl mb-4">
            {(['buy', 'sell'] as const).map(s => (
              <button key={s} onClick={() => setSide(s)}
                className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all ${
                  side === s
                    ? s === 'buy' ? 'bg-emerald-500 text-white shadow-sm' : 'bg-red-500 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-600'
                }`}>
                {s === 'buy' ? 'Buy' : 'Sell'}
              </button>
            ))}
          </div>

          {/* Symbol */}
          <div className="mb-3">
            <label className="block text-xs font-semibold text-gray-500 mb-1">Symbol</label>
            <input
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase())}
              placeholder="AAPL"
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 font-mono uppercase"
            />
          </div>

          {/* Qty mode toggle + input */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-gray-500">Amount</label>
              <div className="flex gap-1">
                {(['shares', 'dollars'] as const).map(m => (
                  <button key={m} onClick={() => setQtyMode(m)}
                    className={`px-2 py-0.5 text-[10px] font-bold rounded-md transition-colors ${
                      qtyMode === m ? 'bg-gray-900 text-white' : 'text-gray-400 hover:text-gray-600'
                    }`}>
                    {m === 'shares' ? 'Shares' : 'Dollars'}
                  </button>
                ))}
              </div>
            </div>
            <input
              type="number"
              value={qty}
              onChange={e => setQty(e.target.value)}
              placeholder={qtyMode === 'shares' ? '10' : '1000'}
              min="0"
              step={qtyMode === 'shares' ? '1' : '0.01'}
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 tabular-nums"
            />
          </div>

          {/* Order type */}
          <div className="mb-3">
            <div className="flex items-center gap-2 mb-1">
              <label className="text-xs font-semibold text-gray-500">Order type</label>
            </div>
            <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
              {(['market', 'limit'] as const).map(t => (
                <button key={t} onClick={() => setOrderType(t)}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                    orderType === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-400'
                  }`}>
                  {t === 'market' ? 'Market' : 'Limit'}
                </button>
              ))}
            </div>
          </div>

          {/* Limit price */}
          {orderType === 'limit' && (
            <div className="mb-3">
              <label className="block text-xs font-semibold text-gray-500 mb-1">Limit price</label>
              <input
                type="number"
                value={limitPrice}
                onChange={e => setLimitPrice(e.target.value)}
                placeholder="0.00"
                min="0"
                step="0.01"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 tabular-nums"
              />
            </div>
          )}

          {error && <div className="text-xs text-red-500 font-medium mb-3">{error}</div>}
        </div>

        <div className="px-5 pb-5 border-t border-gray-100 pt-4">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full py-2.5 text-sm font-bold text-white rounded-xl disabled:opacity-40 transition-opacity"
            style={{
              background: side === 'buy'
                ? 'linear-gradient(135deg, #059669 0%, #10b981 100%)'
                : 'linear-gradient(135deg, #dc2626 0%, #ef4444 100%)',
            }}>
            {loading ? 'Placing...' : `${side === 'buy' ? 'Buy' : 'Sell'} ${symbol || '...'}`}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Position row
// ─────────────────────────────────────────────────────────────────────────────

function PositionRow({ position, onSell, onClose: onClosePos, onTap }: {
  position: AlpacaBrokerPosition;
  onSell: (symbol: string, qty: number) => void;
  onClose: (symbol: string) => void;
  onTap: (symbol: string) => void;
}) {
  const pl = num(position.unrealized_pl);
  const plPct = num(position.unrealized_plpc);
  const isUp = pl >= 0;
  const [showActions, setShowActions] = useState(false);

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <div className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50 transition-colors">
        <button onClick={() => onTap(position.symbol)} className="text-left min-w-[80px] flex-shrink-0">
          <div className="text-sm font-semibold text-gray-900 hover:text-emerald-600 transition-colors">{position.symbol}</div>
          <div className="text-xs text-gray-400">
            {num(position.qty) % 1 === 0 ? num(position.qty) : num(position.qty).toFixed(2)} share{num(position.qty) !== 1 ? 's' : ''}
          </div>
        </button>

        <button onClick={() => setShowActions(!showActions)} className="flex-1 flex items-center justify-center">
          <div className="w-full max-w-[80px] flex items-center gap-0.5">
            <div className={`flex-1 border-t-2 border-dotted ${isUp ? 'border-emerald-300' : 'border-red-300'}`} />
            <div className={`w-2 h-2 rounded-full ${isUp ? 'bg-emerald-500' : 'bg-red-500'}`} />
          </div>
        </button>

        <div className="text-right min-w-[90px]">
          <div className="text-sm font-medium text-gray-900 tabular-nums">{formatCurrency(num(position.current_price))}</div>
          <div className={`text-xs font-medium tabular-nums ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
            {pl >= 0 ? '+' : ''}{formatCurrency(pl)}
          </div>
        </div>
      </div>

      {/* Expanded actions */}
      {showActions && (
        <div className="px-4 pb-3 flex gap-2">
          <button
            onClick={() => onSell(position.symbol, num(position.qty))}
            className="flex-1 py-2 text-xs font-bold text-red-600 bg-red-50 border border-red-100 rounded-lg hover:bg-red-100 transition-colors"
          >
            Sell shares
          </button>
          <button
            onClick={() => onClosePos(position.symbol)}
            className="flex-1 py-2 text-xs font-bold text-gray-600 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Close position
          </button>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Order row
// ─────────────────────────────────────────────────────────────────────────────

function OrderRow({ order, onCancel }: { order: AlpacaOrder; onCancel?: (id: string) => void }) {
  const isBuy = order.side === 'buy';
  const isFilled = order.status === 'filled';
  const isOpen = ['new', 'accepted', 'pending_new', 'partially_filled'].includes(order.status);
  const qty = order.filled_qty || order.qty || order.notional;
  const price = order.filled_avg_price;

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b border-gray-100 last:border-b-0">
      <div className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 ${isBuy ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'}`}>
        <span className={`text-[9px] font-bold ${isBuy ? 'text-emerald-600' : 'text-red-600'}`}>
          {isBuy ? 'B' : 'S'}
        </span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-gray-900">{order.symbol}</div>
        <div className="text-[11px] text-gray-400">
          {qty} {order.notional && !order.qty ? 'USD' : 'sh'} · {order.type}
          {price ? ` @ ${formatCurrency(num(price))}` : ''}
        </div>
      </div>
      <div className="text-right flex-shrink-0">
        <div className={`text-[10px] font-bold uppercase ${
          isFilled ? 'text-emerald-600' : isOpen ? 'text-amber-600' : 'text-gray-400'
        }`}>
          {order.status.replace(/_/g, ' ')}
        </div>
        {order.created_at && (
          <div className="text-[10px] text-gray-300">
            {new Date(order.created_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </div>
        )}
      </div>
      {isOpen && onCancel && (
        <button onClick={() => onCancel(order.id)} className="text-gray-300 hover:text-red-500 flex-shrink-0 p-1" title="Cancel">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Stat card
// ─────────────────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50/60 px-3.5 py-3">
      <div className="text-[9px] font-bold text-gray-400 uppercase tracking-widest mb-1">{label}</div>
      <div className="text-lg font-bold text-gray-900 tabular-nums">{value}</div>
      {sub && <div className="text-[11px] text-gray-400 mt-0.5">{sub}</div>}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main panel
// ─────────────────────────────────────────────────────────────────────────────

type Tab = 'positions' | 'orders';

export default function PortfolioPanel() {
  const { user } = useAuth();
  const { openStock } = useNavigation();
  const [alpacaStatus, setAlpacaStatus] = useState<{ exists: boolean; status?: string; alpaca_account_id?: string } | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [loading, setLoading] = useState(true);

  // Portfolio data
  const [portfolio, setPortfolio] = useState<AlpacaPortfolioResponse | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);

  // Orders
  const [orders, setOrders] = useState<AlpacaOrder[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('positions');

  // Trade modal
  const [tradeModal, setTradeModal] = useState<{ symbol?: string; side?: string; qty?: number } | null>(null);

  // Check account status
  useEffect(() => {
    if (!user) return;
    alpacaBrokerApi.getAccountStatus(user.id)
      .then(setAlpacaStatus)
      .catch(() => setAlpacaStatus({ exists: false }))
      .finally(() => setLoading(false));
  }, [user]);

  const fetchPortfolio = useCallback(() => {
    if (!user) return;
    setPortfolioLoading(true);
    setPortfolioError(null);
    Promise.all([
      alpacaBrokerApi.getPortfolio(user.id),
      alpacaBrokerApi.getOrders(user.id, 'all', 30),
    ])
      .then(([p, o]) => { setPortfolio(p); setOrders(o); })
      .catch((err) => setPortfolioError(err?.response?.data?.detail || 'Failed to load portfolio'))
      .finally(() => setPortfolioLoading(false));
  }, [user]);

  useEffect(() => {
    if (alpacaStatus?.status === 'ACTIVE') fetchPortfolio();
  }, [alpacaStatus?.status, fetchPortfolio]);

  const handleCancelOrder = async (orderId: string) => {
    if (!user) return;
    try {
      await alpacaBrokerApi.cancelOrder(user.id, orderId);
      fetchPortfolio();
    } catch { /* ignore */ }
  };

  const handleClosePosition = async (symbol: string) => {
    if (!user) return;
    try {
      await alpacaBrokerApi.closePosition(user.id, symbol);
      fetchPortfolio();
    } catch { /* ignore */ }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  // ── No account — CTA ──────────────────────────────────────────────────────

  if (!alpacaStatus?.exists) {
    return (
      <div className="flex flex-col h-full bg-white">
        {showOnboarding && user && (
          <AlpacaOnboarding
            userId={user.id}
            onClose={() => setShowOnboarding(false)}
            onSuccess={() => {
              setShowOnboarding(false);
              alpacaBrokerApi.getAccountStatus(user.id).then(setAlpacaStatus).catch(() => {});
            }}
          />
        )}
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <div className="relative mb-6">
            <div className="w-20 h-20 rounded-2xl flex items-center justify-center"
              style={{ background: 'linear-gradient(145deg, #ecfdf5, #d1fae5)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <svg className="w-10 h-10 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
              </svg>
            </div>
            <div className="absolute -top-1 -right-1"><SandboxBadge /></div>
          </div>
          <div className="font-bold text-gray-900 text-lg mb-2">Open an account for your agent</div>
          <div className="text-sm text-gray-500 mb-2 max-w-xs leading-relaxed">
            Your agent needs a brokerage account to execute tax-loss harvesting trades on your behalf.
          </div>
          <div className="text-xs text-gray-400 mb-6 max-w-xs">
            Sandbox account — no real money involved.
          </div>
          <button
            onClick={() => setShowOnboarding(true)}
            className="px-8 py-3 text-sm font-bold text-white rounded-xl transition-all hover:opacity-90 hover:shadow-lg"
            style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)', boxShadow: '0 4px 14px rgba(16,185,129,0.3)' }}>
            Get started
          </button>
        </div>
      </div>
    );
  }

  // ── Pending account ───────────────────────────────────────────────────────

  if (alpacaStatus.status !== 'ACTIVE') {
    const statusLabels: Record<string, { label: string; color: string }> = {
      SUBMITTED: { label: 'Application submitted', color: 'text-amber-600' },
      APPROVAL_PENDING: { label: 'Under review', color: 'text-amber-600' },
      APPROVED: { label: 'Approved — activating', color: 'text-emerald-600' },
      ACTION_REQUIRED: { label: 'Action required', color: 'text-red-500' },
      REJECTED: { label: 'Application declined', color: 'text-red-500' },
    };
    const info = statusLabels[alpacaStatus.status || ''] || { label: alpacaStatus.status || 'Processing', color: 'text-gray-600' };

    return (
      <div className="flex flex-col h-full bg-white items-center justify-center px-6 text-center">
        <div className="mb-2"><SandboxBadge /></div>
        <div className="w-14 h-14 rounded-full bg-amber-50 border border-amber-100 flex items-center justify-center mb-4">
          <svg className="w-7 h-7 text-amber-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </div>
        <div className="font-bold text-gray-900 text-lg mb-1">Agent account</div>
        <div className={`text-sm font-medium mb-3 ${info.color}`}>{info.label}</div>
        <div className="text-xs text-gray-400 max-w-xs">This usually takes a few seconds in sandbox.</div>
      </div>
    );
  }

  // ── Active account — portfolio + trading ──────────────────────────────────

  if (portfolioLoading && !portfolio) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center gap-2">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
        <div className="text-xs text-gray-400">Loading portfolio...</div>
      </div>
    );
  }

  if (portfolioError && !portfolio) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center px-6 text-center">
        <div className="text-sm text-gray-500 mb-3">{portfolioError}</div>
        <button onClick={fetchPortfolio} className="text-sm text-emerald-600 font-medium hover:underline">Retry</button>
      </div>
    );
  }

  const acct = portfolio?.account;
  const positions = portfolio?.positions || [];
  const equity = num(acct?.equity);
  const cash = num(acct?.cash);
  const buyingPower = num(acct?.buying_power);
  const lastEquity = num(acct?.last_equity);
  const dayChange = equity - lastEquity;
  const dayChangePct = lastEquity > 0 ? dayChange / lastEquity : 0;

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Trade modal */}
      {tradeModal && user && (
        <TradeModal
          userId={user.id}
          onClose={() => setTradeModal(null)}
          onSuccess={fetchPortfolio}
          prefill={tradeModal}
        />
      )}

      {/* Header */}
      <div className="shrink-0 px-4 pt-4 pb-2">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900">Agent Portfolio</span>
            <SandboxBadge />
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={fetchPortfolio}
              disabled={portfolioLoading}
              className="p-1.5 text-gray-300 hover:text-gray-500 transition-colors disabled:opacity-30"
              title="Refresh"
            >
              <svg className={`w-3.5 h-3.5 ${portfolioLoading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
              </svg>
            </button>
          </div>
        </div>

        {/* Equity hero */}
        <div className="mb-1">
          <div className="text-2xl font-bold text-gray-900 tabular-nums">{formatCurrency(equity)}</div>
          {lastEquity > 0 && dayChange !== 0 && (
            <div className={`text-sm font-medium tabular-nums ${dayChange >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {dayChange >= 0 ? '+' : ''}{formatCurrency(dayChange)} ({formatPct(dayChangePct)}) today
            </div>
          )}
        </div>
      </div>

      {/* Stats + Trade button */}
      <div className="shrink-0 px-4 pb-3">
        <div className="grid grid-cols-3 gap-2 mb-3">
          <StatCard label="Cash" value={formatCurrency(cash)} />
          <StatCard label="Buying Power" value={formatCurrency(buyingPower)} />
          <StatCard label="Positions" value={String(positions.length)} />
        </div>
        <button
          onClick={() => setTradeModal({})}
          className="w-full py-2.5 text-sm font-bold text-white rounded-xl transition-all hover:opacity-90"
          style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)', boxShadow: '0 2px 8px rgba(16,185,129,0.25)' }}>
          Trade
        </button>
      </div>

      {/* Tabs */}
      <div className="shrink-0 flex border-b border-gray-200">
        {(['positions', 'orders'] as Tab[]).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-wider transition-colors ${
              activeTab === tab
                ? 'text-gray-900 border-b-2 border-gray-900'
                : 'text-gray-400 hover:text-gray-600'
            }`}>
            {tab === 'positions' ? `Positions (${positions.length})` : `Orders (${orders.length})`}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'positions' ? (
          positions.length > 0 ? (
            positions.map(p => (
              <PositionRow
                key={p.symbol}
                position={p}
                onSell={(symbol, qty) => setTradeModal({ symbol, side: 'sell', qty })}
                onClose={handleClosePosition}
                onTap={openStock}
              />
            ))
          ) : (
            <div className="px-4 py-8 text-center">
              <div className="text-sm text-gray-400 mb-1">No open positions</div>
              <div className="text-xs text-gray-300 mb-4">Buy some stocks to get started</div>
              <button
                onClick={() => setTradeModal({ side: 'buy' })}
                className="text-xs font-semibold text-emerald-600 hover:text-emerald-700">
                Place your first trade
              </button>
            </div>
          )
        ) : (
          orders.length > 0 ? (
            orders.map(o => (
              <OrderRow key={o.id} order={o} onCancel={handleCancelOrder} />
            ))
          ) : (
            <div className="px-4 py-8 text-center">
              <div className="text-sm text-gray-400">No orders yet</div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
