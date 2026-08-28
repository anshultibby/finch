/**
 * Shared onboarding/profile field components (mobile) — the native mirror of
 * web's components/onboarding/instruments.tsx. Controlled bits driven by one
 * flat `Draft`, reused by the stepped GoalOnboarding wizard AND the editable
 * mission screen (app/mission.tsx). Keep the Draft shape + draftToRequest in
 * sync with web so both platforms persist identical profiles.
 */
import React from 'react';
import { View, Text, Pressable, TextInput } from 'react-native';
import SegmentedControl from '@/components/ui/SegmentedControl';
import type { Goal, GoalKind, SetGoalRequest } from '@/lib/api';

export const fmt = (n: number) => n.toLocaleString('en-US');

export type Draft = {
  kind: GoalKind;
  amt: number; days: number;
  yr: number; mo: number;
  income: number;
  risk: number;
  options: boolean | null;
  watch: string[];
  notify: 'app' | 'both' | 'email';
  experience: 'new' | 'some' | 'pro';
  constraints: string[];
  notes: string;
};

export const emptyDraft = (): Draft => ({
  kind: 'number', amt: 1000, days: 21, yr: 10, mo: 500, income: 300, risk: 6,
  options: null, watch: ['Big drops in my holdings', 'Earnings for what I own'],
  notify: 'both', experience: 'some', constraints: [], notes: '',
});

export const INTENTS: { kind: GoalKind; icon: string; title: string; sub: string }[] = [
  { kind: 'number', icon: '🎯', title: 'Hit a number', sub: 'A dollar target by a deadline' },
  { kind: 'grow', icon: '🌱', title: 'Grow long-term', sub: 'Steady, low-stress compounding' },
  { kind: 'income', icon: '💵', title: 'Monthly income', sub: 'Cash flow from what I hold' },
  { kind: 'protect', icon: '🛡️', title: 'Watch & protect', sub: 'Just keep an eye out, warn me' },
];
export const TIMEFRAMES: { label: string; days: number; word: string }[] = [
  { label: '1 wk', days: 7, word: 'this week' },
  { label: '3 wks', days: 21, word: '3 weeks' },
  { label: '1 mo', days: 30, word: 'a month' },
  { label: '3 mo', days: 90, word: '3 months' },
];
export const RISKS: { label: string; value: number; sub: string }[] = [
  { label: 'Careful', value: 3, sub: 'small size, ask first' },
  { label: 'Balanced', value: 6, sub: 'real swings, capped' },
  { label: 'Full send', value: 9, sub: 'size up, move fast' },
];
export const WATCH_OPTS = ['Big drops in my holdings', 'Earnings for what I own', 'Unusual options flow', 'My stop levels'];
export const CONSTRAINT_OPTS = ['No crypto', 'No options', 'ESG only', 'No penny stocks', 'US only'];

function daysFromNowISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export function draftToRequest(d: Draft): SetGoalRequest {
  const preferences = {
    watch: d.watch, notify: d.notify, experience: d.experience,
    constraints: d.constraints, notes: d.notes.trim(),
  };
  const base: Partial<SetGoalRequest> = {
    options_enabled: d.kind === 'number' ? !!d.options : false,
    risk: d.kind === 'protect' ? null : d.risk,
    preferences,
  };
  const tf = TIMEFRAMES.find(t => t.days === d.days) ?? TIMEFRAMES[1];
  switch (d.kind) {
    case 'number':
      return { kind: 'number', target_amount: d.amt, deadline: daysFromNowISO(d.days), title: `Make $${fmt(d.amt)} in ${tf.word}`, ...base };
    case 'grow':
      return { kind: 'grow', horizon_years: d.yr, monthly_contribution: d.mo, title: `Grow steadily over ${d.yr} years`, ...base };
    case 'income':
      return { kind: 'income', monthly_income: d.income, title: `Generate ~$${fmt(d.income)}/mo income`, ...base };
    case 'protect':
    default:
      return { kind: 'protect', title: 'Watch & protect my portfolio', config: { watch: d.watch, notify: d.notify }, ...base };
  }
}

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

// ── primitives ────────────────────────────────────────────────────────────────
export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} className={`px-4 py-2.5 rounded-full border ${selected ? 'bg-gray-900 border-gray-900' : 'bg-white border-black/10'}`}>
      <Text className={`text-sm font-body-medium ${selected ? 'text-white' : 'text-gray-600'}`}>{label}</Text>
    </Pressable>
  );
}
export function Stepper({ value, onDec, onInc, prefix, suffix }: { value: string; onDec: () => void; onInc: () => void; prefix?: string; suffix?: string }) {
  return (
    <View className="flex-row items-center justify-center gap-5 my-3">
      <Pressable onPress={onDec} className="w-11 h-11 rounded-full border border-black/10 bg-white items-center justify-center">
        <Text className="text-2xl text-gray-500">−</Text>
      </Pressable>
      <Text className="text-4xl font-body-bold text-gray-900" style={{ fontVariant: ['tabular-nums'] }}>
        {prefix}{value}<Text className="text-lg text-gray-400">{suffix}</Text>
      </Text>
      <Pressable onPress={onInc} className="w-11 h-11 rounded-full border border-black/10 bg-white items-center justify-center">
        <Text className="text-2xl text-gray-500">+</Text>
      </Pressable>
    </View>
  );
}
function Eyebrow({ children }: { children: string }) {
  return <Text className="text-[11px] font-body-medium text-emerald-700 uppercase mb-2" style={{ letterSpacing: 1 }}>◆ {children}</Text>;
}

// ── field groups ──────────────────────────────────────────────────────────────
export function IntentGrid({ value, onChange }: { value: GoalKind | null; onChange: (k: GoalKind) => void }) {
  return (
    <View className="gap-3">
      {INTENTS.map(it => (
        <Pressable key={it.kind} onPress={() => onChange(it.kind)}
          className={`flex-row items-center gap-3 p-4 rounded-2xl border bg-white ${value === it.kind ? 'border-emerald-500' : 'border-black/[0.06]'}`}>
          <Text className="text-2xl">{it.icon}</Text>
          <View className="flex-1">
            <Text className="text-[15px] font-body-bold text-gray-900">{it.title}</Text>
            <Text className="text-xs font-body text-gray-500">{it.sub}</Text>
          </View>
          <Text className="text-gray-300 text-lg">›</Text>
        </Pressable>
      ))}
    </View>
  );
}

export function NumberFields({ draft, set }: { draft: Draft; set: (p: Partial<Draft>) => void }) {
  if (draft.kind === 'number') {
    return (
      <View>
        <Text className="text-base font-body-medium text-gray-900 mb-2">How much, and by when?</Text>
        <Stepper value={fmt(draft.amt)} prefix="$" onDec={() => set({ amt: Math.max(200, draft.amt - 100) })} onInc={() => set({ amt: Math.min(50000, draft.amt + 100) })} />
        <View className="flex-row flex-wrap gap-2 justify-center mt-2">
          {TIMEFRAMES.map(t => <Chip key={t.days} label={t.label} selected={draft.days === t.days} onPress={() => set({ days: t.days })} />)}
        </View>
      </View>
    );
  }
  if (draft.kind === 'grow') {
    return (
      <View>
        <Text className="text-base font-body-medium text-gray-900 mb-2">Your horizon</Text>
        <Stepper value={String(draft.yr)} suffix=" yrs" onDec={() => set({ yr: Math.max(1, draft.yr - 1) })} onInc={() => set({ yr: Math.min(40, draft.yr + 1) })} />
        <Text className="text-sm font-body text-gray-500 text-center mt-4 mb-1">Contribute each month</Text>
        <Stepper value={fmt(draft.mo)} prefix="$" suffix="/mo" onDec={() => set({ mo: Math.max(0, draft.mo - 100) })} onInc={() => set({ mo: draft.mo + 100 })} />
      </View>
    );
  }
  if (draft.kind === 'income') {
    return (
      <View>
        <Text className="text-base font-body-medium text-gray-900 mb-2">How much income each month?</Text>
        <Stepper value={fmt(draft.income)} prefix="$" suffix="/mo" onDec={() => set({ income: Math.max(50, draft.income - 50) })} onInc={() => set({ income: Math.min(5000, draft.income + 50) })} />
        <Text className="text-sm font-body text-gray-500 text-center mt-2">≈ ${fmt(draft.income * 12)}/yr · covered calls &amp; dividends</Text>
      </View>
    );
  }
  // protect
  return (
    <View>
      <Text className="text-base font-body-medium text-gray-900 mb-3">What should I keep an eye on?</Text>
      <View className="flex-row flex-wrap gap-2">
        {WATCH_OPTS.map(w => (
          <Chip key={w} label={w} selected={draft.watch.includes(w)}
            onPress={() => set({ watch: draft.watch.includes(w) ? draft.watch.filter(x => x !== w) : [...draft.watch, w] })} />
        ))}
      </View>
    </View>
  );
}

export function RiskCards({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <View className="gap-2.5">
      {RISKS.map(r => (
        <Pressable key={r.value} onPress={() => onChange(r.value)}
          className={`p-4 rounded-2xl border bg-white ${value === r.value ? 'border-emerald-500' : 'border-black/[0.06]'}`}>
          <Text className="text-[15px] font-body-bold text-gray-900">{r.label}</Text>
          <Text className="text-xs font-body text-gray-500">{r.sub}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export function OptionsCards({ value, onChange }: { value: boolean | null; onChange: (v: boolean) => void }) {
  const opt = (v: boolean, title: string, sub: string) => (
    <Pressable onPress={() => onChange(v)} className={`flex-1 p-4 rounded-2xl border bg-white ${value === v ? 'border-emerald-500' : 'border-black/[0.06]'}`}>
      <Text className="text-[15px] font-body-bold text-gray-900">{title}</Text>
      <Text className="text-xs font-body text-gray-500 mt-0.5">{sub}</Text>
    </Pressable>
  );
  return <View className="flex-row gap-2.5">{opt(true, 'Use options', 'more range, capped')}{opt(false, 'Stocks only', 'keep it simple')}</View>;
}

export function PreferencesBlock({ draft, set }: { draft: Draft; set: (p: Partial<Draft>) => void }) {
  const toggle = (key: 'watch' | 'constraints', v: string) =>
    set({ [key]: draft[key].includes(v) ? draft[key].filter(x => x !== v) : [...draft[key], v] } as Partial<Draft>);
  return (
    <View className="gap-5">
      {draft.kind !== 'protect' && (
        <View>
          <Eyebrow>keep an eye on</Eyebrow>
          <View className="flex-row flex-wrap gap-2">
            {WATCH_OPTS.map(w => <Chip key={w} label={w} selected={draft.watch.includes(w)} onPress={() => toggle('watch', w)} />)}
          </View>
        </View>
      )}
      <View>
        <Eyebrow>how should I reach you</Eyebrow>
        <SegmentedControl options={['app', 'both', 'email']} selected={draft.notify}
          onChange={(v) => set({ notify: v as Draft['notify'] })} labels={{ app: 'App', both: 'App + email', email: 'Email' }} />
      </View>
      <View>
        <Eyebrow>how much investing have you done</Eyebrow>
        <SegmentedControl options={['new', 'some', 'pro']} selected={draft.experience}
          onChange={(v) => set({ experience: v as Draft['experience'] })} labels={{ new: 'New to it', some: 'Some', pro: 'A lot' }} />
      </View>
      <View>
        <Eyebrow>anything I should never do</Eyebrow>
        <View className="flex-row flex-wrap gap-2 mb-2.5">
          {CONSTRAINT_OPTS.map(c => <Chip key={c} label={c} selected={draft.constraints.includes(c)} onPress={() => toggle('constraints', c)} />)}
        </View>
        <TextInput value={draft.notes} onChangeText={(t) => set({ notes: t })} multiline
          placeholder="Anything else in your own words — e.g. 'keep 20% in cash'…" placeholderTextColor="#d1d5db"
          className="bg-white border border-black/10 rounded-xl px-3.5 py-3 text-sm font-body text-gray-900" style={{ minHeight: 64, textAlignVertical: 'top' }} />
      </View>
    </View>
  );
}
