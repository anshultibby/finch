'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Sparkles, SlidersHorizontal, Zap, FileText, CalendarDays, Eye, ChevronRight, ArrowUp } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation, type View } from '@/contexts/NavigationContext';
import {
  activityApi, insightsApi, marketApi, watchlistApi, jobsApi, ideasApi,
  type ActivityRecap, type PortfolioDigest, type ScheduledJob, type TradeIdea, type MoveVerdict,
  VERDICT_META, THESIS_STATUS_META, type ThesisStatus,
} from '@/lib/api';
import { usePendingTrades } from '@/hooks/usePendingTrades';
import { dayDiff, whenLabel, marketStatus, greeting, earningsPreviewPrompt, fmtUsd, fmtPct } from './shared';

// ── Home ─────────────────────────────────────────────────────────────────────
// One page. Finch speaks first (the brief: what changed for *you*, ranked,
// capped at three and hidden when there's nothing worth saying), then six
// cards — one per tool — each with a live line about what Finch did with it.
// Mirrors frontend-mobile/app/(tabs)/index.tsx.

const PULSE = [
  { symbol: 'SPY', label: 'S&P 500' },
  { symbol: 'QQQ', label: 'Nasdaq' },
  { symbol: 'DIA', label: 'Dow' },
];

type BriefItem = { key: string; action?: boolean; verdict?: MoveVerdict; thesis?: ThesisStatus; title: string; body?: string; cta?: string; onClick: () => void };

export default function ProactiveHome() {
  const { user } = useAuth();
  const { navigateTo, openChatWithPrompt, setHomeTab, loadChat, openStock } = useNavigation();
  const { trades: pending } = usePendingTrades(!!user);

  const [loading, setLoading] = useState(true);
  const [recap, setRecap] = useState<ActivityRecap | null>(null);
  const [digest, setDigest] = useState<PortfolioDigest | null>(null);
  const [earnings, setEarnings] = useState<any[]>([]);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [ideas, setIdeas] = useState<TradeIdea[]>([]);
  const [pulse, setPulse] = useState<Record<string, any>>({});
  const [ask, setAsk] = useState('');

  useEffect(() => {
    if (!user) return;
    let alive = true;
    // The digest is LLM-written and slow — it joins the brief when it lands
    // instead of holding the whole brief on a skeleton.
    insightsApi.getPortfolioDigest(user.id).then(d => alive && setDigest(d)).catch(() => {});
    Promise.all([
      marketApi.getEarnings().then(d => alive && setEarnings(Array.isArray(d) ? d : d?.earnings || [])).catch(() => {}),
      marketApi.getBatchQuotes(PULSE.map(p => p.symbol)).then(rows => {
        if (!alive || !Array.isArray(rows)) return;
        const m: Record<string, any> = {};
        rows.forEach((q: any) => { if (q?.symbol) m[q.symbol] = q; });
        setPulse(m);
      }).catch(() => {}),
      activityApi.getRecap().then(r => alive && setRecap(r)).catch(() => {}),
      watchlistApi.getWatchlist(user.id).then(d => {
        const raw = d?.symbols || d?.watchlist || [];
        alive && setWatchlist(raw.map((i: any) => (typeof i === 'string' ? i : i.symbol)).filter(Boolean));
      }).catch(() => {}),
      jobsApi.list().then(d => alive && setJobs(d.jobs || [])).catch(() => {}),
      ideasApi.list(20).then(d => alive && setIdeas(d.ideas || [])).catch(() => {}),
    ]).finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [user]);

  const mySymbols = useMemo(() => {
    const s = new Set<string>(watchlist.map(x => x.toUpperCase()));
    (digest?.movers || []).forEach(m => s.add(m.symbol.toUpperCase()));
    return s;
  }, [watchlist, digest]);

  const myEarnings = useMemo(
    () => earnings
      .filter(e => e?.symbol && mySymbols.has(String(e.symbol).toUpperCase()))
      .filter(e => { const d = dayDiff(e.date); return d >= 0 && d <= 7; })
      .sort((a, b) => String(a.date).localeCompare(String(b.date))),
    [earnings, mySymbols],
  );

  const activeJobs = jobs.filter(j => j.status === 'pending' || j.status === 'running');
  const openIdeas = ideas.filter(i => i.status === 'proposed' && i.outcome === 'pending');

  // ── The brief: ranked, capped at three, never filler ──
  const brief: BriefItem[] = useMemo(() => {
    const items: BriefItem[] = [];
    if (pending.length > 0) {
      items.push({
        key: 'approvals', action: true,
        title: pending.length === 1 ? 'A trade needs your approval' : `${pending.length} trades need your approval`,
        body: pending[0].summary || undefined,
        cta: 'Review',
        onClick: () => navigateTo({ type: 'trader' }),
      });
    }
    // Agent signals that cleared the bar. Routine noise stays in the ledger,
    // and a story change outranks everything but an approval.
    const signals = (recap?.events || [])
      .filter(e => (e.event_type === 'alert' || e.event_type === 'insight') && e.data?.verdict !== 'noise');
    // A thesis the user wrote that's now weakened/broken is the most personal
    // signal there is; then a market-level story change.
    const shift = signals.find(e => e.data?.thesis_status === 'broken' || e.data?.thesis_status === 'weakened')
      || signals.find(e => e.data?.verdict === 'narrative_shift');
    const signal = shift || signals[0];
    const signalItem = signal && {
      key: `evt-${signal.id}`,
      verdict: signal.data?.verdict as MoveVerdict | undefined,
      thesis: (signal.data?.thesis_status || undefined) as ThesisStatus | undefined,
      title: signal.title,
      body: signal.body || undefined,
      onClick: () => (signal.data?.chat_id ? loadChat(String(signal.data.chat_id))
        : signal.data?.symbol ? openStock(String(signal.data.symbol)) : navigateTo({ type: 'trader' })),
    };
    if (signalItem && shift) items.push(signalItem);
    const soon = myEarnings.find(e => dayDiff(e.date) <= 2);
    if (soon) {
      items.push({
        key: `earn-${soon.symbol}`,
        title: `${soon.symbol} reports ${whenLabel(soon.date, soon.time)}`,
        body: 'Want the setup — what the street expects, the implied move, and what it means for you?',
        cta: 'Preview it',
        onClick: () => openChatWithPrompt(earningsPreviewPrompt(soon.symbol), `${soon.symbol} earnings preview`),
      });
    }
    if (signalItem && !shift) items.push(signalItem);
    if (digest?.narrative && digest.mode !== 'empty') {
      items.push({
        key: 'digest',
        title: digest.mode === 'portfolio' ? 'Your book today' : 'Your watchlist today',
        body: digest.narrative,
        onClick: () => (digest.mode === 'portfolio' ? (setHomeTab('portfolio'), navigateTo({ type: 'markets' })) : navigateTo({ type: 'watching' })),
      });
    }
    return items.slice(0, 3);
  }, [pending, myEarnings, recap, digest, navigateTo, openChatWithPrompt, setHomeTab, loadChat, openStock]);

  const cards: { key: string; title: string; line: string; attention?: boolean; Icon: React.ComponentType<{ className?: string }>; tint: string; view: View }[] = [
    {
      key: 'assistant', title: 'Ask Finch', Icon: Sparkles, tint: 'bg-emerald-50 text-emerald-600', view: { type: 'assistant' },
      line: openIdeas.length > 0 ? `${openIdeas.length} idea${openIdeas.length > 1 ? 's' : ''} for you` : 'Research, explain, plan',
      attention: openIdeas.length > 0,
    },
    { key: 'screener', title: 'Screener', Icon: SlidersHorizontal, tint: 'bg-blue-50 text-blue-600', view: { type: 'screener' }, line: 'Describe it, Finch finds it' },
    {
      key: 'trader', title: 'Trader', Icon: Zap, tint: 'bg-amber-50 text-amber-600', view: { type: 'trader' },
      line: pending.length > 0 ? `${pending.length} awaiting approval`
        : activeJobs.length > 0 ? `${activeJobs.length} automation${activeJobs.length > 1 ? 's' : ''} running` : 'Your agent, on a leash',
      attention: pending.length > 0,
    },
    { key: 'financials', title: 'Financials', Icon: FileText, tint: 'bg-violet-50 text-violet-600', view: { type: 'research' }, line: 'Statements, filings, calls' },
    {
      key: 'calendar', title: 'Calendar', Icon: CalendarDays, tint: 'bg-pink-50 text-pink-600', view: { type: 'calendar' },
      line: myEarnings.length > 0 ? `${myEarnings.length} of yours report${myEarnings.length === 1 ? 's' : ''} this week` : `${earnings.length || 'No'} reports this week`,
      attention: myEarnings.some(e => dayDiff(e.date) <= 1),
    },
    {
      key: 'watching', title: 'Watching', Icon: Eye, tint: 'bg-teal-50 text-teal-600', view: { type: 'watching' },
      line: `${watchlist.length} stock${watchlist.length === 1 ? '' : 's'} · ${activeJobs.length} check${activeJobs.length === 1 ? '' : 's'}`,
    },
  ];

  const firstName = ((user?.user_metadata as any)?.full_name || (user?.user_metadata as any)?.name || '').split(' ')[0];
  const status = marketStatus();
  const submitAsk = () => { const q = ask.trim(); if (q) { openChatWithPrompt(q); setAsk(''); } };

  return (
    <div className="h-full overflow-y-auto bg-[#fafaf9]">
      <div className="max-w-3xl mx-auto px-5 pt-7 pb-16">
        {/* Header */}
        <div className="mb-5">
          {status && <div className="text-[12.5px] font-medium text-stone-500">{status}</div>}
          <h1 className="text-[28px] font-bold text-gray-900 tracking-tight mt-1">{greeting()}{firstName ? `, ${firstName}` : ''}</h1>
        </div>

        {/* Book strip */}
        {digest?.mode === 'portfolio' && digest.total_value != null && (
          <button
            onClick={() => { setHomeTab('portfolio'); navigateTo({ type: 'markets' }); }}
            className="w-full flex items-end justify-between bg-white border border-stone-200/80 rounded-2xl px-5 py-4 mb-3 hover:border-stone-300 transition-colors text-left"
          >
            <div>
              <div className="text-[12px] font-medium text-stone-500">Your book</div>
              <div className="text-[28px] font-bold text-gray-900 tracking-tight tabular-nums">{fmtUsd(digest.total_value)}</div>
            </div>
            <div className="text-right">
              <div className={`text-[17px] font-bold tabular-nums ${(digest.day_change_pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>{fmtPct(digest.day_change_pct)}</div>
              <div className="text-[11.5px] text-stone-400">today</div>
            </div>
          </button>
        )}

        {/* The brief */}
        <div className="bg-white border border-emerald-100 rounded-2xl p-5 mb-4" data-testid="finch-brief">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-[7px] h-[7px] rounded-full bg-emerald-500" />
            <span className="text-[11.5px] font-bold text-emerald-600 uppercase tracking-wider">
              {loading ? 'Checking in…' : brief.length > 0 ? 'Finch noticed' : 'All quiet'}
            </span>
          </div>
          {loading ? (
            <div className="space-y-2 animate-pulse">
              <div className="h-4 w-3/4 bg-stone-100 rounded" />
              <div className="h-3.5 w-1/2 bg-stone-100 rounded" />
            </div>
          ) : brief.length === 0 ? (
            <p className="text-[14.5px] text-stone-700 leading-relaxed">
              {mySymbols.size > 0
                ? `Nothing needs you right now. I'm watching ${mySymbols.size} stock${mySymbols.size === 1 ? '' : 's'} and will ping you if something moves.`
                : "Add a few stocks to Watching or connect a brokerage, and I'll start keeping an eye on them for you."}
            </p>
          ) : (
            brief.map((b, i) => (
              <button key={b.key} onClick={b.onClick}
                className={`w-full flex items-center gap-4 py-2.5 text-left group ${i > 0 ? 'border-t border-stone-100' : ''}`}>
                <div className="flex-1 min-w-0">
                  {b.thesis && b.thesis !== 'intact' ? (
                    <span className="inline-block rounded-md px-1.5 py-0.5 mb-1 text-[10.5px] font-bold"
                      style={{ color: THESIS_STATUS_META[b.thesis].fg, background: THESIS_STATUS_META[b.thesis].bg }}>
                      {THESIS_STATUS_META[b.thesis].label}
                    </span>
                  ) : b.verdict ? (
                    <span className="inline-block rounded-md px-1.5 py-0.5 mb-1 text-[10.5px] font-bold"
                      style={{ color: VERDICT_META[b.verdict].fg, background: VERDICT_META[b.verdict].bg }}>
                      {VERDICT_META[b.verdict].label}
                    </span>
                  ) : null}
                  <div className="text-[15px] font-bold text-gray-900">{b.title}</div>
                  {b.body && <div className="text-[13.5px] text-stone-500 leading-snug mt-0.5 line-clamp-2">{b.body}</div>}
                </div>
                {b.cta ? (
                  <span className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-[12.5px] font-bold ${b.action ? 'bg-emerald-600 text-white group-hover:bg-emerald-700' : 'bg-emerald-50 text-emerald-700 group-hover:bg-emerald-100'}`}>{b.cta}</span>
                ) : (
                  <ChevronRight className="w-4 h-4 text-stone-400 flex-shrink-0" />
                )}
              </button>
            ))
          )}
          {recap?.next_run?.run_at && (
            <div className="text-[12px] text-stone-400 mt-2">
              Next: {recap.next_run.name} · {new Date(recap.next_run.run_at).toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}
            </div>
          )}
        </div>

        {/* Six cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {cards.map(({ key, title, line, attention, Icon, tint, view }) => (
            <button key={key} data-testid={`home-card-${key}`} onClick={() => navigateTo(view)}
              className={`text-left bg-white rounded-2xl border p-4 h-[132px] flex flex-col hover:shadow-sm hover:-translate-y-px transition-all ${attention ? 'border-emerald-200' : 'border-stone-200/80 hover:border-stone-300'}`}>
              <div className="flex items-start justify-between">
                <span className={`w-9 h-9 rounded-xl flex items-center justify-center ${tint}`}><Icon className="w-[18px] h-[18px]" /></span>
                {attention && <span className="w-2 h-2 rounded-full bg-emerald-500 mt-1" />}
              </div>
              <div className="mt-auto">
                <div className="text-[16px] font-bold text-gray-900 tracking-tight">{title}</div>
                <div className={`text-[12.5px] mt-0.5 line-clamp-2 ${attention ? 'text-emerald-600' : 'text-stone-500'}`}>{line}</div>
              </div>
            </button>
          ))}
        </div>

        {/* Market pulse */}
        <button onClick={() => { setHomeTab('markets'); navigateTo({ type: 'markets' }); }}
          className="w-full flex items-center bg-white border border-stone-200/80 rounded-2xl px-5 py-3.5 mt-3 hover:border-stone-300 transition-colors">
          {PULSE.map(p => {
            const chg = pulse[p.symbol]?.changesPercentage;
            return (
              <div key={p.symbol} className="flex-1 text-left">
                <div className="text-[11.5px] font-medium text-stone-500">{p.label}</div>
                <div className={`text-[14px] font-bold tabular-nums ${chg == null ? 'text-stone-400' : chg >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>{fmtPct(chg)}</div>
              </div>
            );
          })}
          <ChevronRight className="w-4 h-4 text-stone-400" />
        </button>

        {/* Ask */}
        <div className="mt-5 flex items-center gap-2 bg-white border border-stone-200 rounded-2xl pl-4 pr-2 py-2 shadow-sm focus-within:border-emerald-300">
          <Sparkles className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <input value={ask} onChange={e => setAsk(e.target.value)} onKeyDown={e => e.key === 'Enter' && submitAsk()}
            placeholder="Ask Finch anything…" className="flex-1 bg-transparent text-[15px] py-1.5 focus:outline-none" />
          <button onClick={submitAsk} disabled={!ask.trim()} aria-label="Send"
            className={`w-8 h-8 rounded-full flex items-center justify-center ${ask.trim() ? 'bg-emerald-600 text-white' : 'bg-stone-200 text-white'}`}>
            <ArrowUp className="w-4 h-4" strokeWidth={2.6} />
          </button>
        </div>
      </div>
    </div>
  );
}
