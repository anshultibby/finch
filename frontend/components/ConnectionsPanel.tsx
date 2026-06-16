'use client';

import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { snaptradeApi, casparserApi } from '@/lib/api';
import type { CASParserStatusResponse, CASParserPortfolioResponse } from '@/lib/api';
import { PORTFOLIO_REVIEW_PROMPT } from '@/lib/aiPrompts';
import PriceRangeChart, { type SeriesPoint } from '@/components/ui/PriceRangeChart';
import type { Brokerage, AccountDetail, Position, PortfolioResponse, PortfolioPerformance } from '@/lib/types';

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function fmtPct(n: number) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

function timeAgo(dateStr: string | null): string | null {
  if (!dateStr) return null;
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Broker theming
// ─────────────────────────────────────────────────────────────────────────────

const BROKER_STYLE: Record<string, { gradient: string; accent: string; light: string }> = {
  robinhood:    { gradient: 'from-emerald-500 to-green-600',   accent: 'text-emerald-600', light: 'bg-emerald-50' },
  alpaca:       { gradient: 'from-teal-500 to-cyan-600',      accent: 'text-teal-600',    light: 'bg-teal-50'    },
  schwab:       { gradient: 'from-blue-500 to-blue-700',      accent: 'text-blue-600',    light: 'bg-blue-50'    },
  fidelity:     { gradient: 'from-green-600 to-emerald-700',  accent: 'text-green-600',   light: 'bg-green-50'   },
  etrade:       { gradient: 'from-violet-500 to-purple-700',  accent: 'text-violet-600',  light: 'bg-violet-50'  },
  interactive:  { gradient: 'from-slate-500 to-slate-700',    accent: 'text-slate-600',   light: 'bg-slate-50'   },
  webull:       { gradient: 'from-orange-500 to-amber-600',   accent: 'text-orange-600',  light: 'bg-orange-50'  },
  questrade:    { gradient: 'from-rose-500 to-pink-600',      accent: 'text-rose-600',    light: 'bg-rose-50'    },
  tradier:      { gradient: 'from-indigo-500 to-indigo-700',  accent: 'text-indigo-600',  light: 'bg-indigo-50'  },
  wealthsimple: { gradient: 'from-zinc-500 to-zinc-700',     accent: 'text-zinc-600',    light: 'bg-zinc-100'   },
};
const DEFAULT_STYLE = { gradient: 'from-gray-500 to-gray-700', accent: 'text-gray-600', light: 'bg-gray-50' };

function getBrokerStyle(institution: string) {
  const key = institution?.toLowerCase() ?? '';
  const match = Object.entries(BROKER_STYLE).find(([k]) => key.includes(k));
  return match?.[1] ?? DEFAULT_STYLE;
}

const BROKER_EMOJI: Record<string, string> = {
  robinhood: '🪶', alpaca: '🦙', schwab: '🏛', fidelity: '🔴', etrade: '📈',
  interactive: '🌐', webull: '🐂', questrade: '🍁', moomoo: '🐄', tradier: '⚡', wealthsimple: '✦',
};

function brokerEmoji(name: string): string {
  const key = name?.toLowerCase() ?? '';
  return Object.entries(BROKER_EMOJI).find(([k]) => key.includes(k))?.[1] ?? '🏦';
}

// ─────────────────────────────────────────────────────────────────────────────
// Connect modal
// ─────────────────────────────────────────────────────────────────────────────

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

// ---------------------------------------------------------------------------
// CDSL OTP Connect Modal
// ---------------------------------------------------------------------------

type CdslStep = 'form' | 'otp' | 'success';

function CdslConnectModal({ onClose, onConnected }: {
  onClose: () => void;
  onConnected: () => void;
}) {
  const [step, setStep] = useState<CdslStep>('form');
  const [pan, setPan] = useState('');
  const [boId, setBoId] = useState('');
  const [dob, setDob] = useState('');
  const [otp, setOtp] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ investor_name: string; total_holdings: number } | null>(null);

  const handleInitiate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await casparserApi.initiateConnect(pan.toUpperCase(), boId.replace(/\D/g, ''), dob);
      setSessionId(res.session_id);
      setStep('otp');
    } catch (err: any) {
      setError(err.message || 'Failed to send OTP. Check your details and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await casparserApi.verifyConnect(sessionId, otp, pan.toUpperCase(), boId.replace(/\D/g, ''), dob);
      setResult({ investor_name: res.investor_name, total_holdings: res.total_holdings });
      setStep('success');
    } catch (err: any) {
      setError(err.message || 'Invalid OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-sm shadow-2xl" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-gray-100">
          <div>
            <h2 className="text-base font-bold text-gray-900">Connect Indian Portfolio</h2>
            <p className="text-xs text-gray-500 mt-0.5">Via CDSL eCAS — no broker login required</p>
          </div>
          <button onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-5 py-4">
          {/* Step indicator */}
          <div className="flex items-center gap-2 mb-5">
            {(['form', 'otp', 'success'] as CdslStep[]).map((s, i) => (
              <React.Fragment key={s}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-colors ${
                  s === step ? 'bg-gray-900 text-white' :
                  (i < (['form','otp','success'] as CdslStep[]).indexOf(step)) ? 'bg-emerald-500 text-white' :
                  'bg-gray-100 text-gray-400'
                }`}>{i + 1}</div>
                {i < 2 && <div className="flex-1 h-px bg-gray-200" />}
              </React.Fragment>
            ))}
          </div>

          {step === 'form' && (
            <form onSubmit={handleInitiate} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-1 block">PAN Number</label>
                <input
                  value={pan}
                  onChange={e => setPan(e.target.value.toUpperCase())}
                  placeholder="ABCDE1234F"
                  maxLength={10}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-gray-400"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-1 block">CDSL BO ID <span className="font-normal text-gray-400">(16-digit demat account number)</span></label>
                <input
                  value={boId}
                  onChange={e => setBoId(e.target.value)}
                  placeholder="1234567890123456"
                  maxLength={20}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-gray-400"
                  required
                />
                <p className="text-[10px] text-gray-400 mt-1">Found in HDFC Securities app → Profile → Demat Account details</p>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-1 block">Date of Birth</label>
                <input
                  type="date"
                  value={dob}
                  onChange={e => setDob(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-gray-400"
                  required
                />
              </div>
              {error && <p className="text-xs text-red-500 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
              <button type="submit" disabled={loading}
                className="w-full py-2.5 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors">
                {loading ? 'Sending OTP…' : 'Send OTP →'}
              </button>
              <p className="text-[10px] text-gray-400 text-center">An OTP will be sent to your CDSL-registered mobile number</p>
            </form>
          )}

          {step === 'otp' && (
            <form onSubmit={handleVerify} className="space-y-4">
              <p className="text-sm text-gray-600">Enter the 6-digit OTP sent to your CDSL-registered mobile number.</p>
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-1 block">OTP</label>
                <input
                  value={otp}
                  onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  maxLength={6}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm font-mono text-center tracking-widest text-lg focus:outline-none focus:border-gray-400"
                  autoFocus
                  required
                />
              </div>
              {error && <p className="text-xs text-red-500 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
              <button type="submit" disabled={loading || otp.length < 6}
                className="w-full py-2.5 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors">
                {loading ? 'Verifying…' : 'Verify & Import Holdings'}
              </button>
              <button type="button" onClick={() => { setStep('form'); setError(''); setOtp(''); }}
                className="w-full py-2 text-xs text-gray-400 hover:text-gray-600">
                ← Back
              </button>
            </form>
          )}

          {step === 'success' && result && (
            <div className="text-center py-2 space-y-3">
              <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
                <svg className="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </div>
              <div>
                <p className="font-bold text-gray-900">{result.investor_name || 'Connected!'}</p>
                <p className="text-sm text-gray-500 mt-1">{result.total_holdings} holdings imported from CDSL</p>
              </div>
              <button onClick={() => { onConnected(); onClose(); }}
                className="w-full py-2.5 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors">
                View Holdings
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ConnectModal({ brokerages, connecting, selectedBroker, iframeUrl, onConnect, onClose }: {
  brokerages: Brokerage[];
  connecting: boolean;
  selectedBroker: string | null;
  iframeUrl: string | null;
  onConnect: (id: string) => void;
  onClose: () => void;
}) {
  const [search, setSearch] = useState('');
  const filtered = brokerages.filter(b => b.name.toLowerCase().startsWith(search.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className={`bg-white rounded-2xl shadow-2xl w-full overflow-hidden transition-all ${
        iframeUrl ? 'max-w-2xl max-h-[90vh]' : 'max-w-xl max-h-[80vh]'
      }`} onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 flex items-center justify-between border-b border-gray-100">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {iframeUrl ? 'Sign in to your broker' : 'Connect a brokerage'}
            </h3>
            <p className="text-sm text-gray-500 mt-0.5">
              {iframeUrl ? 'Complete the sign-in below to link your account' : 'Select your broker to securely link your account'}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg p-1.5 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {iframeUrl ? (
          <div className="w-full" style={{ height: 'calc(90vh - 76px)' }}>
            <iframe
              src={iframeUrl}
              className="w-full h-full border-0"
              allow="camera;microphone"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-top-navigation"
            />
          </div>
        ) : (
          <>
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
              {filtered.length === 0 ? (
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
                        {isThis && (
                          <div className="flex items-center gap-1.5">
                            <div className="w-3.5 h-3.5 border-2 border-emerald-200 border-t-emerald-500 rounded-full animate-spin" />
                            <span className="text-xs text-emerald-600 font-medium">Connecting...</span>
                          </div>
                        )}
                        {!isThis && (
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
          </>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Top movers card
// ─────────────────────────────────────────────────────────────────────────────

function MoverCard({ position, onClick }: { position: Position; onClick: () => void }) {
  const gl = position.gain_loss ?? 0;
  const glPct = position.gain_loss_percent ?? 0;
  const isUp = gl >= 0;

  return (
    <button
      onClick={onClick}
      className="flex-shrink-0 w-[120px] rounded-xl border border-gray-100 bg-white p-3 hover:border-gray-200 hover:shadow-sm transition-all text-left"
    >
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-xs font-bold text-gray-900">{position.symbol}</span>
      </div>
      <div className="text-[11px] text-gray-400 mb-1 tabular-nums">{fmt(position.price)}</div>
      <div className={`inline-flex items-center gap-0.5 text-[11px] font-semibold px-1.5 py-0.5 rounded-md tabular-nums ${
        isUp ? 'text-emerald-700 bg-emerald-50' : 'text-red-600 bg-red-50'
      }`}>
        <svg className={`w-2.5 h-2.5 ${isUp ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 19.5l7.5-7.5 7.5 7.5" />
        </svg>
        {fmtPct(glPct)}
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Account row (dashboard-style)
// ─────────────────────────────────────────────────────────────────────────────

function AccountRow({ account, onDisconnect, onClick }: {
  account: AccountDetail;
  onDisconnect: (id: string, name: string) => void;
  onClick: () => void;
}) {
  const totalGainLoss = useMemo(() => {
    return (account.positions || []).reduce((sum, p) => sum + (p.gain_loss ?? 0), 0);
  }, [account.positions]);

  const totalCost = useMemo(() => {
    return (account.positions || []).reduce((sum, p) => sum + (p.total_cost ?? 0), 0);
  }, [account.positions]);

  const gainLossPct = totalCost > 0 ? (totalGainLoss / totalCost) * 100 : 0;
  const isUp = totalGainLoss >= 0;
  const value = account.total_value || account.balance || 0;

  const typeLabel = (type: string) =>
    (type || 'Account').toUpperCase().replace(/_/g, ' ');

  return (
    <div className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50/50 transition-colors group">
      <button onClick={onClick} className="flex-1 flex items-center gap-3 text-left min-w-0">
        <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-sm flex-shrink-0">
          {brokerEmoji(account.institution)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-gray-900 truncate">{account.name}</div>
          <div className="text-[10px] text-gray-400">{typeLabel(account.type)}</div>
        </div>
      </button>
      <div className="flex items-center gap-3 flex-shrink-0">
        {totalGainLoss !== 0 && (
          <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded-md tabular-nums ${
            isUp ? 'text-emerald-700 bg-emerald-50' : 'text-red-600 bg-red-50'
          }`}>
            {fmtPct(gainLossPct)}
          </span>
        )}
        <div className="text-right">
          <div className="text-sm font-semibold text-gray-900 tabular-nums">{fmt(value)}</div>
        </div>
      </div>
      <button onClick={() => onDisconnect(account.id, account.name)}
        className="p-1 text-gray-200 hover:text-red-400 rounded-lg hover:bg-red-50 transition-colors flex-shrink-0 opacity-0 group-hover:opacity-100"
        title="Disconnect">
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Institution group (dashboard-style)
// ─────────────────────────────────────────────────────────────────────────────

interface InstitutionGroupProps {
  institution: string;
  accounts: AccountDetail[];
  onDisconnect: (id: string, name: string) => void;
  onClickAccount: (account: AccountDetail) => void;
}

function InstitutionGroup({ institution, accounts, onDisconnect, onClickAccount }: InstitutionGroupProps) {
  const style = getBrokerStyle(institution);
  const emoji = brokerEmoji(institution);
  const totalValue = accounts.reduce((s, a) => s + (a.total_value || a.balance || 0), 0);

  return (
    <div className="rounded-xl border border-gray-100 overflow-hidden bg-white">
      <div className={`bg-gradient-to-r ${style.gradient} px-4 py-2.5 flex items-center gap-2.5`}>
        <div className="w-7 h-7 rounded-lg bg-white/20 backdrop-blur-sm flex items-center justify-center text-sm flex-shrink-0">
          {emoji}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-semibold text-white truncate">{institution}</div>
          <div className="text-[10px] text-white/70">
            {accounts.length} account{accounts.length !== 1 ? 's' : ''}
          </div>
        </div>
        <div className="text-sm font-bold text-white tabular-nums">{fmt(totalValue)}</div>
      </div>

      <div className="divide-y divide-gray-50">
        {accounts.map(account => (
          <AccountRow
            key={account.id}
            account={account}
            onDisconnect={onDisconnect}
            onClick={() => onClickAccount(account)}
          />
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Empty state
// ─────────────────────────────────────────────────────────────────────────────

function EmptyState({ onConnect }: { onConnect: () => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
      <div className="relative mb-6">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-50 to-emerald-100 border border-emerald-200 flex items-center justify-center">
          <svg className="w-9 h-9 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
          </svg>
        </div>
        <div className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-white border-2 border-emerald-200 flex items-center justify-center">
          <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
        </div>
      </div>

      <h2 className="text-lg font-bold text-gray-900 mb-2">Connect your brokerage</h2>
      <p className="text-sm text-gray-500 max-w-xs leading-relaxed mb-6">
        Link your accounts to see all your holdings in one place and let AI review your portfolio.
      </p>

      <button onClick={onConnect}
        className="w-full max-w-xs flex items-center justify-center gap-2 px-5 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-semibold text-sm transition-colors shadow-sm">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Connect Account
      </button>

      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {['Fidelity', 'Schwab', 'Robinhood', 'E*TRADE', 'Webull'].map(name => (
          <span key={name} className="text-[10px] text-gray-300 bg-gray-50 px-2 py-0.5 rounded-full">{name}</span>
        ))}
        <span className="text-[10px] text-gray-300 bg-gray-50 px-2 py-0.5 rounded-full">+ more</span>
      </div>

      <div className="mt-6 flex items-center gap-2 text-[11px] text-gray-400">
        <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
        </svg>
        Read-only access. We never place trades on your behalf.
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Account detail view
// ─────────────────────────────────────────────────────────────────────────────

interface AllocationEntry {
  label: string;
  value: number;
  pct: number;
  color: string;
}

const ACCOUNT_CHART_RANGES = [
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '1Y', days: 365 },
  { label: 'All', days: 3650 },
];

function AccountDetailView({ account, userId, onBack, onClickSymbol }: {
  account: AccountDetail;
  userId: string;
  onBack: () => void;
  onClickSymbol: (s: string) => void;
}) {
  const [acctChartData, setAcctChartData] = useState<SeriesPoint[]>([]);
  const [acctChartDays, setAcctChartDays] = useState(30);
  const [acctChartLoading, setAcctChartLoading] = useState(true);
  const acctChartCache = useRef<Record<number, SeriesPoint[]>>({});
  const [acctHover, setAcctHover] = useState<{ date: string; value: number } | null>(null);

  const loadAcctChart = useCallback(async (days: number) => {
    const cached = acctChartCache.current[days];
    if (cached) {
      setAcctChartData(cached);
      setAcctChartLoading(false);
      return;
    }
    setAcctChartLoading(true);
    try {
      const start = new Date();
      start.setDate(start.getDate() - days);
      const res = await snaptradeApi.getPortfolioHistory(userId, start.toISOString().split('T')[0], undefined, account.id);
      if (res?.success && res.equity_series?.length) {
        const points = res.equity_series.map(p => ({ date: p.date, value: p.value }));
        acctChartCache.current[days] = points;
        setAcctChartData(points);
      }
    } catch {} finally { setAcctChartLoading(false); }
  }, [userId, account.id]);

  useEffect(() => {
    loadAcctChart(acctChartDays);
  }, [loadAcctChart, acctChartDays]);

  const positions = useMemo(() =>
    [...(account.positions || [])].sort((a, b) => (b.value ?? 0) - (a.value ?? 0)),
    [account.positions]
  );

  const totalValue = account.total_value || account.balance || 0;

  const totalGainLoss = useMemo(() =>
    positions.reduce((sum, p) => sum + (p.gain_loss ?? 0), 0),
    [positions]
  );

  const totalCost = useMemo(() =>
    positions.reduce((sum, p) => sum + (p.total_cost ?? 0), 0),
    [positions]
  );

  const gainLossPct = totalCost > 0 ? (totalGainLoss / totalCost) * 100 : 0;
  const isUp = totalGainLoss >= 0;

  const acctDisplayValue = acctHover?.value ?? totalValue;
  const acctChartStart = acctChartData.length > 0 ? acctChartData[0].value : totalValue;
  const acctChartChange = acctDisplayValue - acctChartStart;
  const acctChartChangePct = acctChartStart > 0 ? (acctChartChange / acctChartStart) * 100 : 0;
  const acctChartIsUp = acctChartChange >= 0;

  const allocations = useMemo((): AllocationEntry[] => {
    const ASSET_COLORS: Record<string, string> = {
      'Equity': '#10b981',
      'ETF': '#3b82f6',
      'Cash': '#94a3b8',
      'Crypto': '#f59e0b',
      'Other': '#8b5cf6',
    };

    const etfPatterns = /^(SPY|QQQ|IVV|VOO|VTI|VEA|VWO|IEMG|AGG|BND|GLD|SLV|ARKK|SCHD|VIG|VYM|VXUS|EFA|IWM|DIA|XLF|XLK|XLE|XLV|XLI|XLP|XLU|XLB|XLRE|XLC|VNQ|TLT|LQD|HYG|IEFA|IJR|IJH|SPTM|SPYG|SPYV|JEPI|JEPQ|SCHX|SCHA)/i;

    const groups: Record<string, number> = {};
    for (const p of positions) {
      const cat = etfPatterns.test(p.symbol) ? 'ETF' : 'Equity';
      groups[cat] = (groups[cat] ?? 0) + (p.value ?? 0);
    }

    const cashValue = totalValue - positions.reduce((s, p) => s + (p.value ?? 0), 0);
    if (cashValue > 0.01) {
      groups['Cash'] = cashValue;
    }

    return Object.entries(groups)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([label, value]) => ({
        label,
        value,
        pct: totalValue > 0 ? (value / totalValue) * 100 : 0,
        color: ASSET_COLORS[label] || ASSET_COLORS['Other'],
      }));
  }, [positions, totalValue]);

  const emoji = brokerEmoji(account.institution);
  const style = getBrokerStyle(account.institution);

  const typeLabel = (type: string) =>
    (type || 'Account').toUpperCase().replace(/_/g, ' ');

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 bg-white border-b border-gray-100">
        <div className="flex items-center justify-between">
          <button onClick={onBack} className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            <span className="text-sm font-medium">Portfolio</span>
          </button>
          <span className="text-[10px] text-gray-400">{typeLabel(account.type)}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="px-4 pt-4 space-y-4">

          {/* Account summary + chart */}
          <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
            <div className="p-4">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${style.gradient} flex items-center justify-center text-base`}>
                  <span className="drop-shadow-sm">{emoji}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-gray-900 truncate">{account.name}</div>
                  <div className="text-[10px] text-gray-400">
                    {account.number ? `****${account.number.slice(-4)}` : account.institution}
                  </div>
                </div>
              </div>
              <div className="text-2xl font-bold text-gray-900 tabular-nums">{fmt(acctDisplayValue)}</div>
              {acctChartData.length >= 2 ? (
                <div className={`flex items-center gap-1 mt-0.5 text-[12px] font-semibold tabular-nums ${
                  acctChartIsUp ? 'text-emerald-600' : 'text-red-500'
                }`}>
                  <svg className={`w-3 h-3 ${acctChartIsUp ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 19.5l7.5-7.5 7.5 7.5" />
                  </svg>
                  {fmt(Math.abs(acctChartChange))} ({fmtPct(acctChartChangePct)})
                </div>
              ) : totalGainLoss !== 0 ? (
                <div className={`flex items-center gap-1 mt-0.5 text-[12px] font-semibold tabular-nums ${
                  isUp ? 'text-emerald-600' : 'text-red-500'
                }`}>
                  <svg className={`w-3 h-3 ${isUp ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 19.5l7.5-7.5 7.5 7.5" />
                  </svg>
                  {fmt(Math.abs(totalGainLoss))} ({fmtPct(gainLossPct)})
                </div>
              ) : null}
            </div>

            {acctChartLoading ? (
              <div className="h-[120px] flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
              </div>
            ) : acctChartData.length >= 2 ? (
              <div className="px-2">
                <PriceRangeChart
                  data={acctChartData}
                  format="currency"
                  height={120}
                  hideHeader
                  hideRangeTabs
                  onHoverChange={(info) => setAcctHover(info ? { date: info.date, value: info.value } : null)}
                />
              </div>
            ) : null}

            <div className="flex items-center justify-center gap-0.5 px-3 py-2 border-t border-gray-50">
              {ACCOUNT_CHART_RANGES.map(r => (
                <button
                  key={r.label}
                  onClick={() => { setAcctChartDays(r.days); loadAcctChart(r.days); }}
                  className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all ${
                    acctChartDays === r.days
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          {/* Allocations */}
          {allocations.length > 0 && (
            <div className="rounded-xl border border-gray-100 bg-white p-4">
              <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Allocations</h3>
              <div className="space-y-2.5">
                {allocations.map(a => (
                  <div key={a.label} className="flex items-center gap-3">
                    <span className="text-xs text-gray-600 w-12 flex-shrink-0">{a.label}</span>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${Math.max(a.pct, 1)}%`, backgroundColor: a.color }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-gray-700 tabular-nums w-10 text-right">
                      {a.pct < 1 ? '< 1%' : `${Math.round(a.pct)}%`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Holdings */}
          {positions.length > 0 && (
            <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
              <div className="px-4 py-3 flex items-center justify-between">
                <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                  Holdings ({positions.length})
                </h3>
              </div>
              <div className="divide-y divide-gray-50">
                {positions.map(p => {
                  const gl = p.gain_loss ?? 0;
                  const glPct = p.gain_loss_percent ?? 0;
                  const pIsUp = gl >= 0;

                  return (
                    <button
                      key={p.symbol}
                      onClick={() => onClickSymbol(p.symbol)}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors text-left"
                    >
                      <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                        <span className="text-[10px] font-bold text-gray-500">{p.symbol.slice(0, 4)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900">{p.symbol}</div>
                        <div className="text-[10px] text-gray-400 tabular-nums">
                          {p.quantity % 1 === 0 ? p.quantity : p.quantity.toFixed(2)} shares
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {gl !== 0 && (
                          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-md tabular-nums ${
                            pIsUp ? 'text-emerald-700 bg-emerald-50' : 'text-red-600 bg-red-50'
                          }`}>
                            {fmtPct(glPct)}
                          </span>
                        )}
                        <span className="text-sm font-semibold text-gray-900 tabular-nums">{fmt(p.value)}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {positions.length === 0 && (
            <div className="rounded-xl border border-gray-100 bg-white p-6 text-center">
              <p className="text-sm text-gray-400">No holdings in this account</p>
            </div>
          )}
        </div>

        <div className="h-20 md:h-6" />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Chart range config
// ─────────────────────────────────────────────────────────────────────────────

const CHART_RANGES = [
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: 'YTD', days: Math.ceil((Date.now() - new Date(new Date().getFullYear(), 0, 1).getTime()) / 86400000) },
  { label: '1Y', days: 365 },
  { label: 'All', days: 3650 },
];

// ─────────────────────────────────────────────────────────────────────────────
// Main panel
// ─────────────────────────────────────────────────────────────────────────────

export default function ConnectionsPanel() {
  const { user } = useAuth();
  const { openChatWithPrompt, openStock } = useNavigation();
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [brokerages, setBrokerages] = useState<Brokerage[]>([]);
  const [chartData, setChartData] = useState<SeriesPoint[]>([]);
  const [chartDays, setChartDays] = useState(30);
  const [chartLoading, setChartLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [selectedAccount, setSelectedAccount] = useState<AccountDetail | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [selectedBroker, setSelectedBroker] = useState<string | null>(null);
  const [iframeUrl, setIframeUrl] = useState<string | null>(null);
  const [showCdslModal, setShowCdslModal] = useState(false);
  const [cdslPortfolio, setCdslPortfolio] = useState<CASParserPortfolioResponse | null>(null);
  const initRef = useRef(false);
  const chartCacheRef = useRef<Record<number, SeriesPoint[]>>({});

  const loadData = useCallback(async () => {
    if (!user?.id) return;
    try {
      const [portfolioRes, brokerRes, perfRes, cdslRes] = await Promise.all([
        snaptradeApi.getPortfolio(user.id).catch(() => null),
        snaptradeApi.getBrokerages().catch(() => null),
        snaptradeApi.getPortfolioPerformance(user.id).catch(() => null),
        casparserApi.getPortfolio(user.id).catch(() => null),
      ]);
      if (portfolioRes?.success) setPortfolio(portfolioRes);
      if (brokerRes?.success) setBrokerages(brokerRes.brokerages);
      if (perfRes?.success) setPerformance(perfRes);
      if (cdslRes?.is_connected) setCdslPortfolio(cdslRes);
    } catch {} finally { setLoading(false); }
  }, [user?.id]);

  const loadChart = useCallback(async (days: number, opts?: { force?: boolean; liveTotal?: number }) => {
    if (!user?.id) return;

    const cached = chartCacheRef.current[days];
    if (cached && !opts?.force) {
      setChartData(cached);
      setChartLoading(false);
      return;
    }

    setChartLoading(true);
    try {
      let series: Array<{ date: string; value: number }> | undefined;

      const start = new Date();
      start.setDate(start.getDate() - days);
      const res = await snaptradeApi.getPortfolioHistory(user.id, start.toISOString().split('T')[0]);
      if (res?.success && res.equity_series?.length) {
        series = res.equity_series;
      }

      if (series && opts?.liveTotal && opts.liveTotal > 0) {
        const lastChart = series[series.length - 1].value;
        const drift = Math.abs(lastChart - opts.liveTotal) / opts.liveTotal;
        if (drift > 0.10) {
          series = undefined;
        }
      }

      if (!series) {
        const buildRes = await snaptradeApi.buildPortfolioHistory(user.id, undefined, true);
        if (buildRes?.success && buildRes.equity_series?.length) {
          series = buildRes.equity_series;
        }
      }

      if (series?.length) {
        const points = series.map(p => ({ date: p.date, value: p.value }));
        chartCacheRef.current[days] = points;
        setChartData(points);
      }
    } catch {} finally { setChartLoading(false); }
  }, [user?.id]);

  useEffect(() => {
    if (!user || initRef.current) return;
    initRef.current = true;
    loadData();
    loadChart(chartDays);
  }, [user, loadData, loadChart]);

  const handleRangeChange = useCallback((days: number) => {
    setChartDays(days);
    loadChart(days);
  }, [loadChart]);

  useEffect(() => {
    if (!iframeUrl) return;
    const handleMessage = (event: MessageEvent) => {
      const isOurCallback = event.origin === window.location.origin
        && event.data?.type === 'SNAPTRADE_CONNECTION';
      const isSnapTradeSuccess = event.data?.status === 'SUCCESS';

      if (isOurCallback || isSnapTradeSuccess) {
        window.removeEventListener('message', handleMessage);
        setConnecting(false);
        setSelectedBroker(null);
        setIframeUrl(null);
        setShowModal(false);
        initRef.current = false;
        chartCacheRef.current = {};
        loadData();
        loadChart(chartDays, { force: true });
        if (user?.id) {
          snaptradeApi.buildPortfolioHistory(user.id, undefined, true).catch(() => {});
        }
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [iframeUrl, chartDays, loadData, loadChart, user?.id]);

  const handleConnect = async (brokerId: string) => {
    if (!user?.id) return;
    setConnecting(true);
    setSelectedBroker(brokerId);
    try {
      const redirectUri = `${window.location.origin}/snaptrade/callback`;
      const response = await snaptradeApi.connectBroker(user.id, redirectUri, brokerId);
      if (response.success && response.redirect_uri) {
        setIframeUrl(response.redirect_uri);
      } else {
        setConnecting(false);
        setSelectedBroker(null);
      }
    } catch {
      setConnecting(false);
      setSelectedBroker(null);
    }
  };

  const handleDisconnect = async (accountId: string, accountName: string) => {
    if (!user?.id) return;
    if (!confirm(`Disconnect ${accountName}? This will remove it from your portfolio.`)) return;
    try {
      await snaptradeApi.disconnectAccount(user.id, accountId);
      initRef.current = false;
      loadData();
    } catch {}
  };

  // ── Derived data ────────────────────────────────────────────────────────────

  const accounts = portfolio?.accounts || [];
  const hasAccounts = accounts.length > 0;
  const totalValue = portfolio?.total_value || 0;

  const topMovers = useMemo(() => {
    const allPositions: Position[] = [];
    for (const acct of accounts) {
      for (const p of acct.positions || []) {
        if (p.gain_loss_percent !== undefined && p.gain_loss_percent !== 0) {
          const existing = allPositions.find(x => x.symbol === p.symbol);
          if (!existing) allPositions.push(p);
        }
      }
    }
    return allPositions
      .sort((a, b) => Math.abs(b.gain_loss_percent ?? 0) - Math.abs(a.gain_loss_percent ?? 0))
      .slice(0, 12);
  }, [accounts]);

  const grouped = useMemo(() => {
    const g = accounts.reduce<Record<string, AccountDetail[]>>((acc, account) => {
      const key = account.institution || 'Unknown';
      (acc[key] ||= []).push(account);
      return acc;
    }, {});
    return Object.entries(g).sort((a, b) => {
      const aVal = a[1].reduce((s, ac) => s + (ac.total_value || ac.balance || 0), 0);
      const bVal = b[1].reduce((s, ac) => s + (ac.total_value || ac.balance || 0), 0);
      return bVal - aVal;
    });
  }, [accounts]);

  // Re-check chart staleness once portfolio data arrives
  const chartStaleChecked = useRef(false);
  useEffect(() => {
    if (!chartStaleChecked.current && totalValue > 0 && chartData.length >= 2) {
      const lastChart = chartData[chartData.length - 1].value;
      const drift = Math.abs(lastChart - totalValue) / totalValue;
      if (drift > 0.10) {
        chartStaleChecked.current = true;
        chartCacheRef.current = {};
        loadChart(chartDays, { force: true, liveTotal: totalValue });
      }
    }
  }, [totalValue, chartData, chartDays, loadChart]);

  const gainLoss = performance?.total_gain_loss ?? 0;
  const gainLossPct = performance?.total_gain_loss_percent ?? 0;
  const isPositive = gainLoss >= 0;

  // ── Chart hover state ───────────────────────────────────────────────────────

  const [hoverInfo, setHoverInfo] = useState<{ date: string; value: number } | null>(null);
  const displayValue = hoverInfo?.value ?? totalValue;
  const chartStart = chartData.length > 0 ? chartData[0].value : totalValue;
  const chartChange = displayValue - chartStart;
  const chartChangePct = chartStart > 0 ? (chartChange / chartStart) * 100 : 0;
  const chartIsUp = chartChange >= 0;

  // ── Loading ─────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-gray-50 items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!hasAccounts) {
    return (
      <div className="flex flex-col h-full bg-gray-50">
        <div className="shrink-0 px-5 py-4 bg-white border-b border-gray-100">
          <h1 className="text-lg font-bold text-gray-900">Portfolio</h1>
        </div>
        <div className="flex-1 overflow-y-auto">
          <EmptyState onConnect={() => setShowModal(true)} />
          <div className="px-5 pb-8">
            <div className="relative flex items-center my-2">
              <div className="flex-1 h-px bg-gray-200" />
              <span className="px-3 text-[11px] text-gray-400 font-medium">or</span>
              <div className="flex-1 h-px bg-gray-200" />
            </div>
            <button onClick={() => setShowCdslModal(true)}
              className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl border border-gray-200 bg-white hover:border-gray-300 text-left transition-colors">
              <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center shrink-0">
                <span className="text-lg">🇮🇳</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-800">Connect Indian Portfolio</p>
                <p className="text-xs text-gray-400">HDFC Securities, Zerodha & more via CDSL</p>
              </div>
              <svg className="w-4 h-4 text-gray-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
        {showModal && (
          <ConnectModal brokerages={brokerages} connecting={connecting} selectedBroker={selectedBroker} iframeUrl={iframeUrl} onConnect={handleConnect} onClose={() => { setShowModal(false); setIframeUrl(null); setConnecting(false); setSelectedBroker(null); }} />
        )}
        {showCdslModal && (
          <CdslConnectModal onClose={() => setShowCdslModal(false)} onConnected={() => { initRef.current = false; loadData(); }} />
        )}
      </div>
    );
  }

  if (selectedAccount) {
    return (
      <AccountDetailView
        account={selectedAccount}
        userId={user!.id}
        onBack={() => setSelectedAccount(null)}
        onClickSymbol={openStock}
      />
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="shrink-0 px-5 py-3 bg-white border-b border-gray-100">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-900">Portfolio</h1>
          <button onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-xs font-semibold transition-colors">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Add
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="px-4 pt-4 space-y-4">

          {/* ── Portfolio value + chart ─────────────────────────────────── */}
          <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
            <div className="px-4 pt-4">
              <div className="text-[11px] text-gray-400 font-medium mb-0.5">
                {hoverInfo ? 'Portfolio value' : 'Total portfolio'}
              </div>
              <div className="text-2xl font-bold text-gray-900 tabular-nums">
                {fmt(displayValue)}
              </div>
              {chartData.length >= 2 && (
                <div className={`flex items-center gap-1 mt-0.5 text-[12px] font-semibold tabular-nums ${
                  chartIsUp ? 'text-emerald-600' : 'text-red-500'
                }`}>
                  <svg className={`w-3 h-3 ${chartIsUp ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 19.5l7.5-7.5 7.5 7.5" />
                  </svg>
                  {fmt(Math.abs(chartChange))} ({fmtPct(chartChangePct)})
                </div>
              )}
              {chartData.length < 2 && gainLoss !== 0 && (
                <div className={`flex items-center gap-1 mt-0.5 text-[12px] font-semibold tabular-nums ${
                  isPositive ? 'text-emerald-600' : 'text-red-500'
                }`}>
                  <svg className={`w-3 h-3 ${isPositive ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 19.5l7.5-7.5 7.5 7.5" />
                  </svg>
                  {fmt(Math.abs(gainLoss))} ({fmtPct(gainLossPct)})
                </div>
              )}
            </div>

            {chartLoading ? (
              <div className="h-[140px] flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
              </div>
            ) : chartData.length >= 2 ? (
              <div className="px-2">
                <PriceRangeChart
                  data={chartData}
                  format="currency"
                  height={140}
                  hideHeader
                  hideRangeTabs
                  onHoverChange={(info) => setHoverInfo(info ? { date: info.date, value: info.value } : null)}
                />
              </div>
            ) : (
              <div className="h-[80px] flex items-center justify-center text-[11px] text-gray-400">
                Chart data will appear after the first sync
              </div>
            )}

            {/* Range tabs */}
            <div className="flex items-center justify-center gap-0.5 px-3 py-2 border-t border-gray-50">
              {CHART_RANGES.map(r => (
                <button
                  key={r.label}
                  onClick={() => handleRangeChange(r.days)}
                  className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all ${
                    chartDays === r.days
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          {/* ── AI Review ──────────────────────────────────────────────── */}
          <button
            onClick={() => openChatWithPrompt(PORTFOLIO_REVIEW_PROMPT, 'Review my portfolio')}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-gray-200 hover:border-gray-300 rounded-xl text-xs font-semibold text-gray-700 hover:text-gray-900 transition-colors shadow-sm"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 0 0-3.09 3.09Z" />
            </svg>
            AI Portfolio Review
          </button>

          {/* ── Top movers ─────────────────────────────────────────────── */}
          {topMovers.length > 0 && (
            <div>
              <div className="flex items-center justify-between px-1 mb-2">
                <h2 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Top Movers</h2>
              </div>
              <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-none">
                {topMovers.map(p => (
                  <MoverCard key={p.symbol} position={p} onClick={() => openStock(p.symbol)} />
                ))}
              </div>
            </div>
          )}

          {/* ── Accounts ───────────────────────────────────────────────── */}
          <div>
            <div className="flex items-center justify-between px-1 mb-2">
              <h2 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Accounts</h2>
              <span className="text-[10px] text-gray-400">{accounts.length} linked</span>
            </div>
            <div className="space-y-2">
              {grouped.map(([institution, accts]) => (
                <InstitutionGroup
                  key={institution}
                  institution={institution}
                  accounts={accts}
                  onDisconnect={handleDisconnect}
                  onClickAccount={(acct) => setSelectedAccount(acct)}
                />
              ))}
            </div>
          </div>

          {/* ── Indian Holdings (CDSL) ─────────────────────────────────── */}
          {cdslPortfolio?.is_connected ? (
            <div>
              <div className="flex items-center justify-between px-1 mb-2">
                <h2 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Indian Portfolio</h2>
                <div className="flex items-center gap-2">
                  {cdslPortfolio.holdings_fetched_at && (
                    <span className="text-[10px] text-gray-400">{timeAgo(cdslPortfolio.holdings_fetched_at)}</span>
                  )}
                  <button onClick={() => setShowCdslModal(true)}
                    className="text-[10px] text-gray-400 hover:text-gray-600 underline underline-offset-2">Refresh</button>
                </div>
              </div>
              <div className="space-y-2">
                {cdslPortfolio.accounts.map((acct, ai) => (
                  <div key={ai} className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                    <div className="px-4 py-2.5 border-b border-gray-50 flex items-center justify-between">
                      <span className="text-xs font-semibold text-gray-700">{acct.dp_name || 'Demat Account'}</span>
                      <span className="text-[10px] text-gray-400">{acct.holdings.length} holdings</span>
                    </div>
                    <div className="divide-y divide-gray-50">
                      {acct.holdings.slice(0, 8).map((h, hi) => (
                        <div key={hi} className="px-4 py-2 flex items-center justify-between">
                          <div className="min-w-0">
                            <p className="text-xs font-semibold text-gray-800 truncate max-w-[180px]">{h.name || h.isin}</p>
                            <p className="text-[10px] text-gray-400 font-mono">{h.isin}</p>
                          </div>
                          <span className="text-xs font-semibold text-gray-600 tabular-nums ml-2 shrink-0">{h.quantity} shares</span>
                        </div>
                      ))}
                      {acct.holdings.length > 8 && (
                        <div className="px-4 py-2 text-center text-[11px] text-gray-400">
                          +{acct.holdings.length - 8} more holdings
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-gray-400 text-center mt-2">
                Holdings snapshot from CDSL · Prices not shown · Refresh requires new OTP
              </p>
            </div>
          ) : (
            <button onClick={() => setShowCdslModal(true)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-200 bg-white hover:border-gray-300 text-left transition-colors">
              <div className="w-8 h-8 rounded-lg bg-orange-50 flex items-center justify-center shrink-0">
                <span className="text-base">🇮🇳</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-gray-800">Connect Indian Portfolio</p>
                <p className="text-[10px] text-gray-400">HDFC Securities, Zerodha & more via CDSL</p>
              </div>
              <svg className="w-4 h-4 text-gray-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}

          {/* Add another US brokerage */}
          <button onClick={() => setShowModal(true)}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border-2 border-dashed border-gray-200 hover:border-gray-300 bg-white text-gray-400 hover:text-gray-600 transition-all">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <span className="text-sm font-medium">Connect another brokerage</span>
          </button>
        </div>

        {/* Spacer for mobile nav */}
        <div className="h-20 md:h-6" />
      </div>

      {showModal && (
        <ConnectModal
          brokerages={brokerages}
          connecting={connecting}
          selectedBroker={selectedBroker}
          iframeUrl={iframeUrl}
          onConnect={handleConnect}
          onClose={() => { setShowModal(false); setIframeUrl(null); setConnecting(false); setSelectedBroker(null); }}
        />
      )}
      {showCdslModal && (
        <CdslConnectModal
          onClose={() => setShowCdslModal(false)}
          onConnected={() => { initRef.current = false; loadData(); }}
        />
      )}
    </div>
  );
}
