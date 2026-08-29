'use client';

/**
 * MeetFinch — a small, skippable card Finch presents to set your mission. Three
 * focused questions, capital-anchored so every number is real:
 *   1) how much you're starting with   (the anchor — everything scales off it)
 *   2) the plan   (aggressive / safe growth / income / watch)
 *   3) the horizon   (by-when for a target, or how-long for growth)
 * Then a grounded reveal (real projection from the capital) → "Let's go" persists
 * via goalApi.setGoal (starting_capital stored in config for the agent).
 * Skippable at any stage. One Finch mark (presenting the card). Finch's tokens.
 */
import React, { useState } from 'react';
import FinchLogo from '@/components/shared/FinchLogo';
import type { SetGoalRequest, GoalKind } from '@/lib/api';

const fmt = (n: number) => n.toLocaleString('en-US');
const numeric = { fontFamily: 'var(--font-numeric), sans-serif' } as const;
const daysFromNowISO = (days: number) => { const d = new Date(); d.setDate(d.getDate() + days); return d.toISOString().slice(0, 10); };

const CAPS = [1000, 5000, 10000, 25000, 50000, 100000];
const PLANS: { k: GoalKind; r: number | null; e: string; h: string; p: string }[] = [
  { k: 'number', r: 8, e: '🚀', h: 'Aggressive profits', p: 'Go for big gains, higher risk' },
  { k: 'grow', r: 4, e: '🌱', h: 'Safe growth', p: 'Steady, low-stress compounding' },
  { k: 'income', r: 5, e: '💵', h: 'Monthly income', p: 'Cash flow from what you hold' },
  { k: 'protect', r: null, e: '🛡️', h: 'Just watch', p: 'Monitor & warn, no trades' },
];
const AGG_TF: [number, string, number][] = [[30, 'This month', 0.12], [90, '3 months', 0.25], [365, 'This year', 0.6]];
const HORIZONS = [5, 10, 20, 30];

type StepKey = 'capital' | 'plan' | 'time' | 'reveal';
const LINE: Record<StepKey, string> = {
  capital: "First — how much are you starting with? Everything scales from this.",
  plan: "Nice. What are we doing with it?",
  time: "And what's the time horizon?",
  reveal: "Here's your mission. Real numbers, from your money.",
};

export default function MeetFinch({ onComplete, onSkip }: {
  onComplete: (g: SetGoalRequest) => void | Promise<void>;
  onSkip?: () => void;
}) {
  const [step, setStep] = useState(0);
  const [capital, setCapital] = useState(5000);
  const [kind, setKind] = useState<GoalKind | null>(null);
  const [risk, setRisk] = useState<number | null>(null);
  const [days, setDays] = useState(30);
  const [years, setYears] = useState(10);
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const steps: StepKey[] = ['capital', 'plan', ...((kind === 'number' || kind === 'grow') ? ['time' as StepKey] : []), 'reveal'];
  const key = steps[Math.min(step, steps.length - 1)];
  const canNext = key === 'plan' ? !!kind : true;
  const isReveal = key === 'reveal';
  const rate = (AGG_TF.find(t => t[0] === days) || AGG_TF[0])[2];

  const next = () => { if (step < steps.length - 1) setStep(step + 1); else finish(); };
  const back = () => setStep(Math.max(0, step - 1));

  const build = (): SetGoalRequest => {
    const config: Record<string, any> = { starting_capital: capital };
    const base: SetGoalRequest = { kind: kind!, risk, options_enabled: (risk ?? 0) >= 8, config, preferences: {} };
    if (kind === 'number') {
      const target = Math.round(capital * rate / 50) * 50;
      const tf = (AGG_TF.find(t => t[0] === days) || AGG_TF[0])[1].toLowerCase();
      return { ...base, target_amount: target, deadline: daysFromNowISO(days), title: `Turn $${fmt(capital)} into $${fmt(capital + target)} (${tf})` };
    }
    if (kind === 'grow') {
      const fv = Math.round(capital * Math.pow(1.08, years));
      return { ...base, options_enabled: false, horizon_years: years, title: `Grow $${fmt(capital)} to ~$${fmt(fv)} over ${years}y` };
    }
    if (kind === 'income') {
      const mo = Math.round(capital * 0.03 / 12);
      return { ...base, options_enabled: false, monthly_income: mo, title: `~$${fmt(mo)}/mo income from $${fmt(capital)}` };
    }
    return { ...base, risk: null, config: { ...config, watch: ['big drops in my holdings', 'earnings for what I own'], notify: 'both' }, title: `Watch & protect $${fmt(capital)}` };
  };

  const finish = async () => { setSaving(true); setDone(true); await onComplete(build()); };

  return (
    <div className="fixed inset-0 z-[60] flex flex-col items-center justify-center p-6"
      style={{ background: 'rgba(20,18,16,.16)', backdropFilter: 'blur(3px)' }}>
      <style>{`@keyframes fcHalo{0%,100%{transform:scale(1);opacity:.55}50%{transform:scale(1.13);opacity:.1}}@keyframes fcIn{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:none}}`}</style>

      {/* Finch, presenting */}
      <div className="flex flex-col items-center mb-0.5 z-[2]">
        <div className="relative rounded-[13px]" style={{ boxShadow: '0 16px 34px -14px rgba(5,150,105,.6)' }}>
          <FinchLogo size={46} />
          <span className="absolute -inset-[6px] rounded-[19px] border-[1.5px] border-emerald-500/40" style={{ animation: 'fcHalo 3s ease-in-out infinite' }} />
        </div>
        {!done && <p className="mt-3.5 text-[13.5px] text-stone-600 max-w-[320px] text-center leading-relaxed">{LINE[key]}</p>}
      </div>

      {/* the card */}
      <div className="w-full max-w-[400px] bg-white border border-black/[0.06] rounded-3xl p-[22px] relative z-[1]"
        style={{ boxShadow: '0 40px 90px -34px rgba(20,18,16,.55)', animation: 'fcIn .4s cubic-bezier(.2,.9,.25,1.04)' }}>
        {done ? (
          <div className="text-center py-4">
            <div className="text-[22px] font-semibold text-gray-900" style={numeric}>Mission set ✓</div>
            <div className="text-[12.5px] text-stone-500 mt-1">{saving ? 'Building your cockpit…' : ''}</div>
          </div>
        ) : (
          <>
            {onSkip && (
              <button type="button" onClick={onSkip} aria-label="Skip"
                className="absolute top-3.5 right-3.5 w-[30px] h-[30px] rounded-[9px] bg-stone-100 text-stone-400 grid place-items-center text-base hover:bg-stone-200 hover:text-gray-900 transition-colors">✕</button>
            )}
            <div className="flex gap-1.5 mb-3.5 pr-9">
              {steps.map((_, i) => (
                <span key={i} className={`h-[5px] rounded-full flex-1 transition-all ${i < step ? 'bg-emerald-400' : i === step ? 'bg-gray-900' : 'bg-stone-200'}`} />
              ))}
            </div>

            {key === 'capital' && <CapitalStep capital={capital} setCapital={setCapital} />}
            {key === 'plan' && <PlanStep kind={kind} onPick={(k, r) => { setKind(k); setRisk(r); }} />}
            {key === 'time' && (kind === 'number'
              ? <TimeStep title="By when?" hint="Aggressive means real swings — a shorter clock is punchier." options={AGG_TF.map(t => [t[0], t[1]] as [number, string])} value={days} onChange={setDays} />
              : <TimeStep title="For how long?" hint="Longer horizon — compounding does the work." options={HORIZONS.map(y => [y, `${y} yrs`] as [number, string])} value={years} onChange={setYears} />)}
            {key === 'reveal' && <Reveal kind={kind!} capital={capital} rate={rate} days={days} years={years} />}

            <div className="flex items-center gap-2.5 mt-[18px]">
              {step > 0 && <button type="button" onClick={back} className="text-[13px] font-semibold text-stone-400 hover:text-gray-900 transition-colors py-2">← Back</button>}
              <button type="button" onClick={next} disabled={!canNext}
                className={`ml-auto rounded-xl px-[22px] py-3 text-sm font-bold text-white transition-colors disabled:opacity-25 ${isReveal ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-gray-900 hover:bg-black'}`}>
                {isReveal ? "Let's go →" : 'Continue'}
              </button>
            </div>

            {!isReveal && onSkip && (
              <button type="button" onClick={onSkip} className="block mx-auto mt-3 text-xs text-stone-400 underline underline-offset-[3px] hover:text-gray-900 transition-colors">Skip setup for now</button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Q({ title, hint }: { title: string; hint: string }) {
  return (<><div className="text-[17px] font-semibold text-gray-900 tracking-[-0.01em] mb-0.5">{title}</div><p className="text-[12.5px] text-stone-400 mb-4 leading-snug">{hint}</p></>);
}

function CapitalStep({ capital, setCapital }: { capital: number; setCapital: (n: number) => void }) {
  return (
    <>
      <Q title="How much are you starting with?" hint="You can add more later. This anchors everything." />
      <div className="text-center text-[34px] font-semibold tracking-tight tabular-nums text-gray-900 mb-2.5" style={numeric}>${fmt(capital)}</div>
      <div className="grid grid-cols-3 gap-2">
        {CAPS.map(c => (
          <button type="button" key={c} onClick={() => setCapital(c)}
            className={`py-2.5 rounded-xl border-[1.5px] text-sm font-semibold transition-colors ${capital === c ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-900 border-gray-200 hover:border-emerald-600'}`}
            style={numeric}>${c >= 1000 ? `${c / 1000}k` : c}</button>
        ))}
      </div>
    </>
  );
}

function PlanStep({ kind, onPick }: { kind: GoalKind | null; onPick: (k: GoalKind, r: number | null) => void }) {
  return (
    <>
      <Q title="What's the plan?" hint="Pick one — it sets how I'll invest." />
      <div className="flex flex-col gap-2.5">
        {PLANS.map(pl => (
          <button type="button" key={pl.k} onClick={() => onPick(pl.k, pl.r)}
            className={`flex items-center gap-3 px-[15px] py-3.5 rounded-2xl border-[1.5px] text-left transition-all ${kind === pl.k ? 'border-emerald-600 bg-emerald-50/60' : 'border-gray-200 bg-white hover:border-emerald-500 hover:-translate-y-px'}`}>
            <span className="text-[22px]">{pl.e}</span>
            <span><span className="block text-[14.5px] font-bold text-gray-900">{pl.h}</span><span className="block text-[12.5px] text-stone-500">{pl.p}</span></span>
          </button>
        ))}
      </div>
    </>
  );
}

function TimeStep({ title, hint, options, value, onChange }: { title: string; hint: string; options: [number, string][]; value: number; onChange: (n: number) => void }) {
  return (
    <>
      <Q title={title} hint={hint} />
      <div className="flex gap-1.5 bg-stone-100 rounded-xl p-1">
        {options.map(([v, t]) => (
          <button type="button" key={v} onClick={() => onChange(v)}
            className={`flex-1 text-[13px] font-semibold py-2.5 rounded-lg transition-colors ${value === v ? 'bg-white text-gray-900 shadow-sm' : 'text-stone-500 hover:text-stone-700'}`}>{t}</button>
        ))}
      </div>
    </>
  );
}

function Reveal({ kind, capital, rate, days, years }: { kind: GoalKind; capital: number; rate: number; days: number; years: number }) {
  const eyebrow = (s: string) => <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-stone-400 mb-2">Your mission · {s}</div>;
  const stat = (v: React.ReactNode, delta?: React.ReactNode, flat?: boolean) => (
    <div className="flex items-baseline gap-2.5">
      <span className="text-[30px] font-semibold tracking-tight tabular-nums text-gray-900" style={numeric}>{v}</span>
      {delta != null && <span className={`text-sm font-semibold ${flat ? 'text-stone-400' : 'text-emerald-600'}`} style={numeric}>{delta}</span>}
    </div>
  );
  const sub = (c: React.ReactNode) => <p className="text-[12.5px] text-stone-600 mt-2 leading-relaxed [&_b]:text-gray-900 [&_b]:font-semibold">{c}</p>;

  if (kind === 'number') {
    const target = Math.round(capital * rate / 50) * 50, end = capital + target, pct = Math.round(rate * 100);
    const tf = (AGG_TF.find(t => t[0] === days) || AGG_TF[0])[1].toLowerCase();
    const per = Math.round(target / days);
    return <div>{eyebrow(tf)}{stat(`$${fmt(end)}`, `+$${fmt(target)} · ${pct}%`)}{sub(<>From your <b>${fmt(capital)}</b> — about <b style={numeric}>${fmt(per)}/day</b>. Aggressive means real swings; I size tight and bank profits.</>)}</div>;
  }
  if (kind === 'grow') {
    const fv = Math.round(capital * Math.pow(1.08, years)), gain = fv - capital, pct = Math.round(gain / capital * 100);
    const fill = Math.min(100, Math.round(capital / fv * 100));
    return (
      <div>
        {eyebrow(`${years} years`)}{stat(`$${fmt(fv)}`, `+$${fmt(gain)} · ${pct}%`)}
        {sub(<><b>${fmt(capital)}</b> compounding at ~8%/yr. Boring, and it works.</>)}
        <div className="mt-3.5 h-2 rounded-full bg-stone-200 overflow-hidden"><div className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400" style={{ width: `${fill}%` }} /></div>
        <div className="flex justify-between font-mono text-[11px] text-stone-400 mt-1.5"><span>${fmt(capital)} today</span><span>${fmt(fv)} in {years}y</span></div>
      </div>
    );
  }
  if (kind === 'income') {
    const mo = Math.round(capital * 0.03 / 12), modest = mo < 75;
    return <div>{eyebrow('monthly income')}{stat(<>${fmt(mo)}<span className="text-base text-stone-400">/mo</span></>)}{sub(<>Realistic on <b>${fmt(capital)}</b> at a safe ~3% yield.{modest ? ' Honestly modest — growing the base first gets you a lot more.' : ' Covered calls can nudge it higher.'}</>)}</div>;
  }
  return <div>{eyebrow('watch & protect')}{stat(`$${fmt(capital)}`, 'on watch', true)}{sub(<>I&apos;ll keep eyes on your book 24/7 and only ping you when it matters — big drops, earnings, unusual moves. No noise.</>)}</div>;
}
