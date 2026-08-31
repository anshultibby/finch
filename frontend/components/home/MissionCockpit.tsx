'use client';

/**
 * MissionCockpit — the goal-oriented home, rebuilt as a light "mission control".
 *
 * The goal is rendered as a living TRAJECTORY (money's arc to the target), with a
 * bold projected figure, a "Finch's desk" live feed off the activity ledger, and a
 * goal-framed market pulse. Adapts to the goal kind: number/grow get the trajectory
 * instrument; income/protect get a calmer "on watch" framing. Everything degrades
 * honestly before a brokerage is connected (projection + connect nudge, no fake pace).
 */
import React, { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight, LineChart, Bot, Wrench, Sparkles, ListChecks,
  Bell, TrendingUp, Clock, DollarSign, BookOpen, Newspaper, Star,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { goalApi, activityApi, marketApi, type Goal, type AgentEvent, type ActivityRecap } from '@/lib/api';

const NUM = 'var(--font-numeric), var(--font-body), system-ui, sans-serif';
const money = (n?: number | null, dp = 0) =>
  n == null ? '' : `$${n.toLocaleString('en-US', { maximumFractionDigits: dp })}`;

function ago(iso?: string | null): string {
  if (!iso) return '';
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 90) return 'now';
  const m = s / 60; if (m < 60) return `${Math.round(m)}m`;
  const h = m / 60; if (h < 24) return `${Math.round(h)}h`;
  return `${Math.round(h / 24)}d`;
}

type Kind = Goal['kind'];

/** Hero figure + trajectory endpoints, derived from the goal (honest projection). */
function heroFor(goal: Goal): {
  eyebrow: string; title: string; sub: string;
  figure: number | null; figureCap: string; delta: string | null;
  trajectory: boolean; start: number; end: number; axisEnd: string;
} {
  const cap = Number((goal.config as any)?.starting_capital) || 0;
  const risk = goal.risk == null ? '' : goal.risk <= 3 ? 'careful' : goal.risk <= 7 ? 'balanced' : 'full send';
  switch (goal.kind) {
    case 'number': {
      const target = goal.target_amount ?? cap;
      const gain = target - cap;
      const deadline = goal.deadline ? new Date(goal.deadline) : null;
      const when = deadline ? deadline.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'target';
      return {
        eyebrow: `The mission${risk ? ` · ${risk}` : ''}`,
        title: goal.title || `Make ${money(target)}`,
        sub: cap ? `Starting from ${money(cap)}. Aggressive means real swings — I size tight and bank profits.` : 'Let’s make this number.',
        figure: target, figureCap: deadline ? `target by ${when}` : 'target',
        delta: cap && gain > 0 ? `+${money(gain)} to go` : null,
        trajectory: cap > 0 && target > cap, start: cap, end: target, axisEnd: `${money(target)}${deadline ? ` · ${when}` : ''}`,
      };
    }
    case 'grow': {
      const years = goal.horizon_years ?? 10;
      const fv = cap ? Math.round(cap * Math.pow(1.08, years)) : 0;
      const endYear = new Date().getFullYear() + years;
      return {
        eyebrow: `The long game · ${years}-year horizon`,
        title: goal.title || `Grow steadily over ${years} years`,
        sub: cap ? `${money(cap)} compounding at ~8% a year. Boring, and it works.` : 'Steady, low-stress compounding.',
        figure: fv || null, figureCap: `projected value in ${years} years`,
        delta: cap && fv ? `+${money(fv - cap)} · +${Math.round((fv - cap) / cap * 100)}%` : null,
        trajectory: cap > 0 && fv > cap, start: cap, end: fv, axisEnd: `${money(fv)} · ${endYear}`,
      };
    }
    case 'income': {
      const mo = goal.monthly_income ?? 0;
      return {
        eyebrow: `Cash flow${risk ? ` · ${risk}` : ''}`,
        title: goal.title || `Generate ${money(mo)}/mo`,
        sub: cap ? `Realistic on ${money(cap)} at a safe ~3% yield. Covered calls can nudge it higher.` : 'Recurring income from what you hold.',
        figure: mo, figureCap: 'target monthly income', delta: null,
        trajectory: false, start: cap, end: cap, axisEnd: '',
      };
    }
    case 'protect':
    default:
      return {
        eyebrow: 'On watch',
        title: goal.title || 'Watch & protect my portfolio',
        sub: 'Monitoring — no scoreboard, just a heads-up when it matters.',
        figure: cap || null, figureCap: cap ? 'on watch' : '', delta: null,
        trajectory: false, start: cap, end: cap, axisEnd: '',
      };
  }
}

/** SVG line + area paths for an accelerating (compounding) curve from start→end. */
function buildCurve(start: number, end: number) {
  const N = 28, W = 400, H = 120, padX = 8, top = 10, bottom = 112;
  const xs = (t: number) => padX + t * (W - 2 * padX);
  const ys = (v: number) => bottom - ((v - start) / Math.max(1, end - start)) * (bottom - top);
  let line = '';
  for (let i = 0; i < N; i++) {
    const t = i / (N - 1);
    const v = start + (end - start) * Math.pow(t, 1.7); // ease-in → compounding shape
    line += `${i ? ' L' : 'M'}${xs(t).toFixed(1)},${ys(v).toFixed(1)}`;
  }
  const area = `${line} L${xs(1).toFixed(1)},${H} L${xs(0).toFixed(1)},${H} Z`;
  return { line, area, endX: xs(1), endY: ys(end), startX: xs(0), startY: ys(start) };
}

function useCountUp(target: number | null): string {
  const [val, setVal] = useState(target ?? 0);
  useEffect(() => {
    if (target == null) return;
    if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      setVal(target); return;
    }
    let raf = 0, start = 0; const dur = 1100;
    const step = (ts: number) => {
      if (!start) start = ts;
      const p = Math.min(1, (ts - start) / dur);
      setVal(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return money(val);
}

export default function MissionCockpit() {
  const { user } = useAuth();
  const { openChatWithPrompt, navigateTo, openStock } = useNavigation();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [recap, setRecap] = useState<ActivityRecap | null>(null);
  const [indices, setIndices] = useState<Array<{ symbol: string; name: string; price: number | null; chg: number }>>([]);
  const [news, setNews] = useState<Array<{ title: string; site?: string; publishedDate?: string; symbol?: string }>>([]);
  const [ask, setAsk] = useState('');

  useEffect(() => {
    if (!user) return;
    let off = false;
    goalApi.getGoal(user.id).then(g => !off && setGoal(g)).catch(() => {}).finally(() => !off && setLoading(false));
    activityApi.getRecap().then(r => !off && setRecap(r)).catch(() => {});
    Promise.all([
      marketApi.getQuote('SPY').catch(() => null),
      marketApi.getQuote('QQQ').catch(() => null),
      marketApi.getQuote('DIA').catch(() => null),
    ]).then(([spy, qqq, dia]) => {
      if (off) return;
      const mk = (q: any, name: string, symbol: string) => q && ({ symbol, name, price: q.price ?? null, chg: q.changesPercentage ?? 0 });
      setIndices([mk(spy, 'S&P 500', 'SPY'), mk(qqq, 'Nasdaq 100', 'QQQ'), mk(dia, 'Dow Jones', 'DIA')].filter(Boolean) as any);
    });
    marketApi.getGeneralNews(3).then((r: any) => {
      if (off) return;
      const items = Array.isArray(r) ? r : (r?.news || r?.articles || []);
      setNews(items.slice(0, 3).map((n: any) => ({ title: n.title, site: n.site || n.source, publishedDate: n.publishedDate, symbol: n.symbol })));
    }).catch(() => {});
    return () => { off = true; };
  }, [user]);

  const hero = useMemo(() => (goal ? heroFor(goal) : null), [goal]);
  const curve = useMemo(() => (hero?.trajectory ? buildCurve(hero.start, hero.end) : null), [hero]);
  const bigNum = useCountUp(hero?.figure ?? null);
  const strategy = (goal?.config as any)?.strategy as { name?: string; slug?: string } | undefined;

  const suggestions = goal
    ? goal.kind === 'protect'
      ? ['Anything I should worry about today?', 'Summarise my risk', 'Review my recent trades']
      : ['How am I doing on my goal?', 'Review my recent trades', 'Explore strategies']
    : ['Explore strategies', 'What should I look into?'];

  const submitAsk = (text: string) => { if (text.trim()) { openChatWithPrompt(text.trim()); setAsk(''); } };
  const startMission = () => {
    try { if (user) localStorage.removeItem(`finch:goal-wizard-skipped:${user.id}`); } catch { /* best effort */ }
    window.location.reload();
  };

  if (loading) return <div className="h-full grid place-items-center text-gray-400 text-sm">Loading your mission…</div>;

  // Build the "Finch's desk" rows from the ledger (+ strategy + connect nudge).
  const deskRows: Array<{ key: string; icon: React.ReactNode; live?: boolean; tag?: string; title: string; sub?: string; time?: string; onClick?: () => void }> = [];
  if (recap?.running_now) {
    deskRows.push({
      key: 'running', live: true, tag: 'Running now', time: 'now',
      icon: <Clock className="w-[17px] h-[17px]" />, title: recap.running_now.name || 'Finch is working',
      sub: 'Live — tap to watch.', onClick: recap.running_now.chat_id ? () => navigateTo({ type: 'home' }) : undefined,
    });
  }
  (recap?.events || []).slice(0, 4).forEach((e: AgentEvent) => deskRows.push(eventRow(e)));
  if (strategy?.name) {
    deskRows.push({ key: 'strat', icon: <ListChecks className="w-4 h-4" />, title: `You adopted ${strategy.name}`, sub: "Bound to your goal — I'll flag each move for approval.", onClick: () => openChatWithPrompt(`How is my ${strategy.name} strategy set up?`) });
  }
  if (deskRows.length === 0) {
    deskRows.push({ key: 'connect', icon: <Star className="w-4 h-4" />, title: 'Connect a brokerage to bring this to life', sub: "Right now your goal is a projection. Connect and I'll track real pace + review real trades.", onClick: () => navigateTo({ type: 'home' }) });
  }

  return (
    <div className="h-full overflow-y-auto" style={{ background: 'radial-gradient(900px 380px at 84% -8%, rgba(16,185,129,.06), transparent 60%), radial-gradient(700px 320px at 6% -6%, rgba(28,25,23,.03), transparent 55%), var(--finch-bg, #faf9f7)' }}>
      <style>{`
        @keyframes mcRise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
        @keyframes mcDraw{to{stroke-dashoffset:0}}
        @keyframes mcPulse{0%{box-shadow:0 0 0 0 rgba(16,185,129,.45)}70%{box-shadow:0 0 0 7px rgba(16,185,129,0)}100%{box-shadow:0 0 0 0 rgba(16,185,129,0)}}
        .mc-rise{opacity:0;animation:mcRise .6s cubic-bezier(.2,.8,.25,1) forwards}
        .mc-d1{animation-delay:.04s}.mc-d2{animation-delay:.12s}.mc-d3{animation-delay:.2s}.mc-d4{animation-delay:.28s}
        .mc-line{stroke-dasharray:640;stroke-dashoffset:640;animation:mcDraw 1.5s .25s cubic-bezier(.6,.05,.2,1) forwards}
        .mc-pulse{width:6px;height:6px;border-radius:50%;background:#10b981;animation:mcPulse 2.4s infinite}
        @media (prefers-reduced-motion: reduce){.mc-rise,.mc-line{animation:none!important;opacity:1!important;transform:none!important;stroke-dashoffset:0!important}}
      `}</style>

      <div className="max-w-[1080px] mx-auto px-6 py-7">
        {/* ── HERO ── */}
        <section
          className="mc-rise mc-d1 relative overflow-hidden bg-white rounded-[22px] border border-[color:var(--finch-border,rgba(0,0,0,.06))] p-6 sm:p-7 mb-4"
          style={{ boxShadow: '0 24px 60px -44px rgba(28,25,23,.55)' }}
        >
          <div className="pointer-events-none absolute inset-0" style={{ background: 'radial-gradient(520px 220px at 88% -30%, rgba(16,185,129,.10), transparent 70%)' }} />
          {hero ? (
            <div className="relative grid gap-7 md:grid-cols-2 items-center">
              {/* left: mission */}
              <div>
                <div className="font-mono text-[10.5px] tracking-[.16em] uppercase text-gray-400 mb-3">{hero.eyebrow}</div>
                <h1 className="text-[clamp(24px,3.2vw,32px)] font-semibold tracking-tight leading-[1.08] text-gray-900" style={{ fontFamily: NUM, textWrap: 'balance' as any }}>
                  {hero.title}
                </h1>
                <p className="mt-1.5 text-[13.5px] text-gray-600 max-w-[46ch]">{hero.sub}</p>

                {hero.figure != null && (
                  <>
                    <div className="mt-5 flex items-baseline gap-3">
                      <span className="text-[clamp(38px,6vw,54px)] font-bold tracking-tight tabular-nums text-gray-900 leading-none" style={{ fontFamily: NUM }}>{bigNum}</span>
                      {hero.delta && <span className="text-[15px] font-semibold text-emerald-600 tabular-nums" style={{ fontFamily: NUM }}>{hero.delta}</span>}
                    </div>
                    <div className="mt-1.5 text-[12.5px] text-gray-400 tabular-nums">{hero.figureCap}</div>
                  </>
                )}

                {/* command bar */}
                <div className="mt-5 flex items-center gap-3 rounded-[15px] border border-[color:var(--finch-border-strong,rgba(0,0,0,.12))] bg-white px-4 py-3 focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/15 transition-all" style={{ boxShadow: '0 10px 30px -24px rgba(28,25,23,.6)' }}>
                  <Sparkles className="w-[18px] h-[18px] text-emerald-600 flex-shrink-0" />
                  <input
                    value={ask} onChange={e => setAsk(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); submitAsk(ask); } }}
                    placeholder="Ask Finch about your goal, a stock, the market…"
                    className="flex-1 min-w-0 bg-transparent outline-none text-[15px] text-gray-900 placeholder:text-gray-400"
                  />
                  <button onClick={() => submitAsk(ask)} disabled={!ask.trim()} aria-label="Send" className="w-[34px] h-[34px] rounded-[10px] bg-gray-900 text-white grid place-items-center hover:bg-black disabled:opacity-30 transition-colors flex-shrink-0">
                    <ArrowRight className="w-4 h-4 -rotate-90" />
                  </button>
                </div>
                <div className="flex flex-wrap gap-2 mt-3">
                  {suggestions.map((s, i) => (
                    <button key={s} onClick={() => submitAsk(s)}
                      className={`text-[12.5px] rounded-full px-3 py-1.5 border transition-colors ${i === 0 ? 'border-emerald-500/30 text-emerald-700 bg-emerald-50' : 'border-gray-200 text-gray-600 bg-white hover:border-emerald-500 hover:text-emerald-700 hover:bg-emerald-50'}`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              {/* right: trajectory OR on-watch */}
              {curve ? (
                <div className="rounded-2xl border border-[color:var(--finch-border,rgba(0,0,0,.06))] p-4" style={{ background: 'linear-gradient(180deg,#fff,#fbfaf8)' }}>
                  <div className="flex items-baseline justify-between mb-1">
                    <span className="font-mono text-[10px] tracking-[.12em] uppercase text-gray-400">Trajectory</span>
                    <span className="inline-flex items-center gap-1.5 font-mono text-[10px] tracking-[.08em] uppercase text-emerald-700 bg-emerald-50 border border-emerald-500/20 rounded-full px-2.5 py-1">
                      <span className="mc-pulse" /> Connect to track live
                    </span>
                  </div>
                  <svg viewBox="0 0 400 120" preserveAspectRatio="none" className="w-full h-[128px] block" aria-hidden="true">
                    <defs>
                      <linearGradient id="mcFill" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0" stopColor="#10b981" stopOpacity=".2" /><stop offset="1" stopColor="#10b981" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <line x1="0" y1="34" x2="400" y2="34" stroke="rgba(0,0,0,.04)" /><line x1="0" y1="72" x2="400" y2="72" stroke="rgba(0,0,0,.04)" />
                    <path d={curve.area} fill="url(#mcFill)" />
                    <path className="mc-line" d={curve.line} fill="none" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    <circle cx={curve.startX} cy={curve.startY} r="4.5" fill="#fff" stroke="#a8a29e" strokeWidth="2" />
                    <circle cx={curve.endX} cy={curve.endY} r="5" fill="#059669" />
                  </svg>
                  <div className="flex justify-between font-mono text-[10.5px] text-gray-400 tabular-nums mt-1">
                    <span>{money(hero.start)} today</span><span>{hero.axisEnd}</span>
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl border border-[color:var(--finch-border,rgba(0,0,0,.06))] bg-[#fbfaf8] p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <Bot className="w-4 h-4 text-emerald-600" />
                    <span className="text-[12.5px] font-semibold text-gray-900">Finch</span>
                    <span className="font-mono text-[10px] tracking-wider uppercase text-gray-400">on watch</span>
                  </div>
                  <p className="text-[12.5px] text-gray-600 leading-relaxed">
                    {goal!.kind === 'protect'
                      ? "I'm watching your book and the things you flagged. You'll only hear from me when something actually needs you."
                      : "I'll keep this on track quietly and flag the moments that matter. Ask me anything on the left."}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <div className="font-mono text-[10.5px] tracking-[.16em] uppercase text-gray-400 mb-2">No mission set</div>
                <h1 className="text-[26px] font-semibold tracking-tight text-gray-900" style={{ fontFamily: NUM }}>What are we doing with your money?</h1>
                <p className="mt-2 text-[13px] text-gray-500 max-w-md">Give Finch a goal — a number, a horizon, or just “watch my portfolio” — and the whole app orients around it.</p>
              </div>
              <button onClick={startMission} className="self-start inline-flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors whitespace-nowrap">
                Set your mission <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </section>

        {/* ── instruments ── */}
        {hero && goal && (
          <section className="mc-rise mc-d2 grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <Stat k="Starting" v={money(Number((goal.config as any)?.starting_capital) || 0) || '—'} />
            {goal.kind === 'number' && <Stat k="Target" v={money(goal.target_amount) || '—'} />}
            {goal.kind === 'grow' && <Stat k="Projected" v={hero.figure ? money(hero.figure) : '—'} />}
            {goal.kind === 'income' && <Stat k="Income" v={goal.monthly_income ? `${money(goal.monthly_income)}` : '—'} suffix="/mo" />}
            {goal.kind === 'protect' && <Stat k="On watch" v={money(Number((goal.config as any)?.starting_capital) || 0) || '—'} />}
            <Stat k="Horizon" v={goal.horizon_years ? `${goal.horizon_years}` : (goal.deadline ? new Date(goal.deadline).getFullYear().toString() : '—')} suffix={goal.horizon_years ? 'yrs' : ''} />
            <Stat k="Risk" v={goal.risk == null ? '—' : `${goal.risk}`} suffix={goal.risk == null ? '' : '/10'} />
          </section>
        )}

        {/* ── two columns ── */}
        <section className="grid lg:grid-cols-[1.35fr_1fr] gap-4 items-start">
          {/* Finch's desk */}
          <div className="mc-rise mc-d3 bg-white rounded-[18px] border border-[color:var(--finch-border,rgba(0,0,0,.06))] overflow-hidden">
            <div className="flex items-center gap-2 px-4 pt-3.5 pb-2.5">
              <h2 className="text-sm font-semibold text-gray-900" style={{ fontFamily: NUM }}>Finch’s desk</h2>
              <span className="ml-auto font-mono text-[10px] tracking-[.1em] uppercase text-gray-400">while you were away</span>
            </div>
            <div>
              {deskRows.map((r, i) => (
                <button key={r.key} onClick={r.onClick} disabled={!r.onClick}
                  className={`w-full text-left flex gap-3 px-4 py-3 items-start ${i > 0 ? 'border-t border-[color:var(--finch-border,rgba(0,0,0,.06))]' : ''} ${r.onClick ? 'hover:bg-stone-50' : ''} transition-colors`}>
                  <span className={`w-[34px] h-[34px] rounded-[10px] grid place-items-center flex-shrink-0 border ${r.live ? 'bg-emerald-50 text-emerald-600 border-emerald-500/25' : 'bg-stone-50 text-gray-500 border-gray-100'}`}>{r.icon}</span>
                  <span className="flex-1 min-w-0">
                    {r.tag && <span className="flex items-center gap-1.5 font-mono text-[9.5px] tracking-[.1em] uppercase text-emerald-600 mb-0.5"><span className="mc-pulse" />{r.tag}</span>}
                    <span className="block text-[13.5px] font-semibold text-gray-900 truncate">{r.title}</span>
                    {r.sub && <span className="block text-[12.5px] text-gray-500 mt-0.5 line-clamp-2">{r.sub}</span>}
                  </span>
                  {r.time && <span className="font-mono text-[10.5px] text-gray-400 flex-shrink-0">{r.time}</span>}
                </button>
              ))}
            </div>
          </div>

          {/* right stack: market pulse + news */}
          <div className="grid gap-4">
            {indices.length > 0 && (
              <div className="mc-rise mc-d3 bg-white rounded-[18px] border border-[color:var(--finch-border,rgba(0,0,0,.06))] overflow-hidden">
                <div className="flex items-center gap-2 px-4 pt-3.5 pb-2.5">
                  <h2 className="text-sm font-semibold text-gray-900" style={{ fontFamily: NUM }}>Market pulse</h2>
                  <span className="ml-auto font-mono text-[10px] tracking-[.1em] uppercase text-gray-400">today</span>
                </div>
                {indices.map((ix, i) => (
                  <button key={ix.symbol} onClick={() => openStock(ix.symbol)} className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-stone-50 transition-colors ${i > 0 ? 'border-t border-[color:var(--finch-border,rgba(0,0,0,.06))]' : ''}`}>
                    <span className="text-[13.5px] font-semibold text-gray-900 w-14 text-left" style={{ fontFamily: NUM }}>{ix.symbol}</span>
                    <span className="text-[12px] text-gray-400 flex-1 text-left">{ix.name}</span>
                    <span className="text-[13.5px] font-semibold text-gray-900 tabular-nums" style={{ fontFamily: NUM }}>{ix.price != null ? ix.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}</span>
                    <span className={`text-[12px] font-semibold tabular-nums w-16 text-right ${ix.chg >= 0 ? 'text-emerald-600' : 'text-rose-600'}`} style={{ fontFamily: NUM }}>{ix.chg >= 0 ? '+' : ''}{ix.chg.toFixed(2)}%</span>
                  </button>
                ))}
              </div>
            )}

            {news.length > 0 && (
              <div className="mc-rise mc-d4 bg-white rounded-[18px] border border-[color:var(--finch-border,rgba(0,0,0,.06))] overflow-hidden">
                <div className="flex items-center gap-2 px-4 pt-3.5 pb-2.5">
                  <Newspaper className="w-4 h-4 text-gray-400" />
                  <h2 className="text-sm font-semibold text-gray-900" style={{ fontFamily: NUM }}>Worth knowing</h2>
                </div>
                {news.map((n, i) => (
                  <button key={i} onClick={() => n.symbol ? openStock(n.symbol) : openChatWithPrompt(`What's the story behind: "${n.title}"?`)} className={`w-full text-left px-4 py-3 hover:bg-stone-50 transition-colors ${i > 0 ? 'border-t border-[color:var(--finch-border,rgba(0,0,0,.06))]' : ''}`}>
                    <div className="text-[13px] font-semibold text-gray-900 leading-snug line-clamp-2">{n.title}</div>
                    <div className="text-[11.5px] text-gray-400 mt-1 flex items-center gap-1.5">
                      {n.symbol && <span className="font-mono text-[10px] text-emerald-700 bg-emerald-50 rounded px-1.5 py-0.5">{n.symbol}</span>}
                      {[n.site, ago(n.publishedDate)].filter(Boolean).join(' · ')}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ── de-emphasized nav ── */}
        <nav className="mc-rise mc-d4 flex flex-wrap gap-2.5 mt-5">
          <NavChip icon={<LineChart className="w-[15px] h-[15px]" />} label="Markets" onClick={() => navigateTo({ type: 'home' })} />
          <NavChip icon={<Bot className="w-[15px] h-[15px]" />} label="Automations" onClick={() => navigateTo({ type: 'jobs' })} />
          <NavChip icon={<Wrench className="w-[15px] h-[15px]" />} label="Widgets" onClick={() => navigateTo({ type: 'widgets' })} />
        </nav>
      </div>
    </div>
  );
}

function eventRow(e: AgentEvent): { key: string; icon: React.ReactNode; title: string; sub?: string; time?: string } {
  const icon =
    e.event_type === 'alert' ? <Bell className="w-4 h-4" /> :
    e.event_type === 'insight' ? <TrendingUp className="w-4 h-4" /> :
    e.event_type === 'brief' ? <Newspaper className="w-4 h-4" /> :
    e.event_type === 'trade_proposed' || e.event_type === 'trade_decided' ? <DollarSign className="w-4 h-4" /> :
    e.event_type === 'job_run' ? <Clock className="w-4 h-4" /> : <BookOpen className="w-4 h-4" />;
  return { key: e.id, icon, title: e.title, sub: e.body || undefined, time: ago(e.created_at) };
}

function Stat({ k, v, suffix }: { k: string; v: string; suffix?: string }) {
  return (
    <div className="bg-white rounded-[14px] border border-[color:var(--finch-border,rgba(0,0,0,.06))] px-4 py-3.5">
      <div className="font-mono text-[10px] tracking-[.12em] uppercase text-gray-400">{k}</div>
      <div className="mt-1.5 text-[22px] font-semibold tracking-tight tabular-nums text-gray-900" style={{ fontFamily: NUM }}>
        {v}{suffix && <span className="text-[13px] text-gray-400 font-medium ml-0.5">{suffix}</span>}
      </div>
    </div>
  );
}

function NavChip({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="inline-flex items-center gap-2 text-[12.5px] text-gray-600 border border-[color:var(--finch-border,rgba(0,0,0,.06))] bg-white rounded-[10px] px-3 py-2 hover:border-[color:var(--finch-border-strong,rgba(0,0,0,.12))] hover:text-gray-900 transition-colors">
      {icon}{label}
    </button>
  );
}
