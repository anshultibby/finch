'use client';

/**
 * MissionCockpit — the goal-oriented home, now a SPEC-DRIVEN board of blocks.
 *
 * The layout is a "cockpit" widget (kind="cockpit") the agent can reorder /
 * toggle / configure. This component fetches that spec + its resolved data and
 * renders each tile with a cockpit-styled block component (chosen by data shape).
 * The ask bar + nav are fixed chrome (interactive, so not tiles). Blocks:
 * goal→trajectory hero, activity→Finch's desk, trades→trade feedback,
 * quote→market pulse, news→worth-knowing. Degrades honestly (connect nudges).
 */
import React, { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight, LineChart, Bot, Wrench, Sparkles,
  Bell, TrendingUp, Clock, DollarSign, BookOpen, Newspaper, Star, ChevronRight,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { widgetsApi } from '@/lib/api';
import type { Widget, Tile } from '@/components/widgets/types';

const NUM = 'var(--font-numeric), var(--font-body), system-ui, sans-serif';
type Payload = Record<string, any>;

const money = (n?: number | null) => (n == null ? '' : `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`);
function ago(iso?: string | null): string {
  if (!iso) return '';
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 90) return 'now';
  const m = s / 60; if (m < 60) return `${Math.round(m)}m`;
  const h = m / 60; if (h < 24) return `${Math.round(h)}h`;
  return `${Math.round(h / 24)}d`;
}
function fmtDate(iso?: string | null): string {
  if (!iso) return '';
  try { return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); } catch { return ''; }
}

/** SVG line + area for an accelerating (compounding) curve from start→end. */
function buildCurve(start: number, end: number) {
  const N = 28, W = 400, H = 120, padX = 8, top = 10, bottom = 112;
  const xs = (t: number) => padX + t * (W - 2 * padX);
  const ys = (v: number) => bottom - ((v - start) / Math.max(1, end - start)) * (bottom - top);
  let line = '';
  for (let i = 0; i < N; i++) {
    const t = i / (N - 1);
    const v = start + (end - start) * Math.pow(t, 1.7);
    line += `${i ? ' L' : 'M'}${xs(t).toFixed(1)},${ys(v).toFixed(1)}`;
  }
  const area = `${line} L${xs(1).toFixed(1)},${H} L${xs(0).toFixed(1)},${H} Z`;
  return { line, area, startX: xs(0), startY: ys(start), endX: xs(1), endY: ys(end) };
}

function useCountUp(target: number | null): string {
  const [val, setVal] = useState(target ?? 0);
  useEffect(() => {
    if (target == null) return;
    if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setVal(target); return; }
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

function reviewPrompt(t: Payload): string {
  const action = t.side === 'BUY' ? 'bought' : 'sold';
  return `I ${action} ${t.quantity} shares of ${t.symbol} at ${money(t.price)} on ${fmtDate(t.date)} (~${money(t.amount)}). `
    + `Review this trade against my goal — was the entry, timing, and sizing sound? Then suggest 2-3 concrete alternatives.`;
}

const spanFor = (size?: string) => (size === 'full' || size === 'lg') ? 'lg:col-span-2' : 'lg:col-span-1';

export default function MissionCockpit() {
  const { user } = useAuth();
  const { openChatWithPrompt, navigateTo, openStock } = useNavigation();
  const [cockpit, setCockpit] = useState<Widget | null>(null);
  const [data, setData] = useState<Record<string, Payload>>({});
  const [loading, setLoading] = useState(true);
  const [ask, setAsk] = useState('');

  useEffect(() => {
    if (!user) return;
    let off = false;
    (async () => {
      try {
        const w = await widgetsApi.getCockpit();
        if (off) return;
        setCockpit(w);
        const d = await widgetsApi.getData(w.id);
        if (!off) setData(d as any);
      } catch { /* fail open — render loading→empty */ }
      finally { if (!off) setLoading(false); }
    })();
    return () => { off = true; };
  }, [user]);

  const tiles: Tile[] = (cockpit?.spec?.tiles as any) || [];
  const heroTile = useMemo(() => tiles.find(t => t.type === 'goal'), [tiles]);
  const restTiles = useMemo(() => tiles.filter(t => t.id !== heroTile?.id), [tiles, heroTile]);
  const heroData: Payload = (heroTile && data[heroTile.id]) || {};
  const hasGoal = heroData.shape === 'trajectory';

  const suggestions = hasGoal
    ? (heroData.kind === 'protect'
        ? ['Anything I should worry about today?', 'Summarise my risk', 'Review my recent trades']
        : ['How am I doing on my goal?', 'Review my recent trades', 'Explore strategies'])
    : ['Explore strategies', 'What should I look into?'];

  const submitAsk = (text: string) => { if (text.trim()) { openChatWithPrompt(text.trim()); setAsk(''); } };
  const startMission = () => {
    try { if (user) localStorage.removeItem(`finch:goal-wizard-skipped:${user.id}`); } catch { /* best effort */ }
    window.location.reload();
  };

  if (loading) return <div className="h-full grid place-items-center text-gray-400 text-sm">Loading your mission…</div>;

  return (
    <div className="h-full overflow-y-auto" style={{ background: 'radial-gradient(900px 380px at 84% -8%, rgba(16,185,129,.06), transparent 60%), radial-gradient(700px 320px at 6% -6%, rgba(28,25,23,.03), transparent 55%), var(--finch-bg, #faf9f7)' }}>
      <style>{`
        @keyframes mcRise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
        @keyframes mcDraw{to{stroke-dashoffset:0}}
        @keyframes mcPulse{0%{box-shadow:0 0 0 0 rgba(16,185,129,.45)}70%{box-shadow:0 0 0 7px rgba(16,185,129,0)}100%{box-shadow:0 0 0 0 rgba(16,185,129,0)}}
        .mc-rise{opacity:0;animation:mcRise .6s cubic-bezier(.2,.8,.25,1) forwards}
        .mc-d1{animation-delay:.04s}.mc-d2{animation-delay:.12s}.mc-d3{animation-delay:.2s}
        .mc-line{stroke-dasharray:640;stroke-dashoffset:640;animation:mcDraw 1.5s .25s cubic-bezier(.6,.05,.2,1) forwards}
        .mc-pulse{width:6px;height:6px;border-radius:50%;background:#10b981;animation:mcPulse 2.4s infinite}
        @media (prefers-reduced-motion: reduce){.mc-rise,.mc-line{animation:none!important;opacity:1!important;transform:none!important;stroke-dashoffset:0!important}}
      `}</style>

      <div className="max-w-[1080px] mx-auto px-6 py-7">
        {/* HERO (goal block) — pinned full-width */}
        <div className="mc-rise mc-d1 mb-4">
          {hasGoal ? <Hero p={heroData} big={<HeroFigure value={heroData.figure} />} />
            : <NoGoal onStart={startMission} />}
        </div>

        {/* command bar — fixed chrome */}
        <div className="mc-rise mc-d2 mb-5">
          <div className="flex items-center gap-3 rounded-[15px] border border-[color:var(--finch-border-strong,rgba(0,0,0,.12))] bg-white px-4 py-3 focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/15 transition-all" style={{ boxShadow: '0 10px 30px -24px rgba(28,25,23,.6)' }}>
            <Sparkles className="w-[18px] h-[18px] text-emerald-600 flex-shrink-0" />
            <input value={ask} onChange={e => setAsk(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); submitAsk(ask); } }}
              placeholder="Ask Finch about your goal, a stock, the market…"
              className="flex-1 min-w-0 bg-transparent outline-none text-[15px] text-gray-900 placeholder:text-gray-400" />
            <button onClick={() => submitAsk(ask)} disabled={!ask.trim()} aria-label="Send" className="w-[34px] h-[34px] rounded-[10px] bg-gray-900 text-white grid place-items-center hover:bg-black disabled:opacity-30 transition-colors flex-shrink-0">
              <ArrowRight className="w-4 h-4 -rotate-90" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            {suggestions.map((s, i) => (
              <button key={s} onClick={() => submitAsk(s)}
                className={`text-[12.5px] rounded-full px-3 py-1.5 border transition-colors ${i === 0 ? 'border-emerald-500/30 text-emerald-700 bg-emerald-50' : 'border-gray-200 text-gray-600 bg-white hover:border-emerald-500 hover:text-emerald-700 hover:bg-emerald-50'}`}>{s}</button>
            ))}
          </div>
        </div>

        {/* board — rest of the blocks, spec order + size */}
        <div className="mc-rise mc-d3 grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          {restTiles.map(tile => {
            const p = data[tile.id];
            const block = renderBlock(tile, p, { openStock, openChatWithPrompt, navigateTo });
            return block ? <div key={tile.id} className={spanFor(tile.size)}>{block}</div> : null;
          })}
        </div>

        {/* nav — fixed chrome */}
        <nav className="mc-rise mc-d3 flex flex-wrap gap-2.5 mt-5">
          <NavChip icon={<LineChart className="w-[15px] h-[15px]" />} label="Markets" onClick={() => navigateTo({ type: 'home' })} />
          <NavChip icon={<Bot className="w-[15px] h-[15px]" />} label="Automations" onClick={() => navigateTo({ type: 'jobs' })} />
          <NavChip icon={<Wrench className="w-[15px] h-[15px]" />} label="Widgets" onClick={() => navigateTo({ type: 'widgets' })} />
        </nav>
      </div>
    </div>
  );
}

function renderBlock(tile: Tile, p: Payload | undefined, nav: any): React.ReactNode {
  const shape = p?.shape;
  if (shape === 'activity') return <Desk p={p!} title={tile.title} nav={nav} />;
  if (shape === 'trades') return <Trades p={p!} title={tile.title} nav={nav} />;
  if (shape === 'table') return <Pulse p={p!} title={tile.title} nav={nav} />;
  if (shape === 'news') return <News p={p!} title={tile.title} nav={nav} />;
  if (shape === 'number') return <StatBlock p={p!} />;
  return null;
}

// ── blocks ────────────────────────────────────────────────────────────────
function HeroFigure({ value }: { value: number | null | undefined }) {
  const s = useCountUp(value ?? null);
  if (value == null) return null;
  return <span className="text-[clamp(38px,6vw,54px)] font-bold tracking-tight tabular-nums text-gray-900 leading-none" style={{ fontFamily: NUM }}>{s}</span>;
}

function Hero({ p, big }: { p: Payload; big: React.ReactNode }) {
  const curve = p.trajectory && p.end > p.start ? buildCurve(p.start, p.end) : null;
  return (
    <section className="relative overflow-hidden bg-white rounded-[22px] border border-[color:var(--finch-border,rgba(0,0,0,.06))] p-6 sm:p-7" style={{ boxShadow: '0 24px 60px -44px rgba(28,25,23,.55)' }}>
      <div className="pointer-events-none absolute inset-0" style={{ background: 'radial-gradient(520px 220px at 88% -30%, rgba(16,185,129,.10), transparent 70%)' }} />
      <div className="relative grid gap-7 md:grid-cols-2 items-center">
        <div>
          <div className="font-mono text-[10.5px] tracking-[.16em] uppercase text-gray-400 mb-3">{p.eyebrow}</div>
          <h1 className="text-[clamp(24px,3.2vw,32px)] font-semibold tracking-tight leading-[1.08] text-gray-900" style={{ fontFamily: NUM, textWrap: 'balance' as any }}>{p.title}</h1>
          <p className="mt-1.5 text-[13.5px] text-gray-600 max-w-[46ch]">{p.sub}</p>
          {p.figure != null && (
            <>
              <div className="mt-5 flex items-baseline gap-3">
                {big}
                {p.delta && <span className="text-[15px] font-semibold text-emerald-600 tabular-nums" style={{ fontFamily: NUM }}>{p.delta}</span>}
              </div>
              <div className="mt-1.5 text-[12.5px] text-gray-400 tabular-nums">{p.figureCap}</div>
            </>
          )}
          {Array.isArray(p.instruments) && p.instruments.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2">
              {p.instruments.map((it: Payload, i: number) => (
                <div key={i} className="rounded-xl border border-[color:var(--finch-border,rgba(0,0,0,.06))] bg-[#fbfaf8] px-3 py-2">
                  <div className="font-mono text-[9.5px] tracking-[.12em] uppercase text-gray-400">{it.k}</div>
                  <div className="text-[16px] font-semibold tabular-nums text-gray-900" style={{ fontFamily: NUM }}>{it.v}{it.suffix && <span className="text-[11px] text-gray-400 ml-0.5">{it.suffix}</span>}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        {curve ? (
          <div className="rounded-2xl border border-[color:var(--finch-border,rgba(0,0,0,.06))] p-4" style={{ background: 'linear-gradient(180deg,#fff,#fbfaf8)' }}>
            <div className="flex items-baseline justify-between mb-1">
              <span className="font-mono text-[10px] tracking-[.12em] uppercase text-gray-400">Trajectory</span>
              <span className="inline-flex items-center gap-1.5 font-mono text-[10px] tracking-[.08em] uppercase text-emerald-700 bg-emerald-50 border border-emerald-500/20 rounded-full px-2.5 py-1"><span className="mc-pulse" /> Connect to track live</span>
            </div>
            <svg viewBox="0 0 400 120" preserveAspectRatio="none" className="w-full h-[128px] block" aria-hidden="true">
              <defs><linearGradient id="mcFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#10b981" stopOpacity=".2" /><stop offset="1" stopColor="#10b981" stopOpacity="0" /></linearGradient></defs>
              <line x1="0" y1="34" x2="400" y2="34" stroke="rgba(0,0,0,.04)" /><line x1="0" y1="72" x2="400" y2="72" stroke="rgba(0,0,0,.04)" />
              <path d={curve.area} fill="url(#mcFill)" />
              <path className="mc-line" d={curve.line} fill="none" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx={curve.startX} cy={curve.startY} r="4.5" fill="#fff" stroke="#a8a29e" strokeWidth="2" />
              <circle cx={curve.endX} cy={curve.endY} r="5" fill="#059669" />
            </svg>
            <div className="flex justify-between font-mono text-[10.5px] text-gray-400 tabular-nums mt-1"><span>{money(p.start)} today</span><span>{p.axisEnd}</span></div>
          </div>
        ) : (
          <div className="rounded-2xl border border-[color:var(--finch-border,rgba(0,0,0,.06))] bg-[#fbfaf8] p-5">
            <div className="flex items-center gap-2 mb-2"><Bot className="w-4 h-4 text-emerald-600" /><span className="text-[12.5px] font-semibold text-gray-900">Finch</span><span className="font-mono text-[10px] tracking-wider uppercase text-gray-400">on watch</span></div>
            <p className="text-[12.5px] text-gray-600 leading-relaxed">I'll keep this on track quietly and flag the moments that matter. Ask me anything above.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function NoGoal({ onStart }: { onStart: () => void }) {
  return (
    <section className="relative overflow-hidden bg-white rounded-[22px] border border-[color:var(--finch-border,rgba(0,0,0,.06))] p-7 flex flex-col md:flex-row md:items-center md:justify-between gap-4" style={{ boxShadow: '0 24px 60px -44px rgba(28,25,23,.55)' }}>
      <div>
        <div className="font-mono text-[10.5px] tracking-[.16em] uppercase text-gray-400 mb-2">No mission set</div>
        <h1 className="text-[26px] font-semibold tracking-tight text-gray-900" style={{ fontFamily: NUM }}>What are we doing with your money?</h1>
        <p className="mt-2 text-[13px] text-gray-500 max-w-md">Give Finch a goal — a number, a horizon, or just “watch my portfolio” — and the whole app orients around it.</p>
      </div>
      <button onClick={onStart} className="self-start inline-flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors whitespace-nowrap">Set your mission <ArrowRight className="w-4 h-4" /></button>
    </section>
  );
}

function Panel({ title, muted, children }: { title?: string; muted?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-[18px] border border-[color:var(--finch-border,rgba(0,0,0,.06))] overflow-hidden h-full">
      {(title || muted) && (
        <div className="flex items-center gap-2 px-4 pt-3.5 pb-2.5">
          {title && <h2 className="text-sm font-semibold text-gray-900" style={{ fontFamily: NUM }}>{title}</h2>}
          {muted && <span className="ml-auto font-mono text-[10px] tracking-[.1em] uppercase text-gray-400">{muted}</span>}
        </div>
      )}
      {children}
    </div>
  );
}

function eventIcon(type?: string) {
  if (type === 'alert') return <Bell className="w-4 h-4" />;
  if (type === 'insight') return <TrendingUp className="w-4 h-4" />;
  if (type === 'brief') return <Newspaper className="w-4 h-4" />;
  if (type === 'trade_proposed' || type === 'trade_decided') return <DollarSign className="w-4 h-4" />;
  if (type === 'job_run') return <Clock className="w-4 h-4" />;
  return <BookOpen className="w-4 h-4" />;
}

function Desk({ p, title, nav }: { p: Payload; title?: string; nav: any }) {
  const rows: React.ReactNode[] = [];
  if (p.running_now) rows.push(
    <Row key="run" live tag="Running now" time="now" icon={<Clock className="w-[17px] h-[17px]" />}
      titleText={p.running_now.name || 'Finch is working'} sub="Live — tap to watch." onClick={() => nav.navigateTo({ type: 'home' })} />
  );
  (p.events || []).forEach((e: Payload, i: number) => rows.push(
    <Row key={i} icon={eventIcon(e.type)} titleText={e.title} sub={e.body} time={ago(e.created_at)} />
  ));
  if (rows.length === 0) rows.push(
    <Row key="c" icon={<Star className="w-4 h-4" />} titleText="Connect a brokerage to bring this to life"
      sub="Right now your goal is a projection. Connect and I'll track real pace + review real trades." onClick={() => nav.navigateTo({ type: 'home' })} />
  );
  return <Panel title={title || "Finch’s desk"} muted="while you were away">{rows}</Panel>;
}

function Row({ icon, titleText, sub, time, live, tag, onClick }: { icon: React.ReactNode; titleText: string; sub?: string; time?: string; live?: boolean; tag?: string; onClick?: () => void }) {
  return (
    <button onClick={onClick} disabled={!onClick} className={`w-full text-left flex gap-3 px-4 py-3 items-start border-t first:border-t-0 border-[color:var(--finch-border,rgba(0,0,0,.06))] ${onClick ? 'hover:bg-stone-50' : ''} transition-colors`}>
      <span className={`w-[34px] h-[34px] rounded-[10px] grid place-items-center flex-shrink-0 border ${live ? 'bg-emerald-50 text-emerald-600 border-emerald-500/25' : 'bg-stone-50 text-gray-500 border-gray-100'}`}>{icon}</span>
      <span className="flex-1 min-w-0">
        {tag && <span className="flex items-center gap-1.5 font-mono text-[9.5px] tracking-[.1em] uppercase text-emerald-600 mb-0.5"><span className="mc-pulse" />{tag}</span>}
        <span className="block text-[13.5px] font-semibold text-gray-900 truncate">{titleText}</span>
        {sub && <span className="block text-[12.5px] text-gray-500 mt-0.5 line-clamp-2">{sub}</span>}
      </span>
      {time && <span className="font-mono text-[10.5px] text-gray-400 flex-shrink-0">{time}</span>}
    </button>
  );
}

function Trades({ p, title, nav }: { p: Payload; title?: string; nav: any }) {
  if (!p.connected || !(p.trades || []).length) {
    return (
      <Panel title={title || 'Review a recent trade'}>
        <div className="px-4 pb-4 pt-1 text-[13px] text-gray-600">
          Connect your brokerage and Finch will review your recent trades and suggest better alternatives.
          <button onClick={() => nav.navigateTo({ type: 'home' })} className="mt-3 block w-full rounded-lg bg-emerald-600 py-2 text-white text-[13px] font-semibold hover:bg-emerald-700 transition-colors">Connect brokerage</button>
        </div>
      </Panel>
    );
  }
  return (
    <Panel title={title || 'Review a recent trade'} muted="tap to critique">
      {(p.trades as Payload[]).map((t) => (
        <button key={t.id} onClick={() => nav.openChatWithPrompt(reviewPrompt(t))} className="w-full flex items-center justify-between px-4 py-2.5 border-t first:border-t-0 border-[color:var(--finch-border,rgba(0,0,0,.06))] hover:bg-stone-50 transition-colors">
          <span className="flex items-center gap-2 min-w-0">
            <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded ${t.side === 'BUY' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{t.side}</span>
            <span className="text-[13.5px] font-semibold text-gray-900" style={{ fontFamily: NUM }}>{t.symbol}</span>
            <span className="text-[12px] text-gray-400 truncate">{t.quantity} sh · {fmtDate(t.date)}</span>
          </span>
          <span className="flex items-center gap-1.5 flex-shrink-0"><span className="text-[13px] font-medium text-gray-600 tabular-nums" style={{ fontFamily: NUM }}>{money(t.amount)}</span><ChevronRight className="w-3.5 h-3.5 text-gray-300" /></span>
        </button>
      ))}
    </Panel>
  );
}

function Pulse({ p, title, nav }: { p: Payload; title?: string; nav: any }) {
  const cols: string[] = p.columns || [];
  const iSym = cols.indexOf('symbol'), iName = cols.indexOf('name'), iPrice = cols.indexOf('price'), iPct = cols.indexOf('change_pct');
  return (
    <Panel title={title || 'Market pulse'} muted="today">
      {(p.rows || []).map((r: any[], i: number) => {
        const pct = iPct >= 0 ? r[iPct] : null;
        return (
          <button key={i} onClick={() => nav.openStock(r[iSym])} className="w-full flex items-center gap-3 px-4 py-2.5 border-t first:border-t-0 border-[color:var(--finch-border,rgba(0,0,0,.06))] hover:bg-stone-50 transition-colors">
            <span className="text-[13.5px] font-semibold text-gray-900 w-14 text-left" style={{ fontFamily: NUM }}>{r[iSym]}</span>
            <span className="text-[12px] text-gray-400 flex-1 text-left truncate">{iName >= 0 ? r[iName] : ''}</span>
            <span className="text-[13.5px] font-semibold text-gray-900 tabular-nums" style={{ fontFamily: NUM }}>{iPrice >= 0 && r[iPrice] != null ? Number(r[iPrice]).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}</span>
            <span className={`text-[12px] font-semibold tabular-nums w-16 text-right ${(pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`} style={{ fontFamily: NUM }}>{pct == null ? '' : `${pct >= 0 ? '+' : ''}${Number(pct).toFixed(2)}%`}</span>
          </button>
        );
      })}
    </Panel>
  );
}

function News({ p, title, nav }: { p: Payload; title?: string; nav: any }) {
  return (
    <Panel title={title || 'Worth knowing'}>
      {(p.items || []).map((n: Payload, i: number) => (
        <button key={i} onClick={() => nav.openChatWithPrompt(`What's the story behind: "${n.title}"?`)} className="w-full text-left px-4 py-3 border-t first:border-t-0 border-[color:var(--finch-border,rgba(0,0,0,.06))] hover:bg-stone-50 transition-colors">
          <div className="text-[13px] font-semibold text-gray-900 leading-snug line-clamp-2">{n.title}</div>
          <div className="text-[11.5px] text-gray-400 mt-1">{[n.source, ago(n.published_at)].filter(Boolean).join(' · ')}</div>
        </button>
      ))}
    </Panel>
  );
}

function StatBlock({ p }: { p: Payload }) {
  const up = (p.delta_pct ?? 0) >= 0;
  return (
    <Panel>
      <div className="px-4 pb-4 pt-1">
        <div className="text-[12px] text-gray-500">{p.label}</div>
        <div className="text-[26px] font-semibold tabular-nums text-gray-900" style={{ fontFamily: NUM }}>{p.value != null ? Number(p.value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}</div>
        {p.delta_pct != null && <div className={`text-[13px] font-semibold tabular-nums ${up ? 'text-emerald-600' : 'text-rose-600'}`} style={{ fontFamily: NUM }}>{up ? '+' : ''}{Number(p.delta_pct).toFixed(2)}%</div>}
      </div>
    </Panel>
  );
}

function NavChip({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="inline-flex items-center gap-2 text-[12.5px] text-gray-600 border border-[color:var(--finch-border,rgba(0,0,0,.06))] bg-white rounded-[10px] px-3 py-2 hover:border-[color:var(--finch-border-strong,rgba(0,0,0,.12))] hover:text-gray-900 transition-colors">
      {icon}{label}
    </button>
  );
}
