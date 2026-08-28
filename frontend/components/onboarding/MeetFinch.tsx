'use client';

/**
 * MeetFinch — the conversational, character-driven onboarding. You meet Finch,
 * say what you want your money to do (one line or a tap), Finch "thinks" (a real
 * LLM interprets it), then reacts with a specific analyst take and reveals a live
 * mission — a counting-up target, a drawing projection, values you can nudge.
 * "Let's go" persists the mission via goalApi.setGoal. Warm, alive, ~one choice.
 *
 * Design: Finch's own tokens (emerald/stone, DM Sans + Space Grotesk numeric),
 * the real FinchLogo mark. Replaces the old stepped ProfileWizard.
 */
import React, { useEffect, useRef, useState } from 'react';
import FinchLogo from '@/components/shared/FinchLogo';
import { useAuth } from '@/contexts/AuthContext';
import { goalApi, type MissionDraft, type SetGoalRequest, type GoalKind } from '@/lib/api';

const fmt = (n: number) => n.toLocaleString('en-US');
const numeric = { fontFamily: 'var(--font-numeric), sans-serif' } as const;
const dayLabel = (d: number) => (d === 7 ? 'this week' : d === 21 ? '3 weeks' : d === 30 ? 'a month' : '3 months');
const daysFromNowISO = (days: number) => { const d = new Date(); d.setDate(d.getDate() + days); return d.toISOString().slice(0, 10); };

const CHIPS: { e: string; label: string; text: string }[] = [
  { e: '🚀', label: 'Aggressive profits', text: 'go aggressive for big profits, I can handle the risk' },
  { e: '🌱', label: 'Safe growth', text: 'grow my savings safely and steadily' },
  { e: '💵', label: 'Monthly income', text: 'generate steady monthly income' },
  { e: '🛡️', label: 'Just watch my back', text: 'just watch my portfolio and warn me' },
];

function fallbackDraft(text: string): MissionDraft {
  const s = text.toLowerCase();
  if (/watch|monitor|protect|warn|keep an eye|don.?t lose|back/.test(s))
    return { kind: 'protect', options_enabled: false, risk: null, title: 'Watch & protect my portfolio', stance: 'alerts only · no trades without you', reaction: "Smoke detector, not arsonist. I'll watch, you sleep." };
  if (/income|monthly|cash ?flow|dividend|passive/.test(s))
    return { kind: 'income', monthly_income: 300, options_enabled: true, risk: 5, title: 'Generate ~$300/mo income', stance: 'conservative · covered calls + dividends', reaction: "Cash flow mode. Let's get you paid." };
  if (/grow|long|steady|slow|safe|retire|years|wealth/.test(s))
    return { kind: 'grow', horizon_years: 10, options_enabled: false, risk: 4, title: 'Grow steadily over 10 years', stance: 'low-stress · diversified', reaction: 'The boring plan. My favorite. This is how real money gets made.' };
  return { kind: 'number', target_amount: 1000, days: 21, options_enabled: true, risk: 7, title: 'Make $1,000 in 3 weeks', stance: 'full send · stocks + options', reaction: 'A target. My favorite kind of problem. Ambitious — not delusional.' };
}

// ── typing effect ──────────────────────────────────────────────────────────────
function Typed({ text, className, speed = 16, onDone }: { text: string; className?: string; speed?: number; onDone?: () => void }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    setN(0);
    let i = 0;
    const id = setInterval(() => {
      i++; setN(i);
      if (i >= text.length) { clearInterval(id); onDone?.(); }
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]); // eslint-disable-line react-hooks/exhaustive-deps
  return <span className={className}>{text.slice(0, n)}</span>;
}

function useCountUp(target: number, run: boolean, dur = 800) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!run) return;
    let raf = 0; const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur); const e = 1 - Math.pow(1 - p, 3);
      setV(Math.round(target * e));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, run, dur]);
  return v;
}

function Says({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-3 items-start mb-6 animate-[popin_0.45s_cubic-bezier(0.2,0.9,0.25,1.04)]">
      <div className="relative flex-none">
        <FinchLogo size={38} />
        <span className="absolute -inset-[5px] rounded-[15px] border-[1.5px] border-emerald-500/30 animate-[halo_3s_ease-in-out_infinite]" />
      </div>
      <div>
        <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-stone-400 mb-1.5">Finch</div>
        <div className="font-semibold text-gray-900 text-[27px] leading-[1.2] tracking-tight" style={numeric}>{children}</div>
      </div>
    </div>
  );
}

function Stepper({ onDec, onInc, children }: { onDec: () => void; onInc: () => void; children: React.ReactNode }) {
  return (
    <div className="inline-flex items-center gap-3">
      <button type="button" onClick={onDec} className="w-8 h-8 rounded-full border border-gray-200 bg-white text-stone-500 grid place-items-center text-lg leading-none hover:border-emerald-600 hover:text-emerald-700 transition-colors">−</button>
      {children}
      <button type="button" onClick={onInc} className="w-8 h-8 rounded-full border border-gray-200 bg-white text-stone-500 grid place-items-center text-lg leading-none hover:border-emerald-600 hover:text-emerald-700 transition-colors">+</button>
    </div>
  );
}

export default function MeetFinch({ onComplete, onSkip }: {
  onComplete: (g: SetGoalRequest) => void | Promise<void>;
  onSkip?: () => void;
}) {
  const { user } = useAuth();
  const [phase, setPhase] = useState<'ask' | 'thinking' | 'reveal' | 'saving'>('ask');
  const [draft, setDraft] = useState<MissionDraft | null>(null);
  const [input, setInput] = useState('');
  const [amt, setAmt] = useState(1000);
  const [days, setDays] = useState(21);
  const [income, setIncome] = useState(300);
  const [years, setYears] = useState(10);
  const [reactionDone, setReactionDone] = useState(false);
  const askedRef = useRef(false);

  const submit = async (text: string) => {
    if (!text.trim() || phase !== 'ask') return;
    setPhase('thinking');
    let d: MissionDraft;
    try { d = user ? await goalApi.interpret(user.id, text) : fallbackDraft(text); }
    catch { d = fallbackDraft(text); }
    setDraft(d);
    if (d.target_amount) setAmt(d.target_amount);
    if (d.days) setDays(d.days);
    if (d.monthly_income) setIncome(d.monthly_income);
    if (d.horizon_years) setYears(d.horizon_years);
    setReactionDone(false);
    setPhase('reveal');
  };

  const buildRequest = (): SetGoalRequest => {
    const d = draft!;
    const base: SetGoalRequest = { kind: d.kind, options_enabled: d.options_enabled, risk: d.risk ?? null, preferences: {}, config: {} };
    if (d.kind === 'number') return { ...base, target_amount: amt, deadline: daysFromNowISO(days), title: `Make $${fmt(amt)} in ${dayLabel(days)}` };
    if (d.kind === 'grow') return { ...base, horizon_years: years, title: `Grow steadily over ${years} years`, options_enabled: false };
    if (d.kind === 'income') return { ...base, monthly_income: income, title: `Generate ~$${fmt(income)}/mo income` };
    return { ...base, risk: null, title: 'Watch & protect my portfolio', config: { watch: ['big drops in my holdings', 'earnings for what I own'], notify: 'both' } };
  };

  const lockIn = async () => { if (draft) { setPhase('saving'); await onComplete(buildRequest()); } };

  return (
    <div className="fixed inset-0 z-[60] overflow-y-auto"
      style={{ background: 'radial-gradient(900px 500px at 80% -10%, #eafaf1, transparent), radial-gradient(700px 400px at 5% 110%, #f2effa, transparent), #fbfbfa' }}>
      <style>{`@keyframes popin{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}@keyframes halo{0%,100%{transform:scale(1);opacity:.55}50%{transform:scale(1.12);opacity:.1}}@keyframes draw{to{stroke-dashoffset:0}}@keyframes blink{0%,60%,100%{opacity:.28;transform:translateY(0)}30%{opacity:1;transform:translateY(-4px)}}`}</style>

      {/* brand bar */}
      <div className="max-w-[600px] mx-auto px-[22px] pt-[22px] flex items-center gap-2.5">
        <FinchLogo size={30} showText />
        {onSkip && <button type="button" onClick={onSkip} className="ml-auto text-[12.5px] text-stone-400 hover:text-gray-900 transition-colors">Skip for now</button>}
      </div>

      <div className="max-w-[600px] mx-auto px-[22px] min-h-[calc(100vh-70px)] flex flex-col justify-center py-10">
        {phase === 'ask' && <AskStep input={input} setInput={setInput} onSubmit={submit} />}

        {phase === 'thinking' && (
          <>
            <Says>Give me a sec…</Says>
            <div className="ml-[50px] inline-flex gap-1.5 py-1.5">
              {[0, 1, 2].map(i => <span key={i} className="w-2 h-2 rounded-full bg-emerald-400" style={{ animation: `blink 1.1s ${i * 0.16}s infinite` }} />)}
            </div>
          </>
        )}

        {phase === 'reveal' && draft && (
          <>
            <Says><Typed text={draft.reaction} onDone={() => setReactionDone(true)} /></Says>
            <div className="ml-[50px] animate-[popin_0.5s_cubic-bezier(0.2,0.9,0.25,1.04)]">
              <Instrument kind={draft.kind} amt={amt} setAmt={setAmt} days={days} setDays={setDays} income={income} setIncome={setIncome} years={years} setYears={setYears} />
              <MissionTag kind={draft.kind} stance={draft.stance} />
              <div className={`flex items-center gap-3 mt-4 transition-opacity duration-500 ${reactionDone ? 'opacity-100' : 'opacity-0'}`}>
                <button type="button" onClick={lockIn}
                  className="flex-1 bg-emerald-600 text-white rounded-2xl py-4 text-[15px] font-bold hover:bg-emerald-700 transition-colors shadow-[0_16px_32px_-16px_rgba(5,150,105,0.7)]">
                  Let&apos;s go →
                </button>
                {onSkip && <button type="button" onClick={onSkip} className="text-[13px] text-stone-400 hover:text-gray-900 transition-colors px-2">Not now</button>}
              </div>
            </div>
          </>
        )}

        {phase === 'saving' && (
          <div className="text-center py-10">
            <div className="inline-block"><FinchLogo size={52} /></div>
            <div className="text-lg font-semibold text-gray-900 mt-4" style={numeric}>Mission set.</div>
            <div className="text-sm text-stone-500 mt-1">Building your cockpit…</div>
          </div>
        )}
      </div>
    </div>
  );
}

function AskStep({ input, setInput, onSubmit }: { input: string; setInput: (v: string) => void; onSubmit: (t: string) => void }) {
  const [greeted, setGreeted] = useState(false);
  return (
    <>
      <Says>
        {greeted
          ? 'What do you want your money to do?'
          : <Typed text="Hey — I'm Finch." onDone={() => setTimeout(() => setGreeted(true), 350)} />}
      </Says>
      {greeted && (
        <div className="ml-[50px] animate-[popin_0.45s_ease]">
          <p className="text-[14.5px] text-stone-500 -mt-3 mb-4">Say it however — a number, a vibe, or “just don&apos;t lose it.”</p>
          <div className="flex items-center gap-2.5 bg-white border-[1.5px] border-gray-200 rounded-2xl pl-[18px] pr-1.5 py-1.5 focus-within:border-emerald-600 focus-within:shadow-[0_0_0_4px_rgba(5,150,105,0.08)] transition-all">
            <input value={input} onChange={e => setInput(e.target.value)} autoFocus
              onKeyDown={e => { if (e.key === 'Enter' && input.trim()) onSubmit(input.trim()); }}
              placeholder="e.g. make $1k this month…"
              className="flex-1 bg-transparent outline-none text-base text-gray-900 py-3 placeholder:text-stone-400" />
            <button type="button" disabled={!input.trim()} onClick={() => input.trim() && onSubmit(input.trim())}
              className="w-10 h-10 rounded-xl bg-gray-900 text-white grid place-items-center text-lg disabled:opacity-25 hover:bg-black transition-colors">↑</button>
          </div>
          <div className="flex flex-wrap gap-2.5 mt-3.5">
            {CHIPS.map(c => (
              <button type="button" key={c.label} onClick={() => onSubmit(c.text)}
                className="flex items-center gap-2.5 text-[14.5px] font-semibold text-gray-900 bg-white border-[1.5px] border-gray-200 rounded-2xl px-4 py-3 hover:border-emerald-600 hover:text-emerald-700 hover:-translate-y-0.5 transition-all">
                <span className="text-lg">{c.e}</span>{c.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="relative bg-white border border-[color:var(--finch-border,rgba(0,0,0,.06))] rounded-[20px] p-5 shadow-[0_24px_60px_-34px_rgba(20,18,16,0.5)] overflow-hidden">
      <span className="absolute left-0 right-0 top-0 h-0.5 bg-gradient-to-r from-transparent via-emerald-400 to-transparent" />
      <div className="flex items-center justify-between mb-3.5">
        <span className="font-mono text-[10.5px] tracking-[0.14em] uppercase text-emerald-700">{label}</span>
        <span className="font-mono text-[10px] uppercase text-stone-400 flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />live</span>
      </div>
      {children}
    </div>
  );
}

function Projection({ bow }: { bow: number }) {
  const my = 64 - (64 - 14) * bow;
  const d = `M6 64 Q 190 ${my - 8} 372 14`;
  return (
    <svg viewBox="0 0 378 78" preserveAspectRatio="none" className="w-full h-[80px] block my-1.5">
      <path d={d} fill="none" stroke="#059669" strokeWidth={2.5} strokeLinecap="round"
        style={{ strokeDasharray: 1, strokeDashoffset: 1, animation: 'draw 1.1s 0.15s ease forwards' }} pathLength={1} />
      <circle cx={372} cy={14} r={4} fill="#fff" stroke="#059669" strokeWidth={2.5} />
    </svg>
  );
}

function Instrument(p: {
  kind: GoalKind; amt: number; setAmt: (n: number) => void; days: number; setDays: (n: number) => void;
  income: number; setIncome: (n: number) => void; years: number; setYears: (n: number) => void;
}) {
  const amtShown = useCountUp(p.amt, p.kind === 'number' || p.kind === 'income');
  if (p.kind === 'protect') {
    return <Card label="on watch"><p className="text-[15px] text-gray-900 leading-relaxed py-1">I&apos;ll keep eyes on your book 24/7 and only ping you when it actually matters — big drops, earnings, unusual moves. No noise.</p></Card>;
  }
  if (p.kind === 'grow') {
    const fv = Math.round(5000 * Math.pow(1.08, p.years) / 1000);
    return (
      <Card label="the long game">
        <div className="text-center text-[52px] font-semibold tracking-tight tabular-nums text-gray-900" style={numeric}>${fmt(fv)}k</div>
        <Projection bow={0.7} />
        <div className="flex items-center justify-center gap-3 mt-2">
          <span className="text-[13px] text-stone-500">over</span>
          <Stepper onDec={() => p.setYears(Math.max(1, p.years - 1))} onInc={() => p.setYears(Math.min(30, p.years + 1))}>
            <span className="text-[22px] font-semibold tabular-nums text-gray-900 min-w-[92px] text-center" style={numeric}>{p.years} years</span>
          </Stepper>
        </div>
        <p className="text-center text-[13px] text-stone-500 mt-3">steady, low-stress, no hype</p>
      </Card>
    );
  }
  if (p.kind === 'income') {
    return (
      <Card label="monthly income">
        <div className="flex items-center justify-center gap-3 mb-1">
          <Stepper onDec={() => p.setIncome(Math.max(50, p.income - 50))} onInc={() => p.setIncome(Math.min(2000, p.income + 50))}>
            <span className="text-[48px] font-semibold tracking-tight tabular-nums text-gray-900" style={numeric}>${fmt(amtShown)}<span className="text-[20px] text-stone-400">/mo</span></span>
          </Stepper>
        </div>
        <p className="text-center text-[13px] text-stone-500 mt-2">≈ <b className="text-gray-900" style={numeric}>${fmt(p.income * 12)}/yr</b> · covered calls &amp; dividends do the work</p>
      </Card>
    );
  }
  // number
  const per = Math.round(p.amt / p.days);
  return (
    <Card label="the target">
      <div className="flex items-center justify-center gap-3 mb-1">
        <Stepper onDec={() => p.setAmt(Math.max(200, p.amt - 100))} onInc={() => p.setAmt(Math.min(5000, p.amt + 100))}>
          <span className="text-[52px] font-semibold tracking-tight tabular-nums text-gray-900" style={numeric}>${fmt(amtShown)}</span>
        </Stepper>
      </div>
      <div className="flex gap-1 bg-stone-100 rounded-xl p-1 my-3 max-w-[320px] mx-auto">
        {[[7, '1 wk'], [21, '3 wks'], [30, '1 mo'], [90, '3 mo']].map(([d, t]) => (
          <button type="button" key={d} onClick={() => p.setDays(d as number)}
            className={`flex-1 text-xs font-semibold py-2 rounded-lg transition-colors ${p.days === d ? 'bg-white text-gray-900 shadow-sm' : 'text-stone-500'}`}>{t}</button>
        ))}
      </div>
      <Projection bow={0.5 + (p.amt / 5000) * 0.5} />
      <p className="text-center text-[13px] text-stone-500 mt-1">≈ <b className="text-gray-900" style={numeric}>${per}/day</b> to hit <b className="text-gray-900" style={numeric}>${fmt(p.amt)}</b> in {dayLabel(p.days)}. I&apos;ll pace you.</p>
    </Card>
  );
}

function MissionTag({ kind, stance }: { kind: GoalKind; stance: string }) {
  if (!stance) return null;
  return (
    <div className="mt-3 flex justify-center">
      <span className="inline-flex items-center gap-2 text-xs text-stone-600 bg-stone-50 border border-gray-200 px-3.5 py-1.5 rounded-full">{stance}</span>
    </div>
  );
}
