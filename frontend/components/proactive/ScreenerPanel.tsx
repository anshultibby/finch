'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Sparkles, ArrowUp, Eye, Loader2 } from 'lucide-react';
import { useNavigation } from '@/contexts/NavigationContext';
import { marketApi, jobsApi, type ScreenerFilters, type ScreenerResult } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';
import TickerLogo from '@/components/ui/TickerLogo';
import { fmtUsd, nextRunAt, ui } from './shared';

// Two ways in: say it in plain English (Finch runs the screen in chat, shows
// the filters it used, ranks and explains), or tap exact filters. Either way a
// screen can become a watcher that only pings on NEW matches.
// Mirrors frontend-mobile/app/screener.tsx.

type Cap = 'small' | 'mid' | 'large' | 'mega';
type Draft = { sector?: string; cap?: Cap; beta?: 'low' | 'high'; dividend?: boolean };

const SECTORS = [
  'Technology', 'Healthcare', 'Financial Services', 'Consumer Cyclical', 'Industrials',
  'Communication Services', 'Consumer Defensive', 'Energy', 'Utilities', 'Real Estate', 'Basic Materials',
];
const CAPS: { key: Cap; label: string; min?: number; max?: number }[] = [
  { key: 'small', label: 'Small', min: 300e6, max: 2e9 },
  { key: 'mid', label: 'Mid', min: 2e9, max: 10e9 },
  { key: 'large', label: 'Large', min: 10e9, max: 200e9 },
  { key: 'mega', label: 'Mega', min: 200e9 },
];
const PRESETS: { label: string; draft: Draft }[] = [
  { label: 'Mega-cap leaders', draft: { cap: 'mega' } },
  { label: 'Dividend payers', draft: { cap: 'large', dividend: true } },
  { label: 'Steady compounders', draft: { cap: 'large', beta: 'low' } },
  { label: 'High-beta movers', draft: { cap: 'mid', beta: 'high' } },
  { label: 'Small-cap tech', draft: { sector: 'Technology', cap: 'small' } },
  { label: 'Healthcare mid-caps', draft: { sector: 'Healthcare', cap: 'mid' } },
];
const NL_EXAMPLES = [
  'Profitable software companies growing revenue 20%+',
  'Beaten-down large caps with strong balance sheets',
  'Dividend stocks yielding 3%+ that raised the payout 5 years running',
];

function toFilters(d: Draft): ScreenerFilters {
  const cap = CAPS.find(c => c.key === d.cap);
  return {
    sector: d.sector,
    market_cap_min: cap?.min ?? 300e6,
    market_cap_max: cap?.max,
    beta_max: d.beta === 'low' ? 0.8 : undefined,
    beta_min: d.beta === 'high' ? 1.5 : undefined,
    dividend_min: d.dividend ? 0.5 : undefined,
    volume_min: 100_000,
  };
}

function describe(d: Draft): string {
  const parts: string[] = [];
  if (d.cap) parts.push(`${CAPS.find(c => c.key === d.cap)?.label.toLowerCase()}-cap`);
  if (d.sector) parts.push(d.sector);
  parts.push('US stocks');
  if (d.beta === 'low') parts.push('with beta under 0.8');
  if (d.beta === 'high') parts.push('with beta over 1.5');
  if (d.dividend) parts.push('that pay a dividend');
  return parts.join(' ');
}

function Chip({ label, on, onClick }: { label: string; on?: boolean; onClick: () => void }) {
  return <button onClick={onClick} className={`${ui.chip} ${on ? ui.chipOn : ui.chipOff}`}>{label}</button>;
}

export default function ScreenerPanel() {
  const { openStock, openChatWithPrompt } = useNavigation();
  const [query, setQuery] = useState('');
  const [draft, setDraft] = useState<Draft>(PRESETS[0].draft);
  const [results, setResults] = useState<ScreenerResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [watchState, setWatchState] = useState<'idle' | 'busy' | 'done' | string>('idle');

  const filters = useMemo(() => toFilters(draft), [draft]);

  const run = useCallback(async () => {
    setLoading(true);
    setError(false);
    try { setResults(await marketApi.screen(filters, 40)); }
    catch { setError(true); setResults([]); }
    finally { setLoading(false); }
  }, [filters]);

  useEffect(() => { run(); setWatchState('idle'); }, [run]);

  const askFinch = (q: string) => {
    const text = q.trim();
    if (!text) return;
    openChatWithPrompt(
      `Screen the market for: ${text}\n\nUse the stock screener and fundamentals. Show the exact filters you applied, then a ranked table of the top 10 with one line on why each made the cut. Flag anything that barely qualifies. End by offering to watch this screen and ping me only when new names qualify.`,
      `Screen: ${text}`,
    );
  };

  const watchScreen = async () => {
    setWatchState('busy');
    try {
      const label = describe(draft);
      await jobsApi.create({
        name: `Watch screen: ${label}`,
        message: `Run this stock screen: ${label} (US-listed, average volume over 100k). Compare against the names you reported last time and tell me ONLY about new names that now qualify, with one line on why each is interesting. If nothing new qualifies, say so in one sentence and don't notify me.`,
        run_at: nextRunAt(9),
        recurrence: 'weekdays',
      });
      setWatchState('done');
    } catch (e: any) {
      setWatchState(e?.response?.data?.detail || "Couldn't set that up — you may be at your plan's automation limit.");
    }
  };

  const sameDraft = (d: Draft) => JSON.stringify(d) === JSON.stringify(draft);

  return (
    <div className="h-full overflow-y-auto bg-[#fafaf9]">
      <div className={ui.page}>
        <PageHeader title="Screener" subtitle="Describe it, or set exact filters" />

        {/* Plain-English → Finch */}
        <div className="bg-white border border-emerald-100 rounded-2xl p-3">
          <div className="flex items-center gap-2 pl-2">
            <Sparkles className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && askFinch(query)}
              placeholder="Describe the stocks you want…" className="flex-1 bg-transparent text-[15px] py-2 focus:outline-none" />
            <button onClick={() => askFinch(query)} disabled={!query.trim()} aria-label="Ask Finch to screen"
              className={`w-8 h-8 rounded-full flex items-center justify-center ${query.trim() ? 'bg-emerald-600 text-white' : 'bg-stone-200 text-white'}`}>
              <ArrowUp className="w-4 h-4" strokeWidth={2.6} />
            </button>
          </div>
          <div className="mt-1">
            {NL_EXAMPLES.map(ex => (
              <button key={ex} onClick={() => askFinch(ex)} className="block w-full text-left px-2 py-1.5 text-[13px] text-stone-500 hover:text-stone-800 truncate">
                “{ex}”
              </button>
            ))}
          </div>
        </div>

        <div className={ui.section}>Start from</div>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map(p => <Chip key={p.label} label={p.label} on={sameDraft(p.draft)} onClick={() => setDraft(p.draft)} />)}
        </div>

        <div className={ui.section}>Filters</div>
        <div className={`${ui.card} p-4 space-y-3`}>
          <FilterRow label="Size">
            <Chip label="Any" on={!draft.cap} onClick={() => setDraft(d => ({ ...d, cap: undefined }))} />
            {CAPS.map(c => <Chip key={c.key} label={c.label} on={draft.cap === c.key} onClick={() => setDraft(d => ({ ...d, cap: c.key }))} />)}
          </FilterRow>
          <FilterRow label="Volatility">
            <Chip label="Any" on={!draft.beta} onClick={() => setDraft(d => ({ ...d, beta: undefined }))} />
            <Chip label="Steady (β<0.8)" on={draft.beta === 'low'} onClick={() => setDraft(d => ({ ...d, beta: 'low' }))} />
            <Chip label="Jumpy (β>1.5)" on={draft.beta === 'high'} onClick={() => setDraft(d => ({ ...d, beta: 'high' }))} />
          </FilterRow>
          <FilterRow label="Income">
            <Chip label="Any" on={!draft.dividend} onClick={() => setDraft(d => ({ ...d, dividend: undefined }))} />
            <Chip label="Pays a dividend" on={!!draft.dividend} onClick={() => setDraft(d => ({ ...d, dividend: true }))} />
          </FilterRow>
          <FilterRow label="Sector">
            <Chip label="All" on={!draft.sector} onClick={() => setDraft(d => ({ ...d, sector: undefined }))} />
            {SECTORS.map(s => <Chip key={s} label={s} on={draft.sector === s} onClick={() => setDraft(d => ({ ...d, sector: s }))} />)}
          </FilterRow>
        </div>

        <div className="flex items-end justify-between">
          <div className={ui.section}>{loading ? 'Screening…' : `${results.length} matches`}</div>
          <button onClick={watchScreen} disabled={watchState === 'busy' || watchState === 'done'}
            className="mb-2 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700 text-[12.5px] font-bold hover:bg-emerald-100 disabled:opacity-70">
            {watchState === 'busy' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
            {watchState === 'done' ? 'Watching — new matches only' : 'Watch this screen'}
          </button>
        </div>
        {watchState !== 'idle' && watchState !== 'busy' && watchState !== 'done' && (
          <div className="mb-2 text-[12.5px] text-red-600">{watchState}</div>
        )}

        {loading ? (
          <div className={`${ui.card} p-4 space-y-3 animate-pulse`}>
            {[0, 1, 2, 3, 4].map(i => <div key={i} className="h-9 bg-stone-100 rounded" />)}
          </div>
        ) : error ? (
          <div className={`${ui.card} p-5 text-[14px] text-stone-600`}>
            Couldn&apos;t run that screen. <button onClick={run} className="text-emerald-700 font-semibold">Retry</button>
          </div>
        ) : results.length === 0 ? (
          <div className={`${ui.card} p-5 text-[14px] text-stone-500`}>Nothing matches. Loosen a filter, or describe what you want above.</div>
        ) : (
          <div className={`${ui.card} overflow-hidden`}>
            {results.map(r => (
              <button key={r.symbol} onClick={() => openStock(r.symbol)} className={ui.row}>
                <TickerLogo symbol={r.symbol} size={30} />
                <div className="flex-1 min-w-0">
                  <div className="text-[14.5px] font-bold text-gray-900">{r.symbol}</div>
                  <div className="text-[12.5px] text-stone-500 truncate">{r.name}{r.industry ? ` · ${r.industry}` : ''}</div>
                </div>
                <div className="text-right">
                  <div className="text-[14.5px] font-medium text-gray-900 tabular-nums">{fmtUsd(r.price)}</div>
                  <div className="text-[12px] text-stone-400 tabular-nums">{fmtUsd(r.market_cap, true)} cap</div>
                </div>
              </button>
            ))}
          </div>
        )}
        <p className="text-[11.5px] text-stone-400 text-center mt-4">Data: Financial Modeling Prep. Filters are exact; Finch&apos;s explanations are AI-generated.</p>
      </div>
    </div>
  );
}

function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[13px] font-bold text-gray-900 mb-1.5">{label}</div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}
