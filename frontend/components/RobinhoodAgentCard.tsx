'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { robinhoodApi, snaptradeApi, type RobinhoodAccountsResponse } from '@/lib/api';

function fmtUsd(v?: string | null): string {
  if (v == null) return '—';
  const n = Number(v);
  return Number.isNaN(n) ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

function fmtSigned(n: number): string {
  const s = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Math.abs(n));
  return `${n >= 0 ? '+' : '−'}${s}`;
}

function timeAgo(iso?: string): string {
  if (!iso) return '';
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

// Our own ownable agent mark — the app's "AI" sparkle, not a borrowed brand glyph.
const Sparkle = ({ className = 'w-4 h-4' }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
  </svg>
);

// "Powered by" lockup using Robinhood's *real* logo, sourced from the same broker
// logo feed the app already uses. Falls back to the plain name if unavailable.
function PoweredBy({ logo }: { logo: string | null }) {
  const [failed, setFailed] = useState(false);
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-gray-400">
      Powered by
      {logo && !failed
        ? <img src={logo} alt="Robinhood" className="h-3 w-3 rounded-sm object-contain" onError={() => setFailed(true)} />
        : null}
      <span className="font-medium text-gray-500">Robinhood</span>
    </span>
  );
}

/** A trading agent that places real orders — powered by Robinhood's agentic MCP. */
export default function RobinhoodAgentCard() {
  const { user } = useAuth();
  const [data, setData] = useState<RobinhoodAccountsResponse | null>(null);
  const [logo, setLogo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user?.id) return;
    setLoading(true);
    try { setData(await robinhoodApi.getAccounts(user.id)); setError(null); }
    catch { setError('Couldn’t load.'); }
    finally { setLoading(false); }
  }, [user?.id]);

  useEffect(() => { load(); }, [load]);

  // Official Robinhood logo from the existing broker-logo feed (one-time).
  useEffect(() => {
    snaptradeApi.getBrokerages()
      .then(res => {
        const rh = (res.brokerages || []).find(b => b.name?.toLowerCase().includes('robinhood'));
        if (rh?.logo) setLogo(rh.logo);
      })
      .catch(() => {});
  }, []);

  // Surface the OAuth redirect result, then clean the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get('robinhood');
    if (!status) return;
    if (status === 'error') setError('Connection failed.');
    params.delete('robinhood');
    const qs = params.toString();
    window.history.replaceState({}, '', window.location.pathname + (qs ? `?${qs}` : ''));
    if (status === 'connected') load();
  }, [load]);

  const handleDisconnect = async () => {
    if (!user?.id) return;
    setBusy(true);
    try { await robinhoodApi.disconnect(user.id); await load(); }
    finally { setBusy(false); }
  };

  const connected = !!data?.is_connected;
  const agentic = data?.agentic_account ?? null;
  const pf = data?.portfolio ?? null;
  const stats = data?.stats ?? null;
  const today = stats?.today ?? null;
  const lastTrade = stats?.last_trade ?? null;

  return (
    <div className="rounded-xl border border-gray-200 p-3.5">
      {/* Header: own sparkle mark + powered-by Robinhood */}
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-green-600 text-white">
          <Sparkle />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-gray-900">AI Trading Agent</div>
          {connected
            ? <div className="flex items-center gap-1.5 text-[11px] text-emerald-600"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />Active</div>
            : <PoweredBy logo={logo} />}
        </div>
      </div>

      {error && <div className="mt-2 text-xs text-red-500">{error}</div>}

      {loading ? (
        <div className="mt-3 h-12 animate-pulse rounded-lg bg-gray-100" />
      ) : connected ? (
        <div className="mt-3">
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="flex items-end justify-between">
              <div>
                <div className="text-[11px] text-gray-400">Account value</div>
                <div className="text-lg font-bold tabular-nums text-gray-900">{fmtUsd(pf?.total_value)}</div>
              </div>
              {today ? (
                <div className="text-right">
                  <div className="text-[11px] text-gray-400">Today</div>
                  <div className={`text-sm font-semibold tabular-nums ${today.amount >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {fmtSigned(today.amount)} <span className="font-normal">({today.pct >= 0 ? '+' : ''}{today.pct}%)</span>
                  </div>
                </div>
              ) : (
                <div className="text-right">
                  <div className="text-[11px] text-gray-400">Buying power</div>
                  <div className="text-sm font-semibold tabular-nums text-gray-700">{fmtUsd(pf?.buying_power?.buying_power)}</div>
                </div>
              )}
            </div>
          </div>

          {/* Activity */}
          {lastTrade && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              <span className={lastTrade.side === 'sell' ? 'text-red-500' : 'text-emerald-600'}>
                {lastTrade.side === 'sell' ? '▼' : '▲'}
              </span>
              <span className="text-gray-600">
                {lastTrade.side === 'sell' ? 'Sold' : 'Bought'} {Number(lastTrade.quantity).toLocaleString()} {lastTrade.symbol}
              </span>
              <span className="ml-auto text-gray-400">{timeAgo(lastTrade.at)}</span>
            </div>
          )}

          <div className="mt-2 flex items-center justify-between text-[11px] text-gray-400">
            <span>
              {stats?.trades_today ? `${stats.trades_today} trade${stats.trades_today === 1 ? '' : 's'} today · ` : ''}
              Agentic{agentic && <span className="ml-0.5">••{agentic.account_number.slice(-4)}</span>}
            </span>
            <button onClick={handleDisconnect} disabled={busy} className="hover:text-red-500 disabled:opacity-50">Disconnect</button>
          </div>
        </div>
      ) : (
        <div className="mt-3">
          <ul className="space-y-1.5 text-xs text-gray-600">
            {['Trades from chat — just ask', 'Its own account — never your main one', 'You set the limits'].map((t) => (
              <li key={t} className="flex items-start gap-2">
                <span className="mt-1.5 h-px w-2 shrink-0 bg-emerald-500" />
                <span>{t}</span>
              </li>
            ))}
          </ul>
          {/* Robinhood only allows connecting from a native (on-device) app, so
              web users are pointed to the Finch mobile app rather than a flow
              that can't complete in the browser. */}
          <div className="mt-3 rounded-lg bg-gray-50 px-3 py-2.5 text-center">
            <div className="text-xs font-medium text-gray-700">Connect in the Finch app</div>
            <div className="mt-0.5 text-[11px] text-gray-400">Robinhood requires connecting on your device</div>
          </div>
        </div>
      )}
    </div>
  );
}
