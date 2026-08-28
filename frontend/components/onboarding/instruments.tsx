'use client';

/**
 * Shared onboarding/profile field components — the "instruments" (live dials +
 * projections) and small primitives, in Finch's design system (Tailwind on
 * emerald / stone / gray tokens, finch-surface, --font-numeric). All controlled:
 * they take a value + onChange so both the stepped ProfileWizard and the
 * Settings profile editor render identical inputs from the same draft state.
 */
import React from 'react';
import type { Goal, GoalKind, SetGoalRequest } from '@/lib/api';

export const fmt = (n: number) => n.toLocaleString('en-US');
export const numeric = { fontFamily: 'var(--font-numeric), sans-serif' } as const;

// ── the working draft (superset of SetGoalRequest, flat for easy editing) ──────
export type Draft = {
  kind: GoalKind | null;
  amt: number;      // number target ($)
  days: number;     // number deadline (days from now)
  yr: number;       // grow horizon (years)
  mo: number;       // grow monthly contribution ($)
  income: number;   // income target ($/mo)
  risk: number;     // 1..10
  options: boolean | null;
  watch: string[];
  notify: 'app' | 'both' | 'email';
  experience: 'new' | 'some' | 'pro';
  constraints: string[];
  notes: string;
};

export const emptyDraft = (): Draft => ({
  kind: null, amt: 1000, days: 21, yr: 10, mo: 500, income: 300, risk: 6,
  options: null, watch: ['big drops in my holdings', 'earnings for what I own'],
  notify: 'both', experience: 'some', constraints: [], notes: '',
});

export const WATCH_OPTS = ['big drops in my holdings', 'earnings for what I own', 'unusual options flow', 'my stop levels'];
export const CONSTRAINT_OPTS = ['no crypto', 'no options', 'ESG only', 'no penny stocks', 'US only'];

function daysFromNowISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

// Hydrate the flat editing draft from a stored Goal (for the Settings editor).
export function goalToDraft(g: Goal): Draft {
  const d = emptyDraft();
  const p = (g.preferences ?? {}) as Record<string, any>;
  let days = 21;
  if (g.deadline) {
    const diff = Math.round((new Date(g.deadline).getTime() - Date.now()) / 86_400_000);
    days = [7, 21, 30, 90].reduce((a, b) => Math.abs(b - diff) < Math.abs(a - diff) ? b : a, 21);
  }
  return {
    ...d,
    kind: g.kind,
    amt: g.target_amount ?? d.amt,
    days,
    yr: g.horizon_years ?? d.yr,
    mo: g.monthly_contribution ?? d.mo,
    income: g.monthly_income ?? d.income,
    risk: g.risk ?? d.risk,
    options: g.options_enabled ?? d.options,
    watch: Array.isArray(p.watch) ? p.watch : (g.config?.watch ?? d.watch),
    notify: p.notify ?? g.config?.notify ?? d.notify,
    experience: p.experience ?? d.experience,
    constraints: Array.isArray(p.constraints) ? p.constraints : d.constraints,
    notes: p.notes ?? '',
  };
}

// Convert the flat editing draft into the API payload the backend expects.
export function draftToRequest(d: Draft): SetGoalRequest {
  const kind = (d.kind ?? 'number') as GoalKind;
  const preferences = {
    watch: d.watch,
    notify: d.notify,
    experience: d.experience,
    constraints: d.constraints,
    notes: d.notes.trim(),
  };
  const base: SetGoalRequest = {
    kind,
    options_enabled: kind === 'number' ? !!d.options : false,
    risk: kind === 'protect' ? null : d.risk,
    preferences,
    config: {},
  };
  if (kind === 'number') {
    const lbl = d.days === 7 ? 'this week' : d.days === 21 ? '3 weeks' : d.days === 30 ? 'a month' : '3 months';
    return { ...base, target_amount: d.amt, deadline: daysFromNowISO(d.days), title: `Make $${fmt(d.amt)} in ${lbl}` };
  }
  if (kind === 'grow') {
    return { ...base, horizon_years: d.yr, monthly_contribution: d.mo, title: `Grow steadily over ${d.yr} years` };
  }
  if (kind === 'income') {
    return { ...base, monthly_income: d.income, title: `Generate ~$${fmt(d.income)}/mo income` };
  }
  return { ...base, config: { watch: d.watch, notify: d.notify }, title: 'Watch & protect my portfolio' };
}

// ── primitives ────────────────────────────────────────────────────────────────
export function Card({ children }: { children: React.ReactNode }) {
  return <div className="finch-surface rounded-2xl p-5">{children}</div>;
}
export function CardEyebrow({ children, live }: { children: React.ReactNode; live?: boolean }) {
  return (
    <div className="flex items-center justify-between mb-3.5">
      <span className="font-mono text-[10.5px] tracking-[0.14em] uppercase text-emerald-700">◆ {children}</span>
      {live && (
        <span className="font-mono text-[10px] uppercase tracking-wider text-stone-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> live
        </span>
      )}
    </div>
  );
}
function Stepper({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className="w-9 h-9 rounded-full border border-gray-200 bg-white text-stone-600 grid place-items-center text-xl leading-none hover:border-emerald-600 hover:text-emerald-700 transition-colors">
      {children}
    </button>
  );
}
function Range({ min, max, step = 1, value, onChange }: { min: number; max: number; step?: number; value: number; onChange: (v: number) => void }) {
  const fill = ((value - min) / (max - min)) * 100;
  return (
    <input type="range" min={min} max={max} step={step} value={value}
      onChange={e => onChange(+e.target.value)}
      className="w-full my-3 h-1.5 appearance-none cursor-pointer rounded-full [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-[22px] [&::-webkit-slider-thumb]:h-[22px] [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:shadow-[0_0_0_2px_#059669,0_4px_12px_-2px_rgba(5,150,105,.6)] [&::-moz-range-thumb]:w-[22px] [&::-moz-range-thumb]:h-[22px] [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-white [&::-moz-range-thumb]:shadow-[0_0_0_2px_#059669]"
      style={{ background: `linear-gradient(90deg,#059669 ${fill}%,rgba(20,18,16,.09) ${fill}%)` }} />
  );
}
export function Segmented<T extends string | number>({ value, onChange, options }: {
  value: T; onChange: (v: T) => void; options: readonly (readonly [T, string])[];
}) {
  return (
    <div className="flex gap-1 bg-stone-100 rounded-xl p-1">
      {options.map(([v, t]) => (
        <button type="button" key={String(v)} onClick={() => onChange(v)}
          className={`flex-1 text-xs font-semibold py-2 rounded-lg transition-colors ${
            value === v ? 'bg-white text-gray-900 shadow-sm' : 'text-stone-500 hover:text-stone-700'
          }`}>
          {t}
        </button>
      ))}
    </div>
  );
}
export function Chip({ children, selected, onClick }: { children: React.ReactNode; selected?: boolean; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className={`text-xs font-semibold px-3 py-2 rounded-full border transition-colors ${
        selected ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-stone-600 border-gray-200 hover:border-emerald-600 hover:text-emerald-700'
      }`}>
      {children}
    </button>
  );
}
function Readout({ children }: { children: React.ReactNode }) {
  return <div className="text-center text-[13px] text-stone-500 [&_b]:text-gray-900 [&_b]:font-semibold">{children}</div>;
}

// ── instruments (controlled) ───────────────────────────────────────────────────
const projPath = (bow: number) => { const my = 58 - (58 - 14) * bow * 0.55; return `M6 58 Q 160 ${my} 314 14`; };
function Projection({ id, bow }: { id: string; bow: number }) {
  const line = projPath(bow);
  return (
    <svg viewBox="0 0 320 66" preserveAspectRatio="none" className="w-full h-[60px] block my-2" aria-hidden>
      <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#10b981" stopOpacity=".28" /><stop offset="1" stopColor="#10b981" stopOpacity="0" /></linearGradient></defs>
      <path d={`${line} L 314 58 Z`} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke="#059669" strokeWidth={2.5} strokeLinecap="round" />
      <circle cx={314} cy={14} r={4} fill="#fff" stroke="#059669" strokeWidth={2.5} />
    </svg>
  );
}

export function TargetInstrument({ amt, days, onAmt, onDays }: { amt: number; days: number; onAmt: (v: number) => void; onDays: (v: number) => void }) {
  const per = Math.round(amt / days), pct = Math.round((amt / 5000) * 100);
  const lbl = days === 7 ? 'this week' : days === 21 ? '3 weeks' : days === 30 ? 'a month' : '3 months';
  return (
    <Card>
      <CardEyebrow live>your target</CardEyebrow>
      <div className="flex items-center justify-center gap-4 mb-1">
        <Stepper onClick={() => onAmt(Math.max(200, amt - 100))}>−</Stepper>
        <div className="text-[44px] font-semibold tracking-tight tabular-nums text-gray-900" style={numeric}>${fmt(amt)}</div>
        <Stepper onClick={() => onAmt(Math.min(5000, amt + 100))}>+</Stepper>
      </div>
      <Range min={200} max={5000} step={100} value={amt} onChange={onAmt} />
      <Segmented value={days} onChange={onDays} options={[[7, '1 wk'], [21, '3 wks'], [30, '1 mo'], [90, '3 mo']]} />
      <Projection id="gwpg-t" bow={0.5 + (amt / 5000) * 0.5} />
      <Readout>≈ <b>${per}/day</b> to hit <b>${fmt(amt)}</b> in {lbl} · a <b>{pct}%</b> run on ~$5k</Readout>
    </Card>
  );
}

export function HorizonInstrument({ yr, mo, onYr, onMo }: { yr: number; mo: number; onYr: (v: number) => void; onMo: (v: number) => void }) {
  const i = 0.0065, n = yr * 12;
  const fv = mo * ((Math.pow(1 + i, n) - 1) / i) + 5000 * Math.pow(1 + i, n);
  return (
    <Card>
      <CardEyebrow live>your horizon</CardEyebrow>
      <div className="flex items-center justify-center mb-1">
        <div className="text-[40px] font-semibold tracking-tight tabular-nums text-gray-900" style={numeric}>{yr} <span className="text-[19px] text-stone-400">years</span></div>
      </div>
      <Range min={1} max={30} value={yr} onChange={onYr} />
      <div className="flex items-center justify-center gap-3 my-3">
        <span className="text-[13px] text-stone-600">put in</span>
        <Stepper onClick={() => onMo(Math.max(0, mo - 100))}>−</Stepper>
        <div className="text-[22px] font-semibold tabular-nums text-gray-900" style={numeric}>${fmt(mo)}<span className="text-xs text-stone-400">/mo</span></div>
        <Stepper onClick={() => onMo(mo + 100)}>+</Stepper>
      </div>
      <Readout>≈ <b>${fmt(Math.round(fv / 1000))}k</b> in {yr} yrs at ~8%/yr · growth adds most of it</Readout>
    </Card>
  );
}

export function IncomeInstrument({ income, onIncome }: { income: number; onIncome: (v: number) => void }) {
  const yr = income * 12, pct = ((yr / 5000) * 100).toFixed(1);
  return (
    <Card>
      <CardEyebrow live>monthly income</CardEyebrow>
      <div className="flex items-center justify-center gap-4 mb-1">
        <Stepper onClick={() => onIncome(Math.max(50, income - 50))}>−</Stepper>
        <div className="text-[44px] font-semibold tracking-tight tabular-nums text-gray-900" style={numeric}>${fmt(income)}<span className="text-[17px] text-stone-400">/mo</span></div>
        <Stepper onClick={() => onIncome(Math.min(2000, income + 50))}>+</Stepper>
      </div>
      <Range min={50} max={2000} step={50} value={income} onChange={onIncome} />
      <div className="mt-4"><Readout>≈ <b>${fmt(yr)}/yr</b> · about <b>{pct}%</b> on ~$5k — covered calls &amp; dividends to get there</Readout></div>
    </Card>
  );
}

const RISK_DESC: Record<number, string> = {
  1: 'Featherweight — tiny positions, no options, I ask before I so much as sneeze.',
  2: 'Featherweight — tiny positions, no options, I ask before I so much as sneeze.',
  3: 'Cautious — small positions, nothing exotic without a heads-up.',
  4: 'Measured — steady entries, quick to take profits off the table.',
  5: 'Balanced — real positions, capped per name, I check in on the big calls.',
  6: 'Balanced — real positions, capped per name, I check in on the big calls.',
  7: 'Leaning aggressive — bigger size, faster triggers, still your call on every trade.',
  8: 'Aggressive — concentrated, options on, moving quickly.',
  9: 'Maximum conviction — big sizing, and you’ll hear what I did afterward. (You sure?)',
  10: 'Maximum conviction — big sizing, and you’ll hear what I did afterward. (You sure?)',
};
export function RiskInstrument({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <Card>
      <CardEyebrow live>how hard to push</CardEyebrow>
      <Range min={1} max={10} value={value} onChange={onChange} />
      <div className="flex justify-between text-[11px] text-stone-400 mx-0.5 mt-2 mb-3 font-mono">
        <span>careful</span><span>balanced</span><span>full send</span>
      </div>
      <div className="min-h-[40px]"><Readout>{RISK_DESC[value]}</Readout></div>
    </Card>
  );
}

// ── higher-level field groups reused by wizard + editor ────────────────────────
export function WatchPicker({ label, watch, onToggle }: { label: string; watch: string[]; onToggle: (w: string) => void }) {
  return (
    <Card>
      <div className="font-mono text-[10.5px] tracking-[0.14em] uppercase text-emerald-700 mb-3">◆ {label}</div>
      <div className="flex flex-wrap gap-2">
        {WATCH_OPTS.map(w => <Chip key={w} selected={watch.includes(w)} onClick={() => onToggle(w)}>{w}</Chip>)}
      </div>
    </Card>
  );
}

export function PreferencesFields({ draft, set }: { draft: Draft; set: (patch: Partial<Draft>) => void }) {
  const toggle = (key: 'watch' | 'constraints', v: string) =>
    set({ [key]: draft[key].includes(v) ? draft[key].filter(x => x !== v) : [...draft[key], v] } as Partial<Draft>);
  return (
    <div className="flex flex-col gap-3">
      {draft.kind !== 'protect' && (
        <WatchPicker label="keep an eye on" watch={draft.watch} onToggle={w => toggle('watch', w)} />
      )}
      <Card>
        <div className="font-mono text-[10.5px] tracking-[0.14em] uppercase text-emerald-700 mb-3">◆ how should I reach you</div>
        <Segmented value={draft.notify} onChange={v => set({ notify: v })} options={[['app', 'app'], ['both', 'app + email'], ['email', 'email']]} />
        <div className="font-mono text-[10.5px] tracking-[0.14em] uppercase text-emerald-700 mt-5 mb-3">◆ how much investing have you done</div>
        <Segmented value={draft.experience} onChange={v => set({ experience: v })} options={[['new', 'new to it'], ['some', 'some'], ['pro', 'a lot']]} />
      </Card>
      <Card>
        <div className="font-mono text-[10.5px] tracking-[0.14em] uppercase text-emerald-700 mb-3">◆ anything I should never do</div>
        <div className="flex flex-wrap gap-2 mb-3">
          {CONSTRAINT_OPTS.map(c => <Chip key={c} selected={draft.constraints.includes(c)} onClick={() => toggle('constraints', c)}>{c}</Chip>)}
        </div>
        <textarea rows={2} value={draft.notes} onChange={e => set({ notes: e.target.value })}
          placeholder="Anything else in your own words — e.g. 'keep 20% in cash', 'I hate meme stocks'…"
          className="w-full resize-none rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-emerald-500 transition-colors" />
      </Card>
    </div>
  );
}

// Renders the right numeric instrument for a kind, driven by the shared draft.
export function NumbersInstrument({ draft, set }: { draft: Draft; set: (patch: Partial<Draft>) => void }) {
  if (draft.kind === 'grow') return <HorizonInstrument yr={draft.yr} mo={draft.mo} onYr={yr => set({ yr })} onMo={mo => set({ mo })} />;
  if (draft.kind === 'income') return <IncomeInstrument income={draft.income} onIncome={income => set({ income })} />;
  if (draft.kind === 'protect') return <WatchPicker label="what should I watch" watch={draft.watch} onToggle={w => set({ watch: draft.watch.includes(w) ? draft.watch.filter(x => x !== w) : [...draft.watch, w] })} />;
  return <TargetInstrument amt={draft.amt} days={draft.days} onAmt={amt => set({ amt })} onDays={days => set({ days })} />;
}
