'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { botsApi, apiKeysApi, snaptradeApi } from '@/lib/api';
import type { Bot, ApiKeyInfo } from '@/lib/types';
import BotCard, { CreateBotCard } from './BotCard';
import {
  Bot as BotIcon,
  Link2,
  Settings,
  LogOut,
  ChevronRight,
  ExternalLink,
  Check,
  Minus,
  TrendingUp,
  Wallet,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type Tab = 'bots' | 'connections';

interface ConnectionStatus {
  kalshi: { connected: boolean; masked?: string };
  polymarket: { connected: boolean; masked?: string };
  snaptrade: { connected: boolean; brokerages?: string[]; accountCount?: number };
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

export default function BotGrid() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>('bots');
  const [bots, setBots] = useState<Bot[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [connections, setConnections] = useState<ConnectionStatus>({
    kalshi: { connected: false },
    polymarket: { connected: false },
    snaptrade: { connected: false },
  });
  const [connectionsLoading, setConnectionsLoading] = useState(true);
  const [showAccountMenu, setShowAccountMenu] = useState(false);

  // ── Fetchers ──────────────────────────────────────────────────────────────

  const fetchBots = useCallback(async () => {
    if (!user) return;
    try {
      const data = await botsApi.listBots(user.id);
      setBots(data);
    } catch (e) {
      console.error('Failed to fetch bots:', e);
    } finally {
      setLoading(false);
    }
  }, [user]);

  const fetchConnections = useCallback(async () => {
    if (!user) return;
    try {
      const [keysRes, snapRes] = await Promise.allSettled([
        apiKeysApi.getApiKeys(user.id),
        snaptradeApi.checkStatus(user.id),
      ]);

      const next: ConnectionStatus = {
        kalshi: { connected: false },
        polymarket: { connected: false },
        snaptrade: { connected: false },
      };

      if (keysRes.status === 'fulfilled' && keysRes.value.success) {
        const keys: ApiKeyInfo[] = keysRes.value.keys;
        const kalshi = keys.find((k) => k.service === 'kalshi');
        const poly = keys.find((k) => k.service === 'polymarket');
        if (kalshi) next.kalshi = { connected: true, masked: kalshi.api_key_id_masked };
        if (poly) next.polymarket = { connected: true, masked: poly.api_key_id_masked };
      }

      if (snapRes.status === 'fulfilled' && snapRes.value.is_connected) {
        next.snaptrade = {
          connected: true,
          brokerages: snapRes.value.brokerages,
          accountCount: snapRes.value.account_count,
        };
      }

      setConnections(next);
    } catch (e) {
      console.error('Failed to fetch connections:', e);
    } finally {
      setConnectionsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchBots();
    fetchConnections();
  }, [fetchBots, fetchConnections]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleCreateBot = async () => {
    if (!user || creating) return;
    setCreating(true);
    try {
      const bot = await botsApi.createBot(user.id, { name: 'New Bot' });
      router.push(`/bot/${bot.id}`);
    } catch (e) {
      console.error('Failed to create bot:', e);
      setCreating(false);
    }
  };

  // ── Derived data ──────────────────────────────────────────────────────────

  const totalPnl = bots.reduce((sum, b) => sum + (b.total_profit_usd || 0) + (b.open_unrealized_pnl || 0), 0);
  const activeBots = bots.filter((b) => b.enabled).length;
  const connectedCount = [connections.kalshi, connections.polymarket, connections.snaptrade].filter(
    (c) => c.connected,
  ).length;

  if (!user) return null;

  const displayName = user.user_metadata?.full_name || user.email?.split('@')[0] || 'Account';
  const avatarUrl = user.user_metadata?.avatar_url;
  const initials = displayName.charAt(0).toUpperCase();

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#fafaf9]">
      <div className="max-w-3xl mx-auto px-5 sm:px-8">
        {/* ── Top bar ── */}
        <header className="flex items-center justify-between pt-8 pb-6">
          <h1 className="text-[22px] font-bold text-gray-900 tracking-tight">Finch</h1>

          {/* Account */}
          <div className="relative">
            <button
              onClick={() => setShowAccountMenu(!showAccountMenu)}
              className="flex items-center gap-2.5 py-1.5 pl-1.5 pr-3 rounded-full hover:bg-gray-100 transition-colors duration-150"
            >
              {avatarUrl ? (
                <img src={avatarUrl} alt="" className="w-7 h-7 rounded-full object-cover" />
              ) : (
                <div className="w-7 h-7 rounded-full bg-gray-800 text-white flex items-center justify-center text-xs font-semibold">
                  {initials}
                </div>
              )}
              <span className="text-sm font-medium text-gray-600 hidden sm:block">{displayName}</span>
            </button>

            {showAccountMenu && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowAccountMenu(false)} />
                <div className="absolute right-0 mt-1.5 w-56 bg-white rounded-xl border border-gray-100 shadow-lg shadow-gray-200/60 z-50 py-1.5 animate-in fade-in slide-in-from-top-1 duration-150">
                  <div className="px-4 py-2.5 border-b border-gray-100">
                    <p className="text-sm font-semibold text-gray-900 truncate">{displayName}</p>
                    {user.email && (
                      <p className="text-xs text-gray-400 mt-0.5 truncate">{user.email}</p>
                    )}
                  </div>
                  <button
                    onClick={() => { setShowAccountMenu(false); router.push('/settings'); }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>
                  <button
                    onClick={() => { setShowAccountMenu(false); signOut(); }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              </>
            )}
          </div>
        </header>

        {/* ── Tabs ── */}
        <nav className="flex gap-1 mb-8 border-b border-gray-150">
          <TabButton
            active={tab === 'bots'}
            onClick={() => setTab('bots')}
            icon={<BotIcon className="w-4 h-4" />}
            label="Bots"
            badge={bots.length > 0 ? String(bots.length) : undefined}
          />
          <TabButton
            active={tab === 'connections'}
            onClick={() => setTab('connections')}
            icon={<Link2 className="w-4 h-4" />}
            label="Connections"
            badge={connectedCount > 0 ? String(connectedCount) : undefined}
          />
        </nav>

        {/* ── Tab content ── */}
        {tab === 'bots' && (
          <BotsTab
            bots={bots}
            loading={loading}
            creating={creating}
            totalPnl={totalPnl}
            activeBots={activeBots}
            onCreateBot={handleCreateBot}
            onBotClick={(id) => router.push(`/bot/${id}`)}
          />
        )}

        {tab === 'connections' && (
          <ConnectionsTab
            connections={connections}
            loading={connectionsLoading}
            onNavigate={(path) => router.push(path)}
          />
        )}

        <div className="h-16" />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab button
// ─────────────────────────────────────────────────────────────────────────────

function TabButton({
  active,
  onClick,
  icon,
  label,
  badge,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  badge?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`relative flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors duration-150 ${
        active
          ? 'text-gray-900'
          : 'text-gray-400 hover:text-gray-600'
      }`}
    >
      {icon}
      {label}
      {badge && (
        <span
          className={`text-[11px] px-1.5 py-0.5 rounded-full font-semibold tabular-nums ${
            active ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-400'
          }`}
        >
          {badge}
        </span>
      )}
      {active && (
        <span className="absolute bottom-0 left-4 right-4 h-[2px] bg-gray-900 rounded-full" />
      )}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Bots tab
// ─────────────────────────────────────────────────────────────────────────────

function BotsTab({
  bots,
  loading,
  creating,
  totalPnl,
  activeBots,
  onCreateBot,
  onBotClick,
}: {
  bots: Bot[];
  loading: boolean;
  creating: boolean;
  totalPnl: number;
  activeBots: number;
  onCreateBot: () => void;
  onBotClick: (id: string) => void;
}) {
  return (
    <div>
      {/* Summary strip */}
      {bots.length > 0 && (
        <div className="flex items-center gap-5 mb-6 px-1">
          <div>
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Total P&L</p>
            <p className={`text-lg font-bold tabular-nums tracking-tight ${totalPnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {totalPnl >= 0 ? '+' : ''}${Math.abs(totalPnl).toFixed(2)}
            </p>
          </div>
          <div className="w-px h-8 bg-gray-200" />
          <div>
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Active</p>
            <p className="text-lg font-bold text-gray-900 tabular-nums tracking-tight">
              {activeBots}<span className="text-gray-300 font-normal">/{bots.length}</span>
            </p>
          </div>
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3.5">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-[148px] rounded-2xl bg-gray-100/70 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3.5">
          <CreateBotCard onClick={onCreateBot} disabled={creating} />
          {bots.map((bot) => (
            <BotCard key={bot.id} bot={bot} onClick={() => onBotClick(bot.id)} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Connections tab
// ─────────────────────────────────────────────────────────────────────────────

function ConnectionsTab({
  connections,
  loading,
  onNavigate,
}: {
  connections: ConnectionStatus;
  loading: boolean;
  onNavigate: (path: string) => void;
}) {
  const items = [
    {
      key: 'kalshi',
      name: 'Kalshi',
      description: 'Prediction markets',
      icon: <TrendingUp className="w-5 h-5" />,
      iconBg: 'bg-violet-50 text-violet-500',
      connected: connections.kalshi.connected,
      detail: connections.kalshi.masked || 'API key connected',
      path: '/settings',
    },
    {
      key: 'polymarket',
      name: 'Polymarket',
      description: 'Prediction markets',
      icon: <TrendingUp className="w-5 h-5" />,
      iconBg: 'bg-sky-50 text-sky-500',
      connected: connections.polymarket.connected,
      detail: connections.polymarket.masked || 'Wallet connected',
      path: '/settings',
    },
    {
      key: 'snaptrade',
      name: 'Portfolio',
      description: 'Brokerage accounts via SnapTrade',
      icon: <Wallet className="w-5 h-5" />,
      iconBg: 'bg-amber-50 text-amber-500',
      connected: connections.snaptrade.connected,
      detail: connections.snaptrade.connected
        ? `${connections.snaptrade.accountCount || 0} account${(connections.snaptrade.accountCount || 0) !== 1 ? 's' : ''} linked`
        : undefined,
      path: '/portfolio',
    },
  ];

  return (
    <div>
      <p className="text-sm text-gray-400 mb-5 px-1">
        Connect your trading platforms and brokerage accounts.
      </p>

      <div className="space-y-2.5">
        {items.map((item) => (
          <button
            key={item.key}
            onClick={() => onNavigate(item.path)}
            className="group w-full flex items-center gap-4 p-4 rounded-2xl bg-white border border-gray-100 hover:border-gray-200 shadow-[0_1px_3px_rgba(0,0,0,0.03)] hover:shadow-[0_3px_10px_rgba(0,0,0,0.05)] transition-all duration-200 text-left"
          >
            {/* Icon */}
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${item.iconBg}`}>
              {item.icon}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2.5">
                <span className="text-[15px] font-semibold text-gray-900">{item.name}</span>
                {loading ? (
                  <span className="w-2 h-2 rounded-full bg-gray-200 animate-pulse" />
                ) : item.connected ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                    <Check className="w-3 h-3" />
                    Connected
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-gray-400 bg-gray-50 px-2 py-0.5 rounded-full">
                    <Minus className="w-3 h-3" />
                    Not set up
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-0.5 truncate">
                {!loading && item.connected && item.detail ? item.detail : item.description}
              </p>
            </div>

            {/* Arrow */}
            <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-400 flex-shrink-0 transition-colors" />
          </button>
        ))}
      </div>
    </div>
  );
}
