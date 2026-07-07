'use client';

/**
 * The approval moment. A proposed trade rendered as a deliberate decision,
 * not a dialog: the order's exact terms, a live expiry countdown, and a
 * hold-to-approve control — approving is a physical act the user performs,
 * not a tap they might not remember making.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { pendingTradesApi, type PendingTradeItem } from '@/lib/api';
import { invalidatePendingTrades } from '@/hooks/usePendingTrades';

const HOLD_MS = 1100;

function useCountdown(expiresAt: string | null): { label: string; urgent: boolean; expired: boolean } {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  if (!expiresAt) return { label: '', urgent: false, expired: false };
  const ms = new Date(expiresAt).getTime() - now;
  if (ms <= 0) return { label: 'expired', urgent: false, expired: true };
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  const label = mins >= 60
    ? `${Math.floor(mins / 60)}h ${mins % 60}m`
    : mins >= 1 ? `${mins}m ${secs}s` : `${secs}s`;
  return { label, urgent: mins < 5, expired: false };
}

function orderRows(p: Record<string, unknown>): [string, string][] {
  const rows: [string, string][] = [];
  const side = String(p.side || '').toUpperCase();
  if (side) rows.push(['Side', side]);
  if (p.quantity) rows.push(['Quantity', `${p.quantity} shares`]);
  if (p.dollar_amount) rows.push(['Amount', `$${Number(p.dollar_amount).toLocaleString()}`]);
  rows.push(['Order type', String(p.type || 'market')]);
  if (p.limit_price) rows.push(['Limit price', `$${Number(p.limit_price).toFixed(2)}`]);
  return rows;
}

export default function ApprovalCard({
  trade,
  onDecided,
}: {
  trade: PendingTradeItem;
  onDecided: (id: string, status: 'approved' | 'rejected' | 'failed' | 'expired') => void;
}) {
  const [progress, setProgress] = useState(0); // 0..1 while holding
  const [busy, setBusy] = useState<'approving' | 'rejecting' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const rafRef = useRef<number>(0);
  const holdStartRef = useRef<number>(0);
  const { label: countdown, urgent, expired } = useCountdown(trade.expires_at);

  const symbol = String(trade.order_params?.symbol || '').toUpperCase();
  const side = String(trade.order_params?.side || '').toLowerCase();

  const cancelHold = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    holdStartRef.current = 0;
    setProgress(0);
  }, []);

  const approve = useCallback(async () => {
    setBusy('approving');
    setError(null);
    try {
      await pendingTradesApi.approve(trade.id);
      invalidatePendingTrades();
      onDecided(trade.id, 'approved');
    } catch (e: unknown) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } };
      if (err.response?.status === 410) { invalidatePendingTrades(); onDecided(trade.id, 'expired'); return; }
      // The backend marks the trade failed on a placement error — terminal.
      setFailed(err.response?.data?.detail || 'Order could not be placed.');
      setBusy(null);
    }
  }, [trade.id, onDecided]);

  const startHold = useCallback(() => {
    if (busy || expired) return;
    holdStartRef.current = performance.now();
    const tick = (t: number) => {
      if (!holdStartRef.current) return;
      const p = Math.min(1, (t - holdStartRef.current) / HOLD_MS);
      setProgress(p);
      if (p >= 1) {
        holdStartRef.current = 0;
        setProgress(0);
        void approve();
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [busy, expired, approve]);

  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);

  const reject = useCallback(async () => {
    setBusy('rejecting');
    setError(null);
    try {
      await pendingTradesApi.reject(trade.id);
      invalidatePendingTrades();
      onDecided(trade.id, 'rejected');
    } catch {
      setError('Could not reject — try again.');
      setBusy(null);
    }
  }, [trade.id, onDecided]);

  if (failed) {
    return (
      <div className="rounded-2xl border border-red-100 bg-red-50/60 p-4">
        <p className="text-sm font-semibold text-red-700 mb-1">Order couldn&apos;t be placed — no trade happened.</p>
        <p className="text-xs text-red-600/80 mb-1">{failed}</p>
        <p className="text-xs text-gray-500">{trade.summary} · Ask Finch to re-propose once fixed.</p>
      </div>
    );
  }

  if (expired) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
        Proposal expired — no trade was placed. <span className="font-medium text-gray-700">{trade.summary}</span>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-emerald-200 bg-white shadow-sm overflow-hidden">
      {/* Eyebrow strip */}
      <div className="flex items-center justify-between px-4 py-2 bg-emerald-50/70 border-b border-emerald-100">
        <span className="text-[11px] font-bold tracking-[0.14em] text-emerald-700 uppercase">
          Trade proposal · needs your approval
        </span>
        <span className={`text-[11px] font-semibold tabular-nums ${urgent ? 'text-red-600' : 'text-emerald-700/70'}`}>
          expires in {countdown}
        </span>
      </div>

      <div className="p-4">
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-lg font-bold text-gray-900">{symbol || 'Order'}</span>
          {side && (
            <span className={`text-[11px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded ${
              side === 'buy' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
            }`}>
              {side}
            </span>
          )}
        </div>
        {trade.summary && <p className="text-sm text-gray-700 mb-3">{trade.summary}</p>}

        <div className="grid grid-cols-2 gap-x-6 gap-y-1 mb-4">
          {orderRows(trade.order_params || {}).map(([k, v]) => (
            <div key={k} className="flex justify-between text-xs border-b border-dashed border-gray-100 py-1">
              <span className="text-gray-400">{k}</span>
              <span className="font-semibold text-gray-800 tabular-nums">{v}</span>
            </div>
          ))}
        </div>

        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}

        <div className="flex items-center gap-2">
          <button
            onPointerDown={startHold}
            onPointerUp={cancelHold}
            onPointerLeave={cancelHold}
            onContextMenu={(e) => e.preventDefault()}
            disabled={!!busy}
            className="relative flex-1 h-11 rounded-xl bg-emerald-600 text-white text-sm font-bold overflow-hidden select-none touch-none disabled:opacity-60"
          >
            {/* fill sweep while holding */}
            <span
              className="absolute inset-y-0 left-0 bg-emerald-800/80"
              style={{ width: `${progress * 100}%`, transition: progress === 0 ? 'width 150ms ease-out' : 'none' }}
            />
            <span className="relative">
              {busy === 'approving' ? 'Placing order…'
                : progress > 0 ? 'Keep holding…' : 'Hold to approve'}
            </span>
          </button>
          <button
            onClick={reject}
            disabled={!!busy}
            className="h-11 px-4 rounded-xl border border-gray-200 text-sm font-semibold text-gray-600 hover:bg-gray-50 disabled:opacity-60"
          >
            {busy === 'rejecting' ? 'Rejecting…' : 'Reject'}
          </button>
        </div>
        <p className="mt-2 text-[11px] text-gray-400">
          Nothing is placed until you approve. If it expires, no trade happens.
        </p>
      </div>
    </div>
  );
}
