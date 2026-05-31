'use client';

import React, { useState } from 'react';
import { Search, Sparkles, SlidersHorizontal, ArrowUpDown } from 'lucide-react';
import { screenerApi, type ScreenSpec, type ScreenRow } from '@/lib/api';
import { useNavigation } from '@/contexts/NavigationContext';
import TickerLogo from '@/components/ui/TickerLogo';
import EmptyState from '@/components/ui/EmptyState';

const SECTORS = [
  'Technology', 'Healthcare', 'Financial Services', 'Consumer Cyclical',
  'Consumer Defensive', 'Energy', 'Industrials', 'Basic Materials',
  'Real Estate', 'Utilities', 'Communication Services',
];

// Market-cap presets → (min, max) in USD.
const CAP_PRESETS: { label: string; min?: number; max?: number }[] = [
  { label: 'Any cap' },
  { label: 'Mega ($200B+)', min: 200_000_000_000 },
  { label: 'Large ($10B+)', min: 10_000_000_000 },
  { label: 'Mid ($2–10B)', min: 2_000_000_000, max: 10_000_000_000 },
  { label: 'Small (<$2B)', max: 2_000_000_000 },
];

const DEFAULT_SPEC: ScreenSpec = {
  filters: { country: 'US', isActivelyTrading: true },
  sortBy: 'marketCap',
  sortDir: 'desc',
  limit: 25,
};

function fmtCap(n?: number): string {
  if (!n) return '—';
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
  return `$${n}`;
}
function fmtVol(n?: number): string {
  if (!n) return '—';
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return String(n);
}

export default function ScreenerPanel() {
  const { openStock } = useNavigation();
  const [spec, setSpec] = useState<ScreenSpec>(DEFAULT_SPEC);
  const [results, setResults] = useState<ScreenRow[] | null>(null);
  const [rationale, setRationale] = useState<string | null>(null);
  const [aiPrompt, setAiPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setFilter = (patch: Partial<ScreenSpec['filters']>) =>
    setSpec(s => ({ ...s, filters: { ...s.filters, ...patch } }));

  const runSpec = async (next: ScreenSpec) => {
    setLoading(true); setError(null);
    try {
      const res = await screenerApi.run(next);
      setResults(res.results);
    } catch (e: any) {
      setError(e?.message || 'Screen failed'); setResults([]);
    } finally { setLoading(false); }
  };

  const runAi = async () => {
    if (!aiPrompt.trim()) return;
    setLoading(true); setError(null); setRationale(null);
    try {
      const res = await screenerApi.ai(aiPrompt.trim());
      // Merge the AI-authored filters onto our defaults so controls reflect them.
      const merged: ScreenSpec = {
        ...DEFAULT_SPEC,
        ...res.spec,
        filters: { ...DEFAULT_SPEC.filters, ...(res.spec?.filters || {}) },
      };
      setSpec(merged);
      setResults(res.results);
      setRationale(res.rationale || null);
    } catch (e: any) {
      setError(e?.message || 'AI screen failed'); setResults([]);
    } finally { setLoading(false); }
  };

  const activeCapLabel = (() => {
    const { marketCapMoreThan: lo, marketCapLowerThan: hi } = spec.filters;
    return CAP_PRESETS.find(p => p.min === (lo ?? undefined) && p.max === (hi ?? undefined))?.label
      ?? (lo || hi ? 'Custom' : 'Any cap');
  })();

  return (
    <div className="flex flex-col h-full bg-white overflow-y-auto">
      <div className="max-w-5xl w-full mx-auto px-4 sm:px-6 py-5">
        {/* Header */}
        <div className="flex items-center gap-2.5 mb-4">
          <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600">
            <SlidersHorizontal className="w-5 h-5" strokeWidth={2} />
          </span>
          <div>
            <h1 className="text-lg font-bold text-gray-900 leading-tight">Screener</h1>
            <p className="text-xs text-gray-400">Describe what you want, or set filters by hand.</p>
          </div>
        </div>

        {/* AI prompt */}
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm focus-within:border-emerald-300 transition-colors mb-3">
          <div className="flex items-center gap-2 px-4 py-3">
            <Sparkles className="w-4 h-4 text-emerald-500 flex-shrink-0" />
            <input
              value={aiPrompt}
              onChange={e => setAiPrompt(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') runAi(); }}
              placeholder="e.g. profitable large-cap healthcare dividend payers with low volatility"
              className="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-400 focus:outline-none"
            />
            <button
              onClick={runAi}
              disabled={loading || !aiPrompt.trim()}
              className="px-3.5 py-1.5 rounded-full bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 transition-colors disabled:opacity-50"
            >
              {loading ? '…' : 'Screen'}
            </button>
          </div>
        </div>

        {/* Manual filters */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <select
            value={spec.filters.sector || ''}
            onChange={e => setFilter({ sector: e.target.value || null })}
            className="text-sm rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-gray-700 focus:outline-none focus:border-emerald-400"
          >
            <option value="">Any sector</option>
            {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          <select
            value={activeCapLabel}
            onChange={e => {
              const p = CAP_PRESETS.find(x => x.label === e.target.value);
              setFilter({ marketCapMoreThan: p?.min ?? null, marketCapLowerThan: p?.max ?? null });
            }}
            className="text-sm rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-gray-700 focus:outline-none focus:border-emerald-400"
          >
            {CAP_PRESETS.map(p => <option key={p.label} value={p.label}>{p.label}</option>)}
            {activeCapLabel === 'Custom' && <option value="Custom">Custom</option>}
          </select>

          <NumInput label="Max price $" value={spec.filters.priceLowerThan} onChange={v => setFilter({ priceLowerThan: v })} />
          <NumInput label="Max beta" value={spec.filters.betaLowerThan} step={0.1} onChange={v => setFilter({ betaLowerThan: v })} />
          <NumInput label="Min div $" value={spec.filters.dividendMoreThan} step={0.1} onChange={v => setFilter({ dividendMoreThan: v })} />

          <button
            onClick={() => { setSpec(DEFAULT_SPEC); setResults(null); setRationale(null); }}
            className="text-sm text-gray-400 hover:text-gray-600 px-2 py-1.5"
          >
            Reset
          </button>
          <button
            onClick={() => runSpec(spec)}
            disabled={loading}
            className="ml-auto inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-gray-900 text-white text-sm font-semibold hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            <Search className="w-3.5 h-3.5" /> Run screen
          </button>
        </div>

        {rationale && (
          <div className="mb-3 flex items-start gap-2 text-sm text-gray-600 bg-emerald-50/60 border border-emerald-100 rounded-xl px-3.5 py-2.5">
            <Sparkles className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
            <span>{rationale}</span>
          </div>
        )}
        {error && <div className="mb-3 text-sm text-red-500">{error}</div>}

        {/* Results */}
        {results === null ? (
          <EmptyState
            icon={SlidersHorizontal}
            title="Build your first screen"
            description="Describe what you're looking for above, or set a sector, market cap, and filters — then Run."
            className="py-20"
          />
        ) : results.length === 0 && !loading ? (
          <EmptyState
            icon={Search}
            title="No matches"
            description="Nothing fit those filters. Loosen the criteria and try again."
            className="py-16"
          />
        ) : (
          <div className="rounded-2xl border border-gray-200 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100 bg-gray-50/60">
              <span className="text-xs font-semibold text-gray-500">{results.length} matches</span>
              <button
                onClick={() => { const sd = spec.sortDir === 'desc' ? 'asc' : 'desc'; const next = { ...spec, sortDir: sd as 'asc' | 'desc' }; setSpec(next); runSpec(next); }}
                className="inline-flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-800"
              >
                <ArrowUpDown className="w-3 h-3" /> {spec.sortBy} · {spec.sortDir}
              </button>
            </div>
            <div className="divide-y divide-gray-100">
              {results.map(r => (
                <button
                  key={r.symbol}
                  onClick={() => openStock(r.symbol)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                >
                  <TickerLogo symbol={r.symbol} size={34} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-900">{r.symbol}</span>
                      {r.sector && <span className="text-[11px] text-gray-400 truncate">{r.sector}</span>}
                    </div>
                    <div className="text-xs text-gray-500 truncate">{r.companyName}</div>
                  </div>
                  <div className="hidden sm:grid grid-cols-4 gap-4 text-right text-xs flex-shrink-0">
                    <Stat label="Price" value={r.price != null ? `$${r.price.toFixed(2)}` : '—'} />
                    <Stat label="Mkt cap" value={fmtCap(r.marketCap)} />
                    <Stat label="Beta" value={r.beta != null ? r.beta.toFixed(2) : '—'} />
                    <Stat label="Div" value={r.lastAnnualDividend ? `$${r.lastAnnualDividend.toFixed(2)}` : '—'} />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function NumInput({ label, value, step, onChange }: { label: string; value?: number | null; step?: number; onChange: (v: number | null) => void }) {
  return (
    <label className="inline-flex items-center gap-1.5 text-sm rounded-lg border border-gray-200 bg-white px-3 py-1.5 focus-within:border-emerald-400">
      <span className="text-gray-400 text-xs whitespace-nowrap">{label}</span>
      <input
        type="number"
        step={step || 1}
        value={value ?? ''}
        onChange={e => onChange(e.target.value === '' ? null : Number(e.target.value))}
        className="w-16 bg-transparent text-gray-900 font-numeric text-sm focus:outline-none"
        placeholder="—"
      />
    </label>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="w-16">
      <div className="text-[10px] uppercase tracking-wide text-gray-400">{label}</div>
      <div className="font-numeric text-gray-900">{value}</div>
    </div>
  );
}
