'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Sparkles, SlidersHorizontal, Zap, FileText, CalendarDays, Eye, ChevronRight, ArrowUp, type LucideIcon } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation, type View } from '@/contexts/NavigationContext';
import {
  activityApi, insightsApi, marketApi, watchlistApi, jobsApi, ideasApi, thesesApi,
  type ActivityRecap, type PortfolioDigest, type ScheduledJob, type TradeIdea, type MoveVerdict,
  VERDICT_META, THESIS_STATUS_META, type ThesisStatus, type Thesis,
} from '@/lib/api';
import { usePendingTrades } from '@/hooks/usePendingTrades';
import WatchRadar, { type RadarBlip } from './WatchRadar';
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
  // null = not loaded yet, so card lines never claim "0 stocks" or "No reports"
  // before the data has actually arrived.
  const [earnings, setEarnings] = useState<any[] | null>(null);
  const [watchlist, setWatchlist] = useState<string[] | null>(null);
  const [jobs, setJobs] = useState<ScheduledJob[] | null>(null);
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [owned, setOwned] = useState<string[]>([]);
  const [ideas, setIdeas] = useState<TradeIdea[]>([]);
  const [pulse, setPulse] = useState<Record<string, any>>({});
  const [ask, setAsk] = useState('');
  const [quotes, setQuotes] = useState<Record<string, number>>({});

  // The brief renders as soon as the fast, decisive sources land (approvals,
  // the user's symbols, the earnings calendar). Slower sources — the activity
  // recap, ideas, and the LLM-written digest — join it when they arrive.
  useEffect(() => {
    if (!user) return;
    let alive = true;
    const set = <T,>(fn: (v: T) => void) => (v: T) => { if (alive) fn(v); };
    insightsApi.getPortfolioDigest(user.id).then(set(setDigest)).catch(() => {});
    activityApi.getRecap().then(set(setRecap)).catch(() => {});
    jobsApi.list().then(d => set(setJobs)(d.jobs || [])).catch(() => set(setJobs)([]));
    ideasApi.list(20).then(d => set(setIdeas)(d.ideas || [])).catch(() => {});
    thesesApi.list().then(d => { set(setTheses)(d.theses || []); set(setOwned)(d.owned || []); }).catch(() => {});
    marketApi.getBatchQuotes(PULSE.map(p => p.symbol)).then(rows => {
      if (!Array.isArray(rows)) return;
      const m: Record<string, any> = {};
      rows.forEach((q: any) => { if (q?.symbol) m[q.symbol] = q; });
      set(setPulse)(m);
    }).catch(() => {});
    Promise.all([
      marketApi.getEarnings().then(d => set(setEarnings)(Array.isArray(d) ? d : d?.earnings || [])).catch(() => set(setEarnings)([])),
      watchlistApi.getWatchlist(user.id).then(d => {
        const raw = d?.symbols || d?.watchlist || [];
        set(setWatchlist)(raw.map((i: any) => (typeof i === 'string' ? i : i.symbol)).filter(Boolean));
      }).catch(() => set(setWatchlist)([])),
    ]).finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [user]);

  const mySymbols = useMemo(() => {
    const s = new Set<string>((watchlist || []).map(x => x.toUpperCase()));
    owned.forEach(x => s.add(x.toUpperCase()));
    (digest?.movers || []).forEach(m => s.add(m.symbol.toUpperCase()));
    return s;
  }, [watchlist, digest, owned]);

  // Today's move for each of the user's stocks — the radar's blips.
  const symbolsKey = Array.from(mySymbols).sort().join(',');
  useEffect(() => {
    if (!symbolsKey) return;
    let alive = true;
    marketApi.getBatchQuotes(symbolsKey.split(',').slice(0, 24)).then(rows => {
      if (!alive || !Array.isArray(rows)) return;
      const m: Record<string, number> = {};
      rows.forEach((q: any) => { if (q?.symbol && q.changesPercentage != null) m[q.symbol.toUpperCase()] = q.changesPercentage; });
      setQuotes(m);
    }).catch(() => {});
    return () => { alive = false; };
  }, [symbolsKey]);

  const myEarnings = useMemo(
    () => (earnings || [])
      .filter(e => e?.symbol && mySymbols.has(String(e.symbol).toUpperCase()))
      .filter(e => { const d = dayDiff(e.date); return d >= 0 && d <= 7; })
      .sort((a, b) => String(a.date).localeCompare(String(b.date))),
    [earnings, mySymbols],
  );

  const thesisBySymbol = useMemo(() => new Map(theses.map(t => [t.symbol, t])), [theses]);
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
      const t = thesisBySymbol.get(String(soon.symbol).toUpperCase());
      items.push({
        key: `earn-${soon.symbol}`,
        title: `${soon.symbol} reports ${whenLabel(soon.date, soon.time)}`,
        // With a thesis, the heads-up is about *their* line in the sand.
        body: t?.breaks
          ? `You said you'd ${t.stance === 'own' ? 'sell' : 'reconsider'} if: ${t.breaks}`
          : 'Want the setup — what the street expects, the implied move, and what it means for you?',
        cta: 'Preview it',
        onClick: () => openChatWithPrompt(earningsPreviewPrompt(soon.symbol, t), `${soon.symbol} earnings preview`),
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
    // Held stocks first — a thesis matters most where real money is.
    const heldUncovered = owned.find(sym => !thesisBySymbol.has(sym));
    const firstUncovered = heldUncovered || (watchlist || []).find(sym => !thesisBySymbol.has(sym.toUpperCase()));
    if (theses.length === 0 && firstUncovered && items.length < 3) {
      items.push({
        key: 'thesis-nudge',
        title: heldUncovered ? `Why do you own ${firstUncovered}?` : `Why are you watching ${firstUncovered}?`,
        body: heldUncovered
          ? 'Write one line on why, and what would make you sell. Every alert on it gets judged against your words.'
          : 'Write one line on why, and what would make you buy. Every alert on it gets judged against your words.',
        cta: 'Write it',
        onClick: () => openStock(firstUncovered),
      });
    }
    return items.slice(0, 3);
  }, [pending, myEarnings, recap, digest, navigateTo, openChatWithPrompt, setHomeTab, loadChat, openStock, thesisBySymbol, theses, watchlist, owned]);

  // Next of the user's own reports, as "NFLX Tue, META Wed".
  const nextReports = myEarnings.slice(0, 2).map(e =>
    `${e.symbol} ${new Date(`${e.date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short' })}`).join(', ');

  // Each tile's second line is live state — what's there right now — rather
  // than a tagline describing the tool.
  const cards: { key: string; title: string; line: string; attention?: boolean; Icon: LucideIcon; view: View }[] = [
    {
      key: 'assistant', title: 'Ask Finch', Icon: Sparkles, view: { type: 'assistant' },
      line: openIdeas.length > 0 ? `${openIdeas.length} idea${openIdeas.length > 1 ? 's' : ''} waiting` : 'Ask about anything',
      attention: openIdeas.length > 0,
    },
    { key: 'screener', title: 'Screener', Icon: SlidersHorizontal, view: { type: 'screener' }, line: 'Describe the stocks you want' },
    {
      key: 'trader', title: 'Trader', Icon: Zap, view: { type: 'trader' },
      line: pending.length > 0 ? `${pending.length} trade${pending.length > 1 ? 's' : ''} to approve` : jobs === null ? 'Approvals and automations' : 'Nothing to approve',
      attention: pending.length > 0,
    },
    { key: 'financials', title: 'Financials', Icon: FileText, view: { type: 'research' }, line: 'Statements and filings' },
    {
      key: 'calendar', title: 'Calendar', Icon: CalendarDays, view: { type: 'calendar' },
      line: earnings === null || watchlist === null
        ? 'Earnings and Finch’s schedule'
        : nextReports || `${earnings.length || 'No'} reports this week`,
      attention: myEarnings.some(e => dayDiff(e.date) <= 1),
    },
    {
      key: 'watching', title: 'Watching', Icon: Eye, view: { type: 'watching' },
      line: watchlist === null || jobs === null
        ? 'Stocks, theses and checks'
        : `${watchlist.length} stock${watchlist.length === 1 ? '' : 's'}, ${theses.length} thes${theses.length === 1 ? 'is' : 'es'}`,
    },
  ];

  const firstName = ((user?.user_metadata as any)?.full_name || (user?.user_metadata as any)?.name || '').split(' ')[0];
  const status = marketStatus();
  const submitAsk = () => { const q = ask.trim(); if (q) { openChatWithPrompt(q); setAsk(''); } };

  // Names Finch has flagged (story change / thesis weakened or broken) glow amber on the radar.
  const flagged = new Set(
    (recap?.events || [])
      .filter(e => e.data?.verdict === 'narrative_shift' || e.data?.thesis_status === 'weakened' || e.data?.thesis_status === 'broken')
      .map(e => String(e.data?.symbol || '').toUpperCase()),
  );
  const blips: RadarBlip[] = Array.from(mySymbols).slice(0, 24).map(sym => ({
    symbol: sym,
    changePct: quotes[sym] ?? null,
    held: owned.includes(sym),
    thesis: thesisBySymbol.has(sym),
    alert: flagged.has(sym),
  }));

  // Tag colours tuned for the dark desk.
  const darkTag = (b: BriefItem) =>
    b.thesis === 'broken' ? { text: THESIS_STATUS_META.broken.label, color: '#fda4af' }
      : b.thesis === 'weakened' ? { text: THESIS_STATUS_META.weakened.label, color: '#fbbf24' }
        : b.verdict === 'narrative_shift' ? { text: VERDICT_META.narrative_shift.label, color: '#fbbf24' }
          : b.verdict === 'news' ? { text: VERDICT_META.news.label, color: '#7dd3fc' }
            : null;

  return (
    <div className="h-full overflow-y-auto bg-[#fafaf9]">
      <div className="max-w-5xl mx-auto px-5 sm:px-6 pt-6 pb-16">
        {/* Finch's desk — the one bold surface: Finch speaking, beside the radar
            of everything it's watching. Everything below is quiet. */}
        <section data-testid="finch-brief"
          className="relative overflow-hidden rounded-[28px] text-emerald-50 bg-[radial-gradient(120%_130%_at_88%_18%,#0f5a45_0%,#073a2d_42%,#04241c_100%)] shadow-[0_24px_60px_-28px_rgba(4,36,28,0.65)]">
          <div className="grid md:grid-cols-[minmax(0,1fr)_auto] gap-6 md:gap-10 items-center px-6 sm:px-9 pt-8 pb-6">
            <div className="min-w-0">
              {status && <div className="text-[13px] font-medium text-emerald-200/70">{status}</div>}
              <h1 className="text-[34px] sm:text-[40px] font-bold tracking-tight leading-[1.05] mt-1.5 text-white">
                {greeting()}{firstName ? `, ${firstName}` : ''}
              </h1>
              {digest?.mode === 'portfolio' && digest.total_value != null && (
                <button onClick={() => { setHomeTab('portfolio'); navigateTo({ type: 'markets' }); }}
                  className="mt-2 text-[15px] text-emerald-100/80 hover:text-white tabular-nums">
                  Your book {fmtUsd(digest.total_value)}{' '}
                  <span className={(digest.day_change_pct ?? 0) >= 0 ? 'text-emerald-300 font-bold' : 'text-rose-300 font-bold'}>{fmtPct(digest.day_change_pct)}</span> today
                </button>
              )}

              <div className="mt-6 max-w-[560px]">
                {loading ? (
                  <div className="space-y-2.5 animate-pulse">
                    <div className="h-5 w-4/5 bg-white/10 rounded" />
                    <div className="h-4 w-3/5 bg-white/10 rounded" />
                  </div>
                ) : brief.length === 0 ? (
                  <p className="text-[19px] font-medium leading-snug text-white">
                    {mySymbols.size > 0
                      ? `Nothing needs you right now. I'm watching ${mySymbols.size} stock${mySymbols.size === 1 ? '' : 's'} and will tell you if something changes.`
                      : "Add a few stocks to Watching or connect a brokerage, and I'll start keeping an eye on them for you."}
                  </p>
                ) : (
                  brief.map((b, i) => {
                    const tag = darkTag(b);
                    return (
                      <button key={b.key} onClick={b.onClick}
                        className={`block w-full text-left group ${i === 0 ? '' : 'mt-4 pt-4 border-t border-white/10'}`}>
                        {tag && <div className="text-[12.5px] font-bold mb-1" style={{ color: tag.color }}>{tag.text}</div>}
                        <div className={`${i === 0 ? 'text-[21px]' : 'text-[16.5px]'} font-bold tracking-tight leading-snug text-white group-hover:text-emerald-100`}>{b.title}</div>
                        {b.body && <div className={`${i === 0 ? 'text-[15px]' : 'text-[14px]'} text-emerald-50/70 leading-relaxed mt-1 line-clamp-3`}>{b.body}</div>}
                        {b.cta && (
                          <span className={`inline-block mt-3 px-4 py-1.5 rounded-full text-[13px] font-bold transition-colors ${b.action ? 'bg-emerald-400 text-emerald-950 group-hover:bg-emerald-300' : 'bg-white/10 text-emerald-50 group-hover:bg-white/20'}`}>{b.cta}</span>
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            <div className="hidden md:flex flex-col items-center">
              <WatchRadar blips={blips} size={300} onSelect={sym => openStock(sym)} />
              <div className="text-[12.5px] text-emerald-100/60 -mt-1 text-center">
                {mySymbols.size > 0
                  ? `Watching ${mySymbols.size} stock${mySymbols.size === 1 ? '' : 's'}${theses.length ? `, ${theses.length} with your thesis` : ''}`
                  : 'Nothing on the radar yet'}
              </div>
            </div>
          </div>

          {/* Market line + next check, set into the desk's bottom edge */}
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-6 sm:px-9 py-3.5 border-t border-white/10 bg-black/10 text-[13px] text-emerald-100/70 tabular-nums">
            {PULSE.map(p => {
              const chg = pulse[p.symbol]?.changesPercentage;
              return (
                <span key={p.symbol}>
                  {p.label}{' '}
                  <span className={`font-bold ${chg == null ? 'text-emerald-100/40' : chg >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>{fmtPct(chg)}</span>
                </span>
              );
            })}
            {!loading && recap?.next_run?.run_at && (
              <span className="text-emerald-100/50">
                Next check: {recap.next_run.name.toLowerCase()}, {new Date(recap.next_run.run_at).toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}
              </span>
            )}
            <button onClick={() => { setHomeTab('markets'); navigateTo({ type: 'markets' }); }}
              className="ml-auto flex items-center gap-1 font-semibold text-emerald-100/80 hover:text-white">
              Markets <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </section>

        {/* The six tools: one quiet panel, hairline dividers, monochrome icons.
            Emerald only where something needs the user. */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 bg-white rounded-[18px] border border-stone-200/80 overflow-hidden [&>*]:border-stone-200/80">
          {cards.map(({ key, title, line, attention, Icon, view }, i) => (
            <button key={key} data-testid={`home-card-${key}`} onClick={() => navigateTo(view)}
              className={`text-left px-5 py-4 min-h-[112px] hover:bg-stone-50 transition-colors border-b sm:[&:nth-child(n+4)]:border-b-0 max-sm:[&:nth-child(n+5)]:border-b-0 ${i % 2 === 0 ? 'max-sm:border-r' : ''} ${i % 3 !== 2 ? 'sm:border-r' : ''}`}>
              <div className="flex items-center justify-between">
                <Icon className={`w-[17px] h-[17px] ${attention ? 'text-emerald-600' : 'text-stone-500'}`} strokeWidth={1.9} />
                {attention && <span className="w-[7px] h-[7px] rounded-full bg-emerald-500" />}
              </div>
              <div className="text-[15.5px] font-bold text-stone-900 mt-3">{title}</div>
              <div className={`text-[13px] mt-0.5 line-clamp-2 ${attention ? 'text-emerald-700 font-medium' : 'text-stone-500'}`}>{line}</div>
            </button>
          ))}
        </div>

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
