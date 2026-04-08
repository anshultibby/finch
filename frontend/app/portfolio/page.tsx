'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { snaptradeApi } from '@/lib/api';
import type { PortfolioResponse, PortfolioPerformance, Position, BrokerageAccount, Brokerage } from '@/lib/types';

// ── Broker accent palette ──────────────────────────────────────────────────
const BROKER_ACCENTS: Record<string, { bg: string; text: string; ring: string; dot: string }> = {
  ROBINHOOD:            { bg: 'bg-emerald-50',  text: 'text-emerald-700',  ring: 'ring-emerald-200',  dot: 'bg-emerald-500'  },
  ALPACA:               { bg: 'bg-teal-50',     text: 'text-teal-700',     ring: 'ring-teal-200',     dot: 'bg-teal-500'     },
  SCHWAB:               { bg: 'bg-blue-50',     text: 'text-blue-700',     ring: 'ring-blue-200',     dot: 'bg-blue-500'     },
  FIDELITY:             { bg: 'bg-red-50',      text: 'text-red-700',      ring: 'ring-red-200',      dot: 'bg-red-500'      },
  ETRADE:               { bg: 'bg-violet-50',   text: 'text-violet-700',   ring: 'ring-violet-200',   dot: 'bg-violet-500'   },
  INTERACTIVE_BROKERS:  { bg: 'bg-slate-100',   text: 'text-slate-700',    ring: 'ring-slate-200',    dot: 'bg-slate-500'    },
  TD:                   { bg: 'bg-green-50',    text: 'text-green-700',    ring: 'ring-green-200',    dot: 'bg-green-500'    },
  WEBULL:               { bg: 'bg-orange-50',   text: 'text-orange-700',   ring: 'ring-orange-200',   dot: 'bg-orange-500'   },
  QUESTRADE:            { bg: 'bg-rose-50',     text: 'text-rose-700',     ring: 'ring-rose-200',     dot: 'bg-rose-500'     },
  MOOMOO:               { bg: 'bg-amber-50',    text: 'text-amber-700',    ring: 'ring-amber-200',    dot: 'bg-amber-500'    },
  TRADIER:              { bg: 'bg-indigo-50',   text: 'text-indigo-700',   ring: 'ring-indigo-200',   dot: 'bg-indigo-500'   },
  WEALTHSIMPLE:         { bg: 'bg-zinc-100',    text: 'text-zinc-700',     ring: 'ring-zinc-200',     dot: 'bg-zinc-500'     },
};
const DEFAULT_ACCENT = { bg: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-200', dot: 'bg-blue-500' };

const BROKER_EMOJI: Record<string, string> = {
  robinhood: '🪶',
  alpaca: '🦙',
  schwab: '🏛',
  fidelity: '🔴',
  etrade: '📈',
  interactive: '🌐',
  td: '🍁',
  webull: '🐂',
  questrade: '🍁',
  moomoo: '🐄',
  tradier: '⚡',
  wealthsimple: '✦',
};

function brokerAccent(brokerId: string) {
  const key = brokerId?.toUpperCase().replace(/[^A-Z_]/g, '_');
  return BROKER_ACCENTS[key] ?? DEFAULT_ACCENT;
}

function brokerEmoji(brokerName: string): string {
  const key = brokerName?.toLowerCase() ?? '';
  return Object.entries(BROKER_EMOJI).find(([k]) => key.includes(k))?.[1] ?? '🏦';
}

// ── Shimmer skeleton ────────────────────────────────────────────────────────
function Shimmer({ className = '' }: { className?: string }) {
  return <div className={`animate-shimmer rounded-lg ${className}`} />;
}

function LoadingSkeleton() {
  return (
    <div className="min-h-screen" style={{ background: 'var(--finch-bg)' }}>
      {/* Header shimmer */}
      <div className="bg-white border-b" style={{ borderColor: 'var(--finch-border)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Shimmer className="h-7 w-32" />
              <Shimmer className="h-4 w-48" />
            </div>
            <div className="flex gap-2">
              <Shimmer className="h-9 w-24" />
              <Shimmer className="h-9 w-28" />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="finch-surface rounded-2xl p-5 space-y-3">
              <Shimmer className="h-3 w-20" />
              <Shimmer className="h-8 w-28" />
              <Shimmer className="h-3 w-16" />
            </div>
          ))}
        </div>

        {/* Account cards */}
        <div>
          <Shimmer className="h-5 w-28 mb-4" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="finch-surface rounded-2xl p-5 space-y-4">
                <div className="flex items-center gap-3">
                  <Shimmer className="h-10 w-10 rounded-full" />
                  <div className="space-y-1.5 flex-1">
                    <Shimmer className="h-4 w-32" />
                    <Shimmer className="h-3 w-20" />
                  </div>
                </div>
                <Shimmer className="h-7 w-28" />
                <div className="flex items-center justify-between">
                  <Shimmer className="h-5 w-16 rounded-full" />
                  <Shimmer className="h-6 w-10 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Holdings table */}
        <div className="finch-surface rounded-2xl overflow-hidden">
          <div className="px-6 py-4 border-b" style={{ borderColor: 'var(--finch-border)' }}>
            <Shimmer className="h-5 w-24" />
          </div>
          <div className="p-4 space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="flex items-center gap-4 py-2">
                <Shimmer className="h-4 w-12" />
                <Shimmer className="h-4 flex-1 max-w-[80px]" />
                <Shimmer className="h-4 w-20 ml-auto" />
                <Shimmer className="h-4 w-20" />
                <Shimmer className="h-4 w-20" />
                <Shimmer className="h-4 w-16" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Connect modal ────────────────────────────────────────────────────────────
function ConnectModal({
  brokerages,
  connecting,
  selectedBroker,
  onConnect,
  onClose,
}: {
  brokerages: Brokerage[];
  connecting: boolean;
  selectedBroker: string | null;
  onConnect: (id: string) => void;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(15,23,42,0.45)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[80vh] overflow-hidden animate-card-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="px-6 py-4 flex items-center justify-between border-b" style={{ borderColor: 'var(--finch-border)' }}>
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Connect a brokerage</h3>
            <p className="text-sm text-slate-500 mt-0.5">All accounts from that broker will be imported</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg p-1.5 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5 overflow-y-auto max-h-[calc(80vh-76px)]">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {brokerages.map((broker) => {
              const isConnecting = connecting && selectedBroker === broker.id;
              const isDisabled = connecting && selectedBroker !== broker.id;
              return (
                <button
                  key={broker.id}
                  onClick={() => onConnect(broker.id)}
                  disabled={isDisabled}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all text-center
                    ${isConnecting
                      ? 'border-green-400 bg-green-50'
                      : 'border-transparent hover:border-slate-200 hover:bg-slate-50'
                    }
                    ${isDisabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}
                  `}
                  style={{ background: isConnecting ? undefined : 'var(--finch-surface)', borderColor: isConnecting ? undefined : 'var(--finch-border)' }}
                >
                  <span className="text-3xl leading-none">{broker.logo}</span>
                  <span className="text-xs font-medium text-slate-700 leading-tight">{broker.name}</span>
                  {isConnecting && (
                    <span className="text-xs text-green-600 font-medium">Connecting…</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Account card ─────────────────────────────────────────────────────────────
function AccountCard({
  account,
  onToggle,
  onDisconnect,
  formatCurrency,
  animDelay,
}: {
  account: BrokerageAccount;
  onToggle: (id: string, current: boolean) => void;
  onDisconnect: (id: string, name: string) => void;
  formatCurrency: (n: number) => string;
  animDelay: number;
}) {
  const accent = brokerAccent(account.broker_id);
  const isActive = account.balance !== null;
  const emoji = brokerEmoji(account.broker_name);

  return (
    <div
      className="finch-surface finch-surface-hover animate-card-in rounded-2xl p-5 flex flex-col gap-4"
      style={{ animationDelay: `${animDelay}ms` }}
    >
      {/* Top row: icon + name + disconnect */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl flex-shrink-0 ${accent.bg} ring-1 ${accent.ring}`}>
            {emoji}
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-slate-900 text-sm leading-tight truncate">{account.name}</p>
            <p className="text-xs text-slate-500 mt-0.5 truncate">{account.broker_name}</p>
          </div>
        </div>
        <button
          onClick={() => onDisconnect(account.account_id, account.name)}
          className="text-slate-300 hover:text-red-400 hover:bg-red-50 p-1.5 rounded-lg transition-colors flex-shrink-0"
          title="Disconnect account"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>

      {/* Balance */}
      <div>
        <p className="text-xs text-slate-400 uppercase tracking-wide font-medium mb-0.5">Balance</p>
        <p className="text-2xl font-bold text-slate-900 tabular-nums">{formatCurrency(account.balance ?? 0)}</p>
      </div>

      {/* Bottom row: type badge + toggle */}
      <div className="flex items-center justify-between">
        <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${accent.bg} ${accent.text}`}>
          {account.type || 'Account'}
        </span>

        <label className="relative inline-flex items-center cursor-pointer gap-2">
          <span className="text-xs text-slate-400">{isActive ? 'Visible' : 'Hidden'}</span>
          <div className="relative">
            <input
              type="checkbox"
              checked={isActive}
              onChange={() => onToggle(account.account_id, isActive)}
              className="sr-only peer"
            />
            <div className={`w-9 h-5 rounded-full peer transition-colors
              ${isActive ? 'bg-green-500' : 'bg-slate-200'}
              peer-focus:ring-2 peer-focus:ring-green-300
            `} />
            <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform
              ${isActive ? 'translate-x-4' : 'translate-x-0'}
            `} />
          </div>
        </label>
      </div>
    </div>
  );
}

// ── Connect CTA card ─────────────────────────────────────────────────────────
function ConnectAccountCard({ onClick, animDelay }: { onClick: () => void; animDelay: number }) {
  return (
    <button
      onClick={onClick}
      className="animate-card-in rounded-2xl border-2 border-dashed flex flex-col items-center justify-center gap-3 py-8 px-5 transition-all hover:border-green-400 hover:bg-green-50 group"
      style={{
        borderColor: 'var(--finch-border-strong)',
        animationDelay: `${animDelay}ms`,
        minHeight: '160px',
      }}
    >
      <div className="w-10 h-10 rounded-full bg-slate-100 group-hover:bg-green-100 flex items-center justify-center transition-colors">
        <svg className="w-5 h-5 text-slate-400 group-hover:text-green-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      </div>
      <span className="text-sm font-medium text-slate-500 group-hover:text-green-700 transition-colors">Connect Account</span>
    </button>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function PortfolioPage() {
  const { user } = useAuth();
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [allAccounts, setAllAccounts] = useState<BrokerageAccount[]>([]);
  const [brokerages, setBrokerages] = useState<Brokerage[]>([]);
  const [loading, setLoading] = useState(true);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [selectedBroker, setSelectedBroker] = useState<string | null>(null);

  useEffect(() => {
    if (user?.id) {
      loadData();
    }
  }, [user?.id]);

  const loadData = async () => {
    if (!user?.id) return;

    setLoading(true);
    try {
      const [portfolioData, performanceData, accountsResponse, brokeragesResponse] = await Promise.all([
        snaptradeApi.getPortfolio(user.id),
        snaptradeApi.getPortfolioPerformance(user.id),
        snaptradeApi.getAccounts(user.id),
        snaptradeApi.getBrokerages(),
      ]);

      setPortfolio(portfolioData);
      setPerformance(performanceData);

      if (accountsResponse.success) {
        setAllAccounts(accountsResponse.accounts);
      }

      if (brokeragesResponse.success) {
        setBrokerages(brokeragesResponse.brokerages);
      }
    } catch (error) {
      console.error('Error loading portfolio:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnectBroker = async (brokerId: string) => {
    if (!user?.id) return;

    setConnecting(true);
    setSelectedBroker(brokerId);

    try {
      const redirectUri = `${window.location.origin}${window.location.pathname}?snaptrade_callback=true`;
      const response = await snaptradeApi.connectBroker(user.id, redirectUri, brokerId);

      if (response.success && response.redirect_uri) {
        const popup = window.open(
          response.redirect_uri,
          'SnapTrade Connection',
          'width=500,height=700,resizable=yes,scrollbars=yes'
        );

        if (!popup || popup.closed) {
          alert('Popup was blocked. Please allow popups for this site.');
          setConnecting(false);
          return;
        }

        const handleMessage = (event: MessageEvent) => {
          if (event.origin !== window.location.origin) return;

          if (event.data.type === 'SNAPTRADE_CONNECTION') {
            window.removeEventListener('message', handleMessage);
            setConnecting(false);
            setSelectedBroker(null);
            setShowConnectModal(false);

            if (event.data.success) {
              loadData();
              // Force-rebuild history to include the newly connected account
              if (user?.id) {
                snaptradeApi.buildPortfolioHistory(user.id, undefined, true).catch(() => {});
              }
            }
          }
        };

        window.addEventListener('message', handleMessage);

        setTimeout(() => {
          window.removeEventListener('message', handleMessage);
          if (connecting) {
            setConnecting(false);
            setSelectedBroker(null);
          }
        }, 300000);
      }
    } catch (err) {
      console.error('Error connecting broker:', err);
      setConnecting(false);
      setSelectedBroker(null);
    }
  };

  const handleToggleAccount = async (accountId: string, currentState: boolean) => {
    if (!user?.id) return;

    try {
      await snaptradeApi.toggleAccountVisibility(user.id, accountId, !currentState);
      await loadData();
    } catch (error) {
      console.error('Error toggling account:', error);
    }
  };

  const handleDisconnectAccount = async (accountId: string, accountName: string) => {
    if (!user?.id) return;

    if (!confirm(`Disconnect ${accountName}? This will remove it from your portfolio.`)) {
      return;
    }

    try {
      await snaptradeApi.disconnectAccount(user.id, accountId);
      await loadData();
    } catch (error) {
      console.error('Error disconnecting account:', error);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercent = (percent: number) => {
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(2)}%`;
  };

  const parseHoldings = (csv: string): Position[] => {
    if (!csv) return [];

    const lines = csv.split('\n');
    if (lines.length < 2) return [];

    const headers = lines[0].split(',');
    const positions: Position[] = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',');
      if (values.length < headers.length) continue;

      const position: any = {};
      headers.forEach((header, index) => {
        const value = values[index];
        if (value && value !== 'None') {
          const numValue = parseFloat(value);
          position[header] = isNaN(numValue) ? value : numValue;
        }
      });

      if (position.symbol) {
        positions.push(position as Position);
      }
    }

    return positions;
  };

  // ── Auth guard ──────────────────────────────────────────────────────────────
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--finch-bg)' }}>
        <div className="finch-surface rounded-2xl p-10 text-center max-w-sm w-full animate-card-in">
          <div className="text-4xl mb-4">🔒</div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Sign in to continue</h2>
          <p className="text-slate-500 text-sm">You need to be signed in to view your portfolio.</p>
        </div>
      </div>
    );
  }

  // ── Loading state ───────────────────────────────────────────────────────────
  if (loading) {
    return <LoadingSkeleton />;
  }

  // ── Empty / no accounts state ───────────────────────────────────────────────
  if (allAccounts.length === 0) {
    const floatingEmojis = ['🪶', '🦙', '🏛', '📈', '🌐', '🐂', '⚡'];
    return (
      <>
        <div
          className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden"
          style={{ background: 'var(--finch-bg)' }}
        >
          {/* Ambient broker emoji grid */}
          <div className="absolute inset-0 pointer-events-none select-none" aria-hidden>
            {floatingEmojis.map((e, i) => (
              <span
                key={i}
                className="absolute text-4xl opacity-[0.06]"
                style={{
                  left: `${10 + (i * 14) % 80}%`,
                  top: `${8 + (i * 23) % 75}%`,
                  transform: `rotate(${(i % 2 === 0 ? 1 : -1) * (8 + i * 3)}deg)`,
                  animationName: 'cardIn',
                  animationDuration: '0.6s',
                  animationDelay: `${i * 80}ms`,
                  animationFillMode: 'both',
                  animationTimingFunction: 'cubic-bezier(0.22,1,0.36,1)',
                }}
              >
                {e}
              </span>
            ))}
          </div>

          {/* CTA card */}
          <div className="finch-surface rounded-2xl p-10 text-center max-w-md w-full animate-card-in relative z-10">
            <div className="w-16 h-16 rounded-2xl bg-green-50 flex items-center justify-center text-3xl mx-auto mb-6">
              📊
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mb-3">Connect your brokerage</h1>
            <p className="text-slate-500 mb-8 text-sm leading-relaxed">
              Link your brokerage accounts to track your portfolio, see performance, and manage investments — all in one place.
            </p>
            <button
              onClick={() => setShowConnectModal(true)}
              className="w-full bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded-xl font-semibold transition-colors shadow-sm"
            >
              Connect Account
            </button>
            <p className="text-xs text-slate-400 mt-4">
              Robinhood, Schwab, Fidelity, E*TRADE, and 8+ more
            </p>
          </div>
        </div>

        {showConnectModal && (
          <ConnectModal
            brokerages={brokerages}
            connecting={connecting}
            selectedBroker={selectedBroker}
            onConnect={handleConnectBroker}
            onClose={() => setShowConnectModal(false)}
          />
        )}
      </>
    );
  }

  // ── Main portfolio view ─────────────────────────────────────────────────────
  const holdings = parseHoldings(portfolio?.holdings_csv || '');
  // Sort by market value descending
  const sortedHoldings = [...holdings].sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
  const totalValue = portfolio?.total_value || 0;
  const gainLoss = performance?.total_gain_loss || 0;
  const gainLossPct = performance?.total_gain_loss_percent || 0;
  const isPositive = gainLoss >= 0;

  return (
    <div className="min-h-screen" style={{ background: 'var(--finch-bg)' }}>

      {/* ── Page header ──────────────────────────────────────────────────────── */}
      <div className="bg-white sticky top-0 z-30 border-b" style={{ borderColor: 'var(--finch-border)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-900">Portfolio</h1>
              <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                {allAccounts.length} account{allAccounts.length !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {/* Refresh */}
              <button
                onClick={loadData}
                className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
                title="Refresh"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span className="hidden sm:inline">Refresh</span>
              </button>
              {/* Connect */}
              <button
                onClick={() => setShowConnectModal(true)}
                className="flex items-center gap-1.5 bg-green-500 hover:bg-green-600 text-white px-3 py-2 rounded-lg text-sm font-semibold transition-colors shadow-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span className="hidden sm:inline">Connect</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">

        {/* ── Stat cards ────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Total Value */}
          <div className="finch-surface rounded-2xl p-5 animate-card-in stat-glow-neutral" style={{ animationDelay: '0ms' }}>
            <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">Total Value</p>
            <p className="text-3xl font-bold text-slate-900 tabular-nums leading-tight">
              {formatCurrency(totalValue)}
            </p>
            <p className="text-xs text-slate-400 mt-2">{portfolio?.total_positions ?? 0} positions</p>
          </div>

          {/* Total Return */}
          <div
            className={`finch-surface rounded-2xl p-5 animate-card-in ${isPositive ? 'stat-glow-positive' : 'stat-glow-negative'}`}
            style={{ animationDelay: '50ms' }}
          >
            <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">Total Return</p>
            <p className={`text-3xl font-bold tabular-nums leading-tight ${isPositive ? 'text-green-600' : 'text-red-500'}`}>
              {formatCurrency(gainLoss)}
            </p>
            <p className={`text-xs mt-2 font-medium ${isPositive ? 'text-green-500' : 'text-red-400'}`}>
              {formatPercent(gainLossPct)}
            </p>
          </div>

          {/* Total Cost */}
          <div className="finch-surface rounded-2xl p-5 animate-card-in stat-glow-neutral" style={{ animationDelay: '100ms' }}>
            <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">Cost Basis</p>
            <p className="text-3xl font-bold text-slate-900 tabular-nums leading-tight">
              {formatCurrency(performance?.total_cost || 0)}
            </p>
            <p className="text-xs text-slate-400 mt-2">amount invested</p>
          </div>

          {/* Accounts */}
          <div className="finch-surface rounded-2xl p-5 animate-card-in stat-glow-neutral" style={{ animationDelay: '150ms' }}>
            <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">Accounts</p>
            <p className="text-3xl font-bold text-slate-900 tabular-nums leading-tight">
              {allAccounts.length}
            </p>
            <p className="text-xs text-slate-400 mt-2">
              {allAccounts.filter(a => a.balance !== null).length} visible
            </p>
          </div>
        </div>

        {/* ── Accounts section (inline) ─────────────────────────────────────── */}
        <section>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Accounts</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {allAccounts.map((account, i) => (
              <AccountCard
                key={account.id}
                account={account}
                onToggle={handleToggleAccount}
                onDisconnect={handleDisconnectAccount}
                formatCurrency={formatCurrency}
                animDelay={i * 40}
              />
            ))}
            <ConnectAccountCard
              onClick={() => setShowConnectModal(true)}
              animDelay={allAccounts.length * 40}
            />
          </div>
        </section>

        {/* ── Holdings table ────────────────────────────────────────────────── */}
        {sortedHoldings.length > 0 && (
          <section className="animate-card-in" style={{ animationDelay: '200ms' }}>
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Holdings</h2>
            <div className="finch-surface rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b" style={{ borderColor: 'var(--finch-border)' }}>
                      <th className="px-6 py-3.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Symbol</th>
                      <th className="px-4 py-3.5 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Qty</th>
                      <th className="px-4 py-3.5 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Price</th>
                      <th className="px-4 py-3.5 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Value</th>
                      <th className="px-4 py-3.5 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider hidden md:table-cell">Avg Cost</th>
                      <th className="px-4 py-3.5 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Gain / Loss</th>
                      <th className="px-6 py-3.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider hidden lg:table-cell w-36">Allocation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedHoldings.map((position, index) => {
                      const gl = position.gain_loss || 0;
                      const glPct = position.gain_loss_percent || 0;
                      const allocationPct = totalValue > 0 ? (position.value / totalValue) * 100 : 0;

                      return (
                        <tr
                          key={index}
                          className="border-b last:border-0 hover:bg-slate-50 transition-colors"
                          style={{ borderColor: 'var(--finch-border)' }}
                        >
                          {/* Symbol */}
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="inline-flex items-center gap-2">
                              <span className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-600">
                                {position.symbol?.charAt(0)}
                              </span>
                              <span className="font-semibold text-slate-900 text-sm">{position.symbol}</span>
                            </span>
                          </td>

                          {/* Qty */}
                          <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-slate-600 tabular-nums">
                            {position.quantity?.toFixed(4)}
                          </td>

                          {/* Price */}
                          <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-slate-700 tabular-nums">
                            {formatCurrency(position.price)}
                          </td>

                          {/* Value */}
                          <td className="px-4 py-4 whitespace-nowrap text-right">
                            <span className="font-semibold text-slate-900 text-sm tabular-nums">
                              {formatCurrency(position.value)}
                            </span>
                          </td>

                          {/* Avg cost */}
                          <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-slate-500 tabular-nums hidden md:table-cell">
                            {position.average_purchase_price ? formatCurrency(position.average_purchase_price) : <span className="text-slate-300">—</span>}
                          </td>

                          {/* Gain / loss */}
                          <td className="px-4 py-4 whitespace-nowrap text-right">
                            {gl !== 0 ? (
                              <div className="space-y-0.5">
                                <p className={`text-sm font-semibold tabular-nums ${gl >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                                  {formatCurrency(gl)}
                                </p>
                                <p className={`text-xs tabular-nums ${glPct >= 0 ? 'text-green-500' : 'text-red-400'}`}>
                                  {formatPercent(glPct)}
                                </p>
                              </div>
                            ) : (
                              <span className="text-slate-300 text-sm">—</span>
                            )}
                          </td>

                          {/* Allocation bar */}
                          <td className="px-6 py-4 hidden lg:table-cell">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-green-400 rounded-full"
                                  style={{ width: `${Math.min(allocationPct, 100)}%` }}
                                />
                              </div>
                              <span className="text-xs text-slate-400 tabular-nums w-10 text-right">
                                {allocationPct.toFixed(1)}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}
      </div>

      {/* ── Connect modal ─────────────────────────────────────────────────────── */}
      {showConnectModal && (
        <ConnectModal
          brokerages={brokerages}
          connecting={connecting}
          selectedBroker={selectedBroker}
          onConnect={handleConnectBroker}
          onClose={() => setShowConnectModal(false)}
        />
      )}
    </div>
  );
}
