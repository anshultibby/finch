'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { botsApi, apiKeysApi, snaptradeApi } from '@/lib/api';
import type { Bot, ApiKeyInfo } from '@/lib/types';
import BotCard, { CreateBotCard } from './BotCard';
import BotVisualizationsPanel from './BotVisualizationsPanel';
import {
  Bot as BotIcon,
  Link2,
  LogOut,
  Check,
  TrendingUp,
  Wallet,
  Key,
  Shield,
  ExternalLink,
  Eye,
  EyeOff,
  Loader2,
  Trash2,
  ChevronDown,
  ChevronUp,
  X,
  BarChart3,
  Search,
  Briefcase,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type Tab = 'bots' | 'connections' | 'portfolio' | 'visualizations';

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
  const [showCreateModal, setShowCreateModal] = useState(false);

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

  const handleCreateBot = async (data: { name: string; platform: string; capital_amount?: number }) => {
    if (!user || creating) return;
    setCreating(true);
    try {
      const bot = await botsApi.createBot(user.id, data);
      router.push(`/bot/${bot.id}`);
    } catch (e) {
      console.error('Failed to create bot:', e);
      setCreating(false);
    }
  };

  const handleDeleteBot = async (botId: string) => {
    if (!user) return;
    try {
      await botsApi.deleteBot(user.id, botId);
      setBots((prev) => prev.filter((b) => b.id !== botId));
    } catch (e) {
      console.error('Failed to delete bot:', e);
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
    <div className="min-h-screen bg-[#fafaf9] relative">
      <div className="max-w-3xl mx-auto px-5 sm:px-8">
        {/* ── Top bar ── */}
        <header className="flex items-center justify-between pt-8 pb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gray-900 to-gray-700 flex items-center justify-center shadow-sm">
              <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.306a11.95 11.95 0 015.814-5.518l2.74-1.22" />
              </svg>
            </div>
            <h1 className="text-[22px] font-bold text-gray-900 tracking-tight">Finch</h1>
          </div>

          {/* Account */}
          <div className="relative">
            <button
              onClick={() => setShowAccountMenu(!showAccountMenu)}
              className="flex items-center gap-2.5 py-1.5 pl-1.5 pr-3 rounded-full hover:bg-gray-100 transition-colors duration-200"
            >
              {avatarUrl ? (
                <img src={avatarUrl} alt="" className="w-7 h-7 rounded-full object-cover ring-2 ring-gray-100" />
              ) : (
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-gray-800 to-gray-600 text-white flex items-center justify-center text-xs font-semibold ring-2 ring-gray-100">
                  {initials}
                </div>
              )}
              <span className="text-sm font-medium text-gray-600 hidden sm:block">{displayName}</span>
            </button>

            {showAccountMenu && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowAccountMenu(false)} />
                <div className="absolute right-0 mt-1.5 w-56 bg-white rounded-xl border border-gray-100 shadow-xl shadow-gray-200/40 z-50 py-1.5">
                  <div className="px-4 py-2.5 border-b border-gray-100">
                    <p className="text-sm font-semibold text-gray-900 truncate">{displayName}</p>
                    {user.email && (
                      <p className="text-xs text-gray-400 mt-0.5 truncate">{user.email}</p>
                    )}
                  </div>
                  <button
                    onClick={() => { setShowAccountMenu(false); setTab('connections'); }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                  >
                    <Key className="w-4 h-4" />
                    Connections
                  </button>
                  <button
                    onClick={() => { setShowAccountMenu(false); signOut(); }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors"
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
        <nav className="flex gap-1 mb-8 border-b border-gray-200/80">
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
          <TabButton
            active={tab === 'portfolio'}
            onClick={() => setTab('portfolio')}
            icon={<Briefcase className="w-4 h-4" />}
            label="Portfolio"
          />
          <TabButton
            active={tab === 'visualizations'}
            onClick={() => setTab('visualizations')}
            icon={<BarChart3 className="w-4 h-4" />}
            label="Visualizations"
          />
        </nav>

        {/* ── Tab content ── */}
        {tab === 'bots' && (
          <>
            <BotsTab
              bots={bots}
              loading={loading}
              creating={creating}
              totalPnl={totalPnl}
              activeBots={activeBots}
              onCreateBot={() => setShowCreateModal(true)}
              onBotClick={(id) => router.push(`/bot/${id}`)}
              onDeleteBot={handleDeleteBot}
            />
            {showCreateModal && (
              <CreateBotModal
                creating={creating}
                onClose={() => setShowCreateModal(false)}
                onCreate={(data) => handleCreateBot(data)}
              />
            )}
          </>
        )}

        {tab === 'connections' && (
          <ConnectionsTab
            connections={connections}
            loading={connectionsLoading}
            userId={user.id}
            onRefresh={fetchConnections}
          />
        )}

        {tab === 'portfolio' && (
          <PortfolioTab userId={user.id} />
        )}

        {tab === 'visualizations' && (
          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden" style={{ height: 'calc(100vh - 200px)' }}>
            <BotVisualizationsPanel />
          </div>
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
  onDeleteBot,
}: {
  bots: Bot[];
  loading: boolean;
  creating: boolean;
  totalPnl: number;
  activeBots: number;
  onCreateBot: () => void;
  onBotClick: (id: string) => void;
  onDeleteBot: (id: string) => void;
}) {
  const totalCapital = bots.reduce((sum, b) => sum + (b.capital_balance ?? 0), 0);
  const totalRuns = bots.reduce((sum, b) => sum + (b.total_runs || 0), 0);
  const totalPositions = bots.reduce((sum, b) => sum + (b.open_positions_count || 0), 0);

  return (
    <div>
      {/* Summary strip — stat cards with subtle glow */}
      {bots.length > 0 && (
        <div className="flex items-stretch gap-3 mb-8">
          <div className={`relative flex-1 rounded-xl px-4 py-3 bg-white border border-gray-100 overflow-hidden ${totalPnl >= 0 ? 'stat-glow-positive' : 'stat-glow-negative'}`}>
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Total P&L</p>
            <p className={`text-xl font-bold tabular-nums tracking-tight mt-0.5 ${totalPnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {totalPnl >= 0 ? '+' : ''}${Math.abs(totalPnl).toFixed(2)}
            </p>
          </div>
          <div className="relative flex-1 rounded-xl px-4 py-3 bg-white border border-gray-100 overflow-hidden stat-glow-neutral">
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Capital</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums tracking-tight mt-0.5">
              ${totalCapital.toFixed(0)}
            </p>
          </div>
          <div className="relative flex-1 rounded-xl px-4 py-3 bg-white border border-gray-100 overflow-hidden stat-glow-neutral">
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Active</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums tracking-tight mt-0.5">
              {activeBots}<span className="text-gray-300 font-normal text-base">/{bots.length}</span>
            </p>
          </div>
          {totalPositions > 0 && (
            <div className="relative flex-1 rounded-xl px-4 py-3 bg-white border border-gray-100 overflow-hidden stat-glow-neutral">
              <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Positions</p>
              <p className="text-xl font-bold text-gray-900 tabular-nums tracking-tight mt-0.5">{totalPositions}</p>
            </div>
          )}
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-[160px] rounded-2xl animate-shimmer" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div className="animate-card-in" style={{ animationDelay: '0ms' }}>
            <CreateBotCard onClick={onCreateBot} disabled={creating} />
          </div>
          {bots.map((bot, i) => (
            <div key={bot.id} className="animate-card-in" style={{ animationDelay: `${(i + 1) * 60}ms` }}>
              <BotCard bot={bot} onClick={() => onBotClick(bot.id)} onDelete={onDeleteBot} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Connections tab — inline credential management
// ─────────────────────────────────────────────────────────────────────────────

function ConnectionsTab({
  connections,
  loading,
  userId,
  onRefresh,
}: {
  connections: ConnectionStatus;
  loading: boolean;
  userId: string;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const toggle = (key: string) => {
    setExpanded(expanded === key ? null : key);
    setFormData({});
    setFeedback(null);
    setConfirmDelete(null);
  };

  const handleSave = async (service: string) => {
    setSaving(true);
    setFeedback(null);
    try {
      const res = await apiKeysApi.saveApiKey(userId, service, formData);
      if (res.success) {
        setFeedback({ type: 'success', message: 'Credentials saved and encrypted.' });
        setFormData({});
        onRefresh();
      } else {
        setFeedback({ type: 'error', message: res.message || 'Failed to save.' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Failed to save credentials.' });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (service: string) => {
    setTesting(true);
    setFeedback(null);
    try {
      const hasFormData = Object.values(formData).some(v => v?.trim());
      const res = hasFormData
        ? await apiKeysApi.testCredentialsBeforeSave(userId, service, formData)
        : await apiKeysApi.testApiKey(userId, service);
      setFeedback({
        type: res.success ? 'success' : 'error',
        message: res.message,
      });
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Test failed.' });
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async (service: string) => {
    try {
      await apiKeysApi.deleteApiKey(userId, service);
      setFeedback({ type: 'success', message: 'Credentials removed.' });
      setConfirmDelete(null);
      onRefresh();
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Failed to delete.' });
    }
  };

  const handleSnaptradeConnect = async () => {
    setConnecting(true);
    setFeedback(null);
    try {
      const redirectUri = `${window.location.origin}/portfolio?snaptrade_callback=true`;
      const res = await snaptradeApi.initiateConnection(userId, redirectUri);
      if (res.redirect_uri) {
        window.location.href = res.redirect_uri;
      } else {
        setFeedback({ type: 'error', message: 'Failed to get connection URL.' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Failed to start connection.' });
    } finally {
      setConnecting(false);
    }
  };

  const services = [
    {
      key: 'kalshi',
      name: 'Kalshi',
      description: 'Event contracts & prediction markets',
      icon: <TrendingUp className="w-5 h-5" />,
      iconBg: 'bg-violet-50 text-violet-500',
      connected: connections.kalshi.connected,
      masked: connections.kalshi.masked,
      helpUrl: 'https://kalshi.com/account/api',
      helpLabel: 'Get your Kalshi API key',
      fields: [
        { key: 'api_key_id', label: 'API Key ID', type: 'text' as const, placeholder: 'e.g. abc123-def456' },
        { key: 'private_key', label: 'Private Key (PEM)', type: 'textarea' as const, placeholder: '-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----' },
      ],
      steps: [
        'Go to your Kalshi account settings',
        'Navigate to API Keys section',
        'Create a new key and download the .key file',
        'Paste the Key ID and file contents here',
      ],
    },
    {
      key: 'polymarket',
      name: 'Polymarket',
      description: 'Crypto prediction markets',
      icon: <TrendingUp className="w-5 h-5" />,
      iconBg: 'bg-sky-50 text-sky-500',
      connected: connections.polymarket.connected,
      masked: connections.polymarket.masked,
      helpUrl: undefined,
      helpLabel: undefined,
      fields: [
        { key: 'private_key', label: 'Wallet Private Key', type: 'text' as const, placeholder: '0x...' },
        { key: 'funder_address', label: 'Funder Address (optional)', type: 'text' as const, placeholder: '0x...' },
      ],
      steps: [
        'Export your private key from MetaMask or your wallet',
        'In MetaMask: Account menu → Account Details → Show Private Key',
        'Paste the key (starts with 0x) here',
      ],
    },
    {
      key: 'snaptrade',
      name: 'Portfolio',
      description: 'Connect your brokerage account via SnapTrade',
      icon: <Wallet className="w-5 h-5" />,
      iconBg: 'bg-amber-50 text-amber-500',
      connected: connections.snaptrade.connected,
      masked: connections.snaptrade.connected && connections.snaptrade.accountCount
        ? `${connections.snaptrade.accountCount} account${connections.snaptrade.accountCount !== 1 ? 's' : ''} linked`
        : undefined,
      helpUrl: undefined,
      helpLabel: undefined,
      fields: [],
      steps: [],
    },
  ];

  return (
    <div>
      {/* Security banner */}
      <div className="flex items-center gap-2.5 mb-6 px-1">
        <Shield className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <p className="text-xs text-gray-400">
          All credentials are encrypted with AES-128 before storage. Private keys are never exposed in responses.
        </p>
      </div>

      <div className="space-y-3">
        {services.map((svc) => {
          const isExpanded = expanded === svc.key;
          const isApiKeyService = svc.fields.length > 0;
          const isExpandable = isApiKeyService || svc.key === 'snaptrade';

          return (
            <div
              key={svc.key}
              className={`rounded-2xl bg-white border transition-all duration-200 overflow-hidden ${
                isExpanded ? 'border-gray-200 shadow-[0_3px_12px_rgba(0,0,0,0.06)]' : 'border-gray-100 shadow-[0_1px_3px_rgba(0,0,0,0.03)]'
              }`}
            >
              {/* Header row */}
              <button
                onClick={() => isExpandable && toggle(svc.key)}
                className={`w-full flex items-center gap-4 p-4 text-left transition-colors ${
                  isExpandable ? 'hover:bg-gray-50/50 cursor-pointer' : 'cursor-default'
                }`}
              >
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${svc.iconBg}`}>
                  {svc.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2.5">
                    <span className="text-[15px] font-semibold text-gray-900">{svc.name}</span>
                    {loading ? (
                      <span className="w-2 h-2 rounded-full bg-gray-200 animate-pulse" />
                    ) : svc.connected ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                        <Check className="w-3 h-3" />
                        Connected
                      </span>
                    ) : null}
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5 truncate">
                    {!loading && svc.connected && svc.masked ? svc.masked : svc.description}
                  </p>
                </div>
                {isExpandable && (
                  <div className="flex-shrink-0 text-gray-300">
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </div>
                )}
              </button>

              {/* SnapTrade expanded panel */}
              {isExpanded && svc.key === 'snaptrade' && (
                <div className="px-4 pb-4 pt-0">
                  <div className="border-t border-gray-100 pt-4">
                    {feedback && (
                      <div className={`mb-4 px-3 py-2.5 rounded-xl text-sm font-medium ${
                        feedback.type === 'success'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                          : 'bg-red-50 text-red-600 border border-red-100'
                      }`}>
                        {feedback.message}
                      </div>
                    )}
                    <p className="text-sm text-gray-500 mb-4">
                      {svc.connected
                        ? 'Your brokerage is connected. You can reconnect or add another account.'
                        : 'Link your brokerage account securely through SnapTrade. You\'ll be redirected to authorize the connection.'}
                    </p>
                    <button
                      onClick={handleSnaptradeConnect}
                      disabled={connecting}
                      className="w-full py-2.5 text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {connecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wallet className="w-4 h-4" />}
                      {connecting ? 'Connecting...' : svc.connected ? 'Add another account' : 'Connect brokerage'}
                    </button>
                  </div>
                </div>
              )}

              {/* API key expanded panel */}
              {isExpanded && isApiKeyService && (
                <div className="px-4 pb-4 pt-0">
                  <div className="border-t border-gray-100 pt-4">
                    {/* Feedback */}
                    {feedback && (
                      <div className={`mb-4 px-3 py-2.5 rounded-xl text-sm font-medium ${
                        feedback.type === 'success'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                          : 'bg-red-50 text-red-600 border border-red-100'
                      }`}>
                        {feedback.message}
                      </div>
                    )}

                    {/* Connected state: show status + actions */}
                    {svc.connected && !Object.values(formData).some(v => v?.trim()) && (
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => handleTest(svc.key)}
                            disabled={testing}
                            className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                          >
                            {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Test connection'}
                          </button>
                          {confirmDelete === svc.key ? (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-red-500">Remove credentials?</span>
                              <button
                                onClick={() => handleDelete(svc.key)}
                                className="px-2 py-1 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                              >
                                Yes, delete
                              </button>
                              <button
                                onClick={() => setConfirmDelete(null)}
                                className="px-2 py-1 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setConfirmDelete(svc.key)}
                              className="p-1.5 text-gray-300 hover:text-red-400 rounded-lg transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Form fields */}
                    <div className="space-y-3">
                      {svc.fields.map((field) => (
                        <div key={field.key}>
                          <label className="block text-xs font-medium text-gray-500 mb-1.5">{field.label}</label>
                          {field.type === 'textarea' ? (
                            <textarea
                              value={formData[field.key] || ''}
                              onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                              placeholder={field.placeholder}
                              rows={5}
                              className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm font-mono placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all resize-none"
                            />
                          ) : (
                            <div className="relative">
                              <input
                                type={field.key.includes('private_key') && !showKey[field.key] ? 'password' : 'text'}
                                value={formData[field.key] || ''}
                                onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                                placeholder={field.placeholder}
                                className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all pr-10"
                              />
                              {field.key.includes('private_key') && (
                                <button
                                  type="button"
                                  onClick={() => setShowKey({ ...showKey, [field.key]: !showKey[field.key] })}
                                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500 transition-colors"
                                >
                                  {showKey[field.key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Help link + steps */}
                    {(svc.helpUrl || svc.steps.length > 0) && (
                      <div className="mt-4 p-3 bg-gray-50/70 rounded-xl">
                        {svc.helpUrl && (
                          <a
                            href={svc.helpUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-900 hover:text-gray-600 transition-colors mb-2"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            {svc.helpLabel}
                          </a>
                        )}
                        <ol className="text-xs text-gray-400 space-y-1">
                          {svc.steps.map((step, i) => (
                            <li key={i} className="flex gap-2">
                              <span className="text-gray-300 font-medium">{i + 1}.</span>
                              {step}
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2.5 mt-4">
                      <button
                        onClick={() => handleTest(svc.key)}
                        disabled={testing || saving}
                        className="flex-1 py-2.5 text-sm font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                      >
                        {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                        {testing ? 'Testing...' : 'Test'}
                      </button>
                      <button
                        onClick={() => handleSave(svc.key)}
                        disabled={testing || saving || !svc.fields.some(f => formData[f.key]?.trim())}
                        className="flex-1 py-2.5 text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-xl transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                      >
                        {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                        {saving ? 'Saving...' : svc.connected ? 'Update credentials' : 'Save & connect'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Create Bot Modal
// ─────────────────────────────────────────────────────────────────────────────

type PlatformChoice = 'research' | 'kalshi' | 'alpaca' | null;

const PLATFORMS: { key: Exclude<PlatformChoice, null>; label: string; description: string; icon: React.ReactNode; available: boolean }[] = [
  {
    key: 'research',
    label: 'Research',
    description: 'Portfolio advisor',
    icon: <Search className="w-5 h-5" />,
    available: true,
  },
  {
    key: 'kalshi',
    label: 'Kalshi',
    description: 'Prediction markets',
    icon: <TrendingUp className="w-5 h-5" />,
    available: true,
  },
  {
    key: 'alpaca',
    label: 'Brokerage',
    description: 'Stocks & ETFs',
    icon: <BarChart3 className="w-5 h-5" />,
    available: false,
  },
];

function CreateBotModal({
  creating,
  onClose,
  onCreate,
}: {
  creating: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; platform: string; capital_amount?: number }) => void;
}) {
  const [name, setName] = useState('');
  const [platform, setPlatform] = useState<PlatformChoice>(null);
  const [capital, setCapital] = useState('');

  const handleSubmit = () => {
    if (!platform) return;
    const trimmedName = name.trim() || 'New Bot';
    const capitalAmount = parseFloat(capital);
    onCreate({
      name: trimmedName,
      platform,
      ...(capitalAmount > 0 ? { capital_amount: capitalAmount } : {}),
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-1">
          <h2 className="text-lg font-bold text-gray-900">New Bot</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-6 pb-6 pt-4 space-y-5">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Election Tracker"
              autoFocus
              className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !creating) handleSubmit();
              }}
            />
          </div>

          {/* Bot Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Type
            </label>
            <div className="grid grid-cols-3 gap-2">
              {PLATFORMS.map((p) => {
                const selected = platform === p.key;
                return (
                  <button
                    key={p.key}
                    onClick={() => {
                      if (!p.available) return;
                      setPlatform(p.key);
                    }}
                    disabled={!p.available}
                    className={`relative flex flex-col items-center gap-1.5 p-3.5 rounded-xl border-2 transition-all text-center ${
                      selected
                        ? 'border-gray-900 bg-gray-50'
                        : p.available
                          ? 'border-gray-100 hover:border-gray-200 bg-white'
                          : 'border-gray-100 bg-gray-50/50 opacity-50 cursor-not-allowed'
                    }`}
                  >
                    <div className={`${selected ? 'text-gray-900' : 'text-gray-400'} transition-colors`}>
                      {p.icon}
                    </div>
                    <span className={`text-xs font-semibold ${selected ? 'text-gray-900' : 'text-gray-500'}`}>
                      {p.label}
                    </span>
                    <span className="text-[10px] text-gray-400 leading-tight">{p.description}</span>
                    {!p.available && (
                      <span className="absolute -top-1.5 -right-1.5 text-[9px] font-bold text-white bg-gray-400 px-1.5 py-0.5 rounded-full">
                        Soon
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Capital — only for trading platforms */}
          {platform && platform !== 'research' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Starting Capital</label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-gray-400">$</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={capital}
                  onChange={(e) => setCapital(e.target.value)}
                  placeholder="0.00"
                  className="w-full pl-7 pr-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all tabular-nums"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !creating) handleSubmit();
                  }}
                />
              </div>
              <p className="text-[11px] text-gray-400 mt-1.5">You can add more later</p>
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={creating || !platform}
            className="w-full py-2.5 text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {creating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Bot'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Portfolio Tab — account cards → drill into holdings
// ─────────────────────────────────────────────────────────────────────────────

interface AccountInfo {
  id: string;
  name: string;
  number: string;
  institution: string;
  type: string;
  balance: number;
}

function PortfolioTab({ userId }: { userId: string }) {
  const [accounts, setAccounts] = useState<AccountInfo[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [totalGainLoss, setTotalGainLoss] = useState(0);
  const [totalGainLossPct, setTotalGainLossPct] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null); // null = "All" overview

  useEffect(() => {
    (async () => {
      try {
        const [acctRes, portfolio, performance] = await Promise.all([
          snaptradeApi.getAccounts(userId),
          snaptradeApi.getPortfolio(userId),
          snaptradeApi.getPortfolioPerformance(userId).catch(() => null),
        ]);
        if (acctRes.success) {
          setAccounts(acctRes.accounts.map((a: any) => ({
            id: a.id || a.account_id,
            name: a.name,
            number: a.number || '',
            institution: a.institution || a.broker_name || '',
            type: a.type || '',
            balance: a.balance || 0,
          })));
        }
        if (portfolio.success) {
          setTotalValue(portfolio.total_value || 0);
        }
        if (performance?.success) {
          setTotalGainLoss(performance.total_gain_loss || 0);
          setTotalGainLossPct(performance.total_gain_loss_percent || 0);
        }
      } catch (e) {
        console.error('Failed to load portfolio accounts:', e);
      } finally {
        setLoading(false);
      }
    })();
  }, [userId]);

  const fmt = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
  const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;

  // Drill-down: show the holdings panel for a specific account or all
  if (selectedAccount !== null) {
    const acct = accounts.find(a => a.id === selectedAccount);
    return (
      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden" style={{ height: 'calc(100vh - 200px)' }}>
        <BotVisualizationsPanel
          onBack={() => setSelectedAccount(null)}
          accountId={selectedAccount === 'all' ? undefined : selectedAccount}
          accountName={selectedAccount === 'all' ? 'All Accounts' : acct?.name}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="text-center py-16">
        <Briefcase className="w-10 h-10 text-gray-200 mx-auto mb-3" />
        <p className="text-sm text-gray-400 mb-1">No accounts connected</p>
        <p className="text-xs text-gray-400">Go to Connections to link your brokerage</p>
      </div>
    );
  }

  const accountTypeLabel = (type: string) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  return (
    <div>
      {/* All Accounts overview card */}
      <button
        onClick={() => setSelectedAccount('all')}
        className="w-full text-left mb-4 p-5 rounded-xl border border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm transition-all group"
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">All Accounts</div>
            <div className="text-2xl font-bold text-gray-900 tabular-nums">{fmt(totalValue)}</div>
            {totalGainLoss !== 0 && (
              <div className={`text-sm font-medium tabular-nums mt-0.5 ${totalGainLoss >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                {totalGainLoss >= 0 ? '+' : ''}{fmt(totalGainLoss)} ({fmtPct(totalGainLossPct)})
              </div>
            )}
          </div>
          <div className="p-2 rounded-lg bg-gray-50 group-hover:bg-gray-100 transition-colors">
            <TrendingUp className="w-5 h-5 text-gray-400" />
          </div>
        </div>
        <div className="text-xs text-gray-400 mt-2">{accounts.length} account{accounts.length !== 1 ? 's' : ''} connected</div>
      </button>

      {/* Individual account cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {accounts.map(acct => (
          <button
            key={acct.id}
            onClick={() => setSelectedAccount(acct.id)}
            className="text-left p-4 rounded-xl border border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm transition-all group"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
                <Wallet className="w-4 h-4 text-gray-500" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold text-gray-900 truncate">{acct.name}</div>
                <div className="text-[11px] text-gray-400">{acct.institution} · {accountTypeLabel(acct.type)}</div>
              </div>
            </div>
            <div className="text-lg font-bold text-gray-900 tabular-nums">{fmt(acct.balance)}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
