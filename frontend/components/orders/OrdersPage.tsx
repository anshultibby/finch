'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { alpacaBrokerApi } from '@/lib/api';
import SandboxBadge from '@/components/shared/SandboxBadge';
import type { AlpacaOrder } from '@/lib/types';

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function num(v: string | null | undefined): number {
  return parseFloat(v || '0') || 0;
}

type Tab = 'open' | 'filled' | 'all';

function OrderCard({ order, onCancel, onSymbolClick }: {
  order: AlpacaOrder;
  onCancel?: (id: string) => void;
  onSymbolClick: (symbol: string) => void;
}) {
  const isBuy = order.side === 'buy';
  const isFilled = order.status === 'filled';
  const isCancelled = order.status === 'canceled' || order.status === 'cancelled';
  const isOpen = ['new', 'accepted', 'pending_new', 'partially_filled'].includes(order.status);

  const statusColor = isFilled ? 'text-emerald-600 bg-emerald-50 border-emerald-200'
    : isOpen ? 'text-amber-600 bg-amber-50 border-amber-200'
    : isCancelled ? 'text-gray-400 bg-gray-50 border-gray-200'
    : 'text-red-500 bg-red-50 border-red-200';

  return (
    <div className="px-4 sm:px-6 py-3.5 border-b border-gray-100 last:border-b-0">
      <div className="flex items-start gap-3">
        {/* Side badge */}
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 ${
          isBuy ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'
        }`}>
          <span className={`text-[10px] font-black ${isBuy ? 'text-emerald-600' : 'text-red-600'}`}>
            {isBuy ? 'BUY' : 'SELL'}
          </span>
        </div>

        {/* Details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <button onClick={() => onSymbolClick(order.symbol)} className="text-sm font-bold text-gray-900 hover:text-emerald-600 transition-colors">
              {order.symbol}
            </button>
            <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-md border ${statusColor}`}>
              {order.status.replace(/_/g, ' ')}
            </span>
          </div>
          <div className="text-xs text-gray-400">
            {order.qty ? `${order.qty} shares` : order.notional ? `$${num(order.notional).toLocaleString()}` : ''} · {order.type}
            {order.limit_price ? ` @ ${formatCurrency(num(order.limit_price))}` : ''}
          </div>
          {isFilled && order.filled_avg_price && (
            <div className="text-xs text-emerald-600 mt-0.5">
              Filled {order.filled_qty} @ {formatCurrency(num(order.filled_avg_price))}
            </div>
          )}
        </div>

        {/* Right side */}
        <div className="text-right flex-shrink-0">
          <div className="text-[11px] text-gray-400">
            {order.created_at ? new Date(order.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}
          </div>
          <div className="text-[11px] text-gray-300">
            {order.created_at ? new Date(order.created_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : ''}
          </div>
          {isOpen && onCancel && (
            <button onClick={() => onCancel(order.id)}
              className="mt-1 text-[10px] font-semibold text-red-500 hover:text-red-700 transition-colors">
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function OrdersPage() {
  const { user } = useAuth();
  const { openStock } = useNavigation();
  const [orders, setOrders] = useState<AlpacaOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>('all');
  const [hasAccount, setHasAccount] = useState(false);

  const fetchOrders = useCallback(async () => {
    if (!user) return;
    try {
      const status = await alpacaBrokerApi.getAccountStatus(user.id);
      if (!status.exists || status.status !== 'ACTIVE') {
        setHasAccount(false);
        return;
      }
      setHasAccount(true);
      const data = await alpacaBrokerApi.getOrders(user.id, 'all', 100);
      setOrders(Array.isArray(data) ? data : []);
    } catch {
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  const handleCancel = async (orderId: string) => {
    if (!user) return;
    try {
      await alpacaBrokerApi.cancelOrder(user.id, orderId);
      fetchOrders();
    } catch { /* ignore */ }
  };

  const filtered = orders.filter(o => {
    if (tab === 'open') return ['new', 'accepted', 'pending_new', 'partially_filled'].includes(o.status);
    if (tab === 'filled') return o.status === 'filled';
    return true;
  });

  const openCount = orders.filter(o => ['new', 'accepted', 'pending_new', 'partially_filled'].includes(o.status)).length;

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!hasAccount) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center px-6 text-center">
        <div className="text-sm text-gray-500 mb-2">No agent account</div>
        <div className="text-xs text-gray-400">Open an account to start trading and see your order history.</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="shrink-0 px-4 sm:px-6 pt-5 pb-2">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-lg font-bold text-gray-900">Orders</span>
          <SandboxBadge />
          <button onClick={fetchOrders} className="ml-auto p-1.5 text-gray-300 hover:text-gray-500 transition-colors" title="Refresh">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
          {([
            { id: 'all' as Tab, label: `All (${orders.length})` },
            { id: 'open' as Tab, label: `Open (${openCount})` },
            { id: 'filled' as Tab, label: 'Filled' },
          ]).map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                tab === t.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-400'
              }`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Order list */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length > 0 ? (
          filtered.map(o => (
            <OrderCard key={o.id} order={o} onCancel={handleCancel} onSymbolClick={openStock} />
          ))
        ) : (
          <div className="px-6 py-12 text-center">
            <div className="text-sm text-gray-400 mb-1">
              {tab === 'open' ? 'No open orders' : tab === 'filled' ? 'No filled orders' : 'No orders yet'}
            </div>
            <div className="text-xs text-gray-300">
              {orders.length === 0 ? 'Place a trade to see your orders here' : 'Try a different filter'}
            </div>
          </div>
        )}
        <div className="h-20 md:h-4" />
      </div>
    </div>
  );
}
