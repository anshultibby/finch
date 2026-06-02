'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { robinhoodApi, type RobinhoodAccountsResponse } from '@/lib/api';

function fmtUsd(v?: string | null): string {
  if (v == null) return '—';
  const n = Number(v);
  return Number.isNaN(n) ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

const Feather = ({ className = 'w-4 h-4' }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z" />
    <line x1="16" y1="8" x2="2" y2="22" />
    <line x1="17.5" y1="15" x2="9" y2="15" />
  </svg>
);

/** A trading agent that places real orders — powered by Robinhood's agentic MCP. */
export default function RobinhoodAgentCard() {
  const { user } = useAuth();
  const [data, setData] = useState<RobinhoodAccountsResponse | null>(null);
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

  const handleConnect = async () => {
    if (!user?.id) return;
    setBusy(true); setError(null);
    try {
      const res = await robinhoodApi.connect(user.id);
      if (res.authorize_url) { window.location.href = res.authorize_url; return; }
      setError(res.message || 'Couldn’t start.');
    } catch { setError('Couldn’t start.'); }
    setBusy(false);
  };

  const handleDisconnect = async () => {
    if (!user?.id) return;
    setBusy(true);
    try { await robinhoodApi.disconnect(user.id); await load(); }
    finally { setBusy(false); }
  };

  const connected = !!data?.is_connected;
  const agentic = data?.agentic_account ?? null;
  const pf = data?.portfolio ?? null;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-green-600 text-white">
          <Feather />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-gray-900">Trading Agent</div>
          <div className="text-[11px] text-gray-400">Powered by Robinhood</div>
        </div>
        {connected && <span className="h-2 w-2 rounded-full bg-emerald-500" title="Connected" />}
      </div>

      {error && <div className="mt-2 text-xs text-red-500">{error}</div>}

      {loading ? (
        <div className="mt-3 h-12 animate-pulse rounded-lg bg-gray-100" />
      ) : connected ? (
        <div className="mt-3">
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-gray-700">
                Agentic{agentic && <span className="ml-1 text-gray-400">••{agentic.account_number.slice(-4)}</span>}
              </span>
              <span className="font-semibold text-gray-900">{fmtUsd(pf?.buying_power?.buying_power)}</span>
            </div>
          </div>
          <button onClick={handleDisconnect} disabled={busy}
            className="mt-2 text-[11px] text-gray-400 hover:text-red-500 disabled:opacity-50">
            Disconnect
          </button>
        </div>
      ) : (
        <div className="mt-3">
          <p className="text-xs leading-relaxed text-gray-500">
            An agent that places real trades for you — in an isolated account, never your main portfolio.
          </p>
          <button onClick={handleConnect} disabled={busy}
            className="mt-3 w-full rounded-lg bg-gradient-to-br from-emerald-500 to-green-600 py-2 text-xs font-semibold text-white shadow-sm transition hover:opacity-90 disabled:opacity-50">
            {busy ? 'Connecting…' : 'Enable trading'}
          </button>
        </div>
      )}
    </div>
  );
}
