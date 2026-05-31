'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Sparkles, Wallet, Activity, PieChart, Coins, Layers, RefreshCw } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { snaptradeApi, alpacaBrokerApi, analyticsApi, type AnalyticsView } from '@/lib/api';
import TickerLogo from '@/components/ui/TickerLogo';
import EmptyState from '@/components/ui/EmptyState';

const SECTOR_COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16', '#6366f1', '#94a3b8'];

function fmtMoney(n: number): string {
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}
const pct = (x: number) => `${(x * 100).toFixed(0)}%`;

export default function AnalyticsPanel() {
  const { user } = useAuth();
  const { openStock, navigateTo } = useNavigation();
  const [view, setView] = useState<AnalyticsView | null>(null);
  const [loading, setLoading] = useState(true);
  const [noHoldings, setNoHoldings] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true); setError(null); setNoHoldings(false);
    try {
      // Pull holdings from both connected sources.
      const [ext, alp] = await Promise.all([
        snaptradeApi.getPortfolio(user.id).catch(() => null),
        alpacaBrokerApi.getPortfolio(user.id).catch(() => null),
      ]);
      const holdings: { symbol: string; value: number }[] = [];
      ext?.accounts?.forEach(a => a.positions?.forEach(p => {
        if (p.symbol && p.value) holdings.push({ symbol: p.symbol, value: p.value });
      }));
      (alp as any)?.positions?.forEach((p: any) => {
        const v = parseFloat(p.market_value || '0');
        if (p.symbol && v) holdings.push({ symbol: p.symbol, value: v });
      });
      if (holdings.length === 0) { setNoHoldings(true); setView(null); return; }
      const v = await analyticsApi.analyzePortfolio(holdings);
      setView(v);
    } catch (e: any) {
      setError(e?.message || 'Could not analyze portfolio');
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center gap-3">
        <RefreshCw className="w-6 h-6 text-emerald-500 animate-spin" />
        <p className="text-sm text-gray-400">Analyzing your portfolio…</p>
      </div>
    );
  }

  if (noHoldings) {
    return (
      <div className="flex flex-col h-full bg-white">
        <EmptyState
          icon={Wallet}
          title="Connect your portfolio"
          description="Link a brokerage and Finch will break down your allocation, risk, concentration, and dividend income — with an AI read on what it all means."
          action={{ label: 'Go to Dashboard', onClick: () => navigateTo({ type: 'home' }) }}
          className="h-full"
        />
      </div>
    );
  }

  if (error || !view) {
    return (
      <div className="flex flex-col h-full bg-white">
        <EmptyState icon={Activity} title="Couldn't analyze" description={error || 'Try again in a moment.'}
          action={{ label: 'Retry', onClick: load }} className="h-full" />
      </div>
    );
  }

  const beta = view.weighted_beta;
  const betaTone = beta == null ? 'text-gray-900' : beta > 1.15 ? 'text-red-500' : beta < 0.9 ? 'text-emerald-600' : 'text-gray-900';

  return (
    <div className="flex flex-col h-full bg-white overflow-y-auto">
      <div className="max-w-5xl w-full mx-auto px-4 sm:px-6 py-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600">
              <PieChart className="w-5 h-5" strokeWidth={2} />
            </span>
            <div>
              <h1 className="text-lg font-bold text-gray-900 leading-tight">Portfolio Analytics</h1>
              <p className="text-xs text-gray-400">{view.holding_count} holdings · {fmtMoney(view.total_value)}</p>
            </div>
          </div>
          <button onClick={load} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {/* AI narration */}
        {view.narration && (
          <div className="flex items-start gap-2.5 text-sm text-gray-700 leading-relaxed bg-emerald-50/60 border border-emerald-100 rounded-2xl px-4 py-3.5 mb-4">
            <Sparkles className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
            <ReactMarkdownNarration text={view.narration} />
          </div>
        )}

        {/* Metric cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
          <Metric icon={Activity} label="Portfolio beta" value={beta != null ? beta.toFixed(2) : '—'} tone={betaTone}
            hint={beta == null ? '' : beta > 1 ? 'more volatile than market' : 'less volatile than market'} />
          <Metric icon={Layers} label="Top-5 concentration" value={pct(view.top5_concentration)}
            tone={view.top5_concentration > 0.7 ? 'text-red-500' : 'text-gray-900'}
            hint={`largest ${pct(view.largest_position_weight)}`} />
          <Metric icon={Coins} label="Dividend income" value={fmtMoney(view.annual_dividend_income)} tone="text-gray-900"
            hint={`${pct(view.dividend_yield)} yield / yr`} />
          <Metric icon={PieChart} label="Sectors" value={String(view.sector_allocation.length)} tone="text-gray-900"
            hint={view.sector_allocation[0] ? `${view.sector_allocation[0].label} ${pct(view.sector_allocation[0].weight)}` : ''} />
        </div>

        {/* Allocation + holdings */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Sector allocation bar */}
          <div className="rounded-2xl border border-gray-200 p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-3">Sector allocation</h3>
            <div className="flex h-2.5 rounded-full overflow-hidden mb-3">
              {view.sector_allocation.map((a, i) => (
                <div key={a.label} style={{ width: `${a.weight * 100}%`, background: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
              ))}
            </div>
            <div className="space-y-1.5">
              {view.sector_allocation.map((a, i) => (
                <div key={a.label} className="flex items-center gap-2 text-sm">
                  <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                  <span className="text-gray-700 flex-1 truncate">{a.label}</span>
                  <span className="font-numeric text-gray-500">{fmtMoney(a.value)}</span>
                  <span className="font-numeric font-semibold text-gray-900 w-10 text-right">{pct(a.weight)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Top holdings */}
          <div className="rounded-2xl border border-gray-200 p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-3">Top holdings</h3>
            <div className="space-y-1">
              {view.top_holdings.map(h => (
                <button key={h.symbol} onClick={() => openStock(h.symbol)}
                  className="w-full flex items-center gap-3 py-1.5 text-left hover:bg-gray-50 rounded-lg px-1.5 -mx-1.5 transition-colors">
                  <TickerLogo symbol={h.symbol} size={28} />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-bold text-gray-900">{h.symbol}</div>
                    {h.sector && <div className="text-[11px] text-gray-400 truncate">{h.sector}</div>}
                  </div>
                  <div className="text-right">
                    <div className="font-numeric text-sm font-semibold text-gray-900">{pct(h.weight)}</div>
                    <div className="font-numeric text-[11px] text-gray-400">{fmtMoney(h.value)}</div>
                  </div>
                  {/* weight bar */}
                  <div className="w-14 h-1.5 rounded-full bg-gray-100 overflow-hidden hidden sm:block">
                    <div className="h-full bg-emerald-500" style={{ width: `${Math.min(h.weight * 100, 100)}%` }} />
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Metric({ icon: Icon, label, value, hint, tone }: { icon: React.ElementType; label: string; value: string; hint?: string; tone?: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 p-3.5">
      <div className="flex items-center gap-1.5 text-gray-400 mb-1.5">
        <Icon className="w-3.5 h-3.5" />
        <span className="text-[11px] font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className={`text-2xl font-bold font-numeric ${tone || 'text-gray-900'}`}>{value}</div>
      {hint && <div className="text-[11px] text-gray-400 mt-0.5">{hint}</div>}
    </div>
  );
}

// Lightweight bold-aware renderer for the narration (handles **bold**).
function ReactMarkdownNarration({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <span>
      {parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**')
          ? <strong key={i} className="font-semibold text-gray-900">{p.slice(2, -2)}</strong>
          : <span key={i}>{p}</span>
      )}
    </span>
  );
}
