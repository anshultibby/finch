/**
 * MeetFinch (mobile) — a small, skippable card Finch presents to set your
 * mission (native mirror of web). Three focused, capital-anchored questions:
 * how much you're starting with → the plan → the horizon → a grounded reveal
 * (real projection from the capital). "Let's go" persists via goalApi; skippable
 * at any stage. One Finch mark presenting the card.
 */
import React, { useState } from 'react';
import { View, Text, Pressable, ScrollView } from 'react-native';
import * as Haptics from 'expo-haptics';
import FinchLogo from '@/components/FinchLogo';
import type { SetGoalRequest, GoalKind } from '@/lib/api';

const fmt = (n: number) => n.toLocaleString('en-US');
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

export default function MeetFinch({ onDone, onSkip }: { onDone: (g: SetGoalRequest) => Promise<void> | void; onSkip?: () => void }) {
  const [step, setStep] = useState(0);
  const [capital, setCapital] = useState(5000);
  const [kind, setKind] = useState<GoalKind | null>(null);
  const [risk, setRisk] = useState<number | null>(null);
  const [days, setDays] = useState(30);
  const [years, setYears] = useState(10);
  const [done, setDone] = useState(false);

  const steps: StepKey[] = ['capital', 'plan', ...((kind === 'number' || kind === 'grow') ? ['time' as StepKey] : []), 'reveal'];
  const key = steps[Math.min(step, steps.length - 1)];
  const canNext = key === 'plan' ? !!kind : true;
  const isReveal = key === 'reveal';
  const rate = (AGG_TF.find(t => t[0] === days) || AGG_TF[0])[2];
  const tap = (fn: () => void) => () => { Haptics.selectionAsync(); fn(); };

  const build = (): SetGoalRequest => {
    const config: Record<string, any> = { starting_capital: capital };
    const base: SetGoalRequest = { kind: kind!, risk, options_enabled: (risk ?? 0) >= 8, config, preferences: {} };
    if (kind === 'number') {
      const target = Math.round(capital * rate / 50) * 50;
      const tf = (AGG_TF.find(t => t[0] === days) || AGG_TF[0])[1].toLowerCase();
      return { ...base, target_amount: target, deadline: daysFromNowISO(days), title: `Turn $${fmt(capital)} into $${fmt(capital + target)} (${tf})` };
    }
    if (kind === 'grow') { const fv = Math.round(capital * Math.pow(1.08, years)); return { ...base, options_enabled: false, horizon_years: years, title: `Grow $${fmt(capital)} to ~$${fmt(fv)} over ${years}y` }; }
    if (kind === 'income') { const mo = Math.round(capital * 0.03 / 12); return { ...base, options_enabled: false, monthly_income: mo, title: `~$${fmt(mo)}/mo income from $${fmt(capital)}` }; }
    return { ...base, risk: null, config: { ...config, watch: ['big drops in my holdings', 'earnings for what I own'], notify: 'both' }, title: `Watch & protect $${fmt(capital)}` };
  };

  const next = async () => {
    if (step < steps.length - 1) { Haptics.selectionAsync(); setStep(step + 1); }
    else { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium); setDone(true); await onDone(build()); }
  };
  const back = () => setStep(Math.max(0, step - 1));

  return (
    <View className="flex-1 items-center justify-center px-6" style={{ backgroundColor: 'rgba(20,18,16,0.28)' }}>
      {/* Finch, presenting */}
      <View className="items-center" style={{ marginBottom: 2, zIndex: 2 }}>
        <View className="rounded-[13px]" style={{ shadowColor: '#059669', shadowOpacity: 0.5, shadowRadius: 20, shadowOffset: { width: 0, height: 14 } }}><FinchLogo size={46} /></View>
        {!done && <Text className="mt-3.5 text-[13.5px] text-stone-100 text-center" style={{ maxWidth: 320, lineHeight: 20 }}>{LINE[key]}</Text>}
      </View>

      <View className="w-full bg-white rounded-3xl p-[22px]" style={{ maxWidth: 400, shadowColor: '#000', shadowOpacity: 0.25, shadowRadius: 40, shadowOffset: { width: 0, height: 24 } }}>
        {done ? (
          <View className="items-center py-4">
            <Text className="text-[22px] font-body-bold text-gray-900">Mission set ✓</Text>
            <Text className="text-[12.5px] text-stone-500 mt-1">Building your cockpit…</Text>
          </View>
        ) : (
          <>
            {onSkip && (
              <Pressable onPress={onSkip} hitSlop={8} className="absolute top-3.5 right-3.5 w-[30px] h-[30px] rounded-[9px] bg-stone-100 items-center justify-center z-10">
                <Text className="text-stone-400 text-base">✕</Text>
              </Pressable>
            )}
            <View className="flex-row gap-1.5 mb-4" style={{ paddingRight: 36 }}>
              {steps.map((_, i) => (
                <View key={i} className={`flex-1 rounded-full ${i < step ? 'bg-emerald-400' : i === step ? 'bg-gray-900' : 'bg-stone-200'}`} style={{ height: 5 }} />
              ))}
            </View>

            {key === 'capital' && <CapitalStep capital={capital} onPick={c => tap(() => setCapital(c))()} />}
            {key === 'plan' && <PlanStep kind={kind} onPick={(k, r) => tap(() => { setKind(k); setRisk(r); })()} />}
            {key === 'time' && (kind === 'number'
              ? <TimeStep title="By when?" hint="Aggressive means real swings — a shorter clock is punchier." options={AGG_TF.map(t => [t[0], t[1]] as [number, string])} value={days} onChange={v => tap(() => setDays(v))()} />
              : <TimeStep title="For how long?" hint="Longer horizon — compounding does the work." options={HORIZONS.map(y => [y, `${y} yrs`] as [number, string])} value={years} onChange={v => tap(() => setYears(v))()} />)}
            {key === 'reveal' && <Reveal kind={kind!} capital={capital} rate={rate} days={days} years={years} />}

            <View className="flex-row items-center gap-2.5 mt-[18px]">
              {step > 0 && <Pressable onPress={back} className="py-2"><Text className="text-[13px] font-body-bold text-stone-400">← Back</Text></Pressable>}
              <Pressable onPress={next} disabled={!canNext} className={`ml-auto rounded-xl px-[22px] py-3 ${!canNext ? 'bg-gray-300' : isReveal ? 'bg-emerald-600' : 'bg-gray-900'}`}>
                <Text className="text-sm font-body-bold text-white">{isReveal ? "Let's go →" : 'Continue'}</Text>
              </Pressable>
            </View>

            {!isReveal && onSkip && (
              <Pressable onPress={onSkip} className="items-center mt-3"><Text className="text-xs text-stone-400 underline">Skip setup for now</Text></Pressable>
            )}
          </>
        )}
      </View>
    </View>
  );
}

function Q({ title, hint }: { title: string; hint: string }) {
  return (<><Text className="text-[17px] font-body-bold text-gray-900 mb-0.5">{title}</Text><Text className="text-[12.5px] text-stone-400 mb-4" style={{ lineHeight: 17 }}>{hint}</Text></>);
}

function CapitalStep({ capital, onPick }: { capital: number; onPick: (n: number) => void }) {
  return (
    <>
      <Q title="How much are you starting with?" hint="You can add more later. This anchors everything." />
      <Text className="text-center text-[34px] font-body-bold text-gray-900 mb-2.5" style={{ fontVariant: ['tabular-nums'] }}>${fmt(capital)}</Text>
      <View className="flex-row flex-wrap" style={{ gap: 8 }}>
        {CAPS.map(c => (
          <Pressable key={c} onPress={() => onPick(c)} className={`rounded-xl border-[1.5px] items-center justify-center ${capital === c ? 'bg-gray-900 border-gray-900' : 'bg-white border-gray-200'}`} style={{ width: '31.5%', paddingVertical: 11 }}>
            <Text className={`text-sm font-body-bold ${capital === c ? 'text-white' : 'text-gray-900'}`}>${c >= 1000 ? `${c / 1000}k` : c}</Text>
          </Pressable>
        ))}
      </View>
    </>
  );
}

function PlanStep({ kind, onPick }: { kind: GoalKind | null; onPick: (k: GoalKind, r: number | null) => void }) {
  return (
    <>
      <Q title="What's the plan?" hint="Pick one — it sets how I'll invest." />
      <View style={{ gap: 10 }}>
        {PLANS.map(pl => (
          <Pressable key={pl.k} onPress={() => onPick(pl.k, pl.r)} className={`flex-row items-center gap-3 px-[15px] py-3.5 rounded-2xl border-[1.5px] ${kind === pl.k ? 'border-emerald-600 bg-emerald-50' : 'border-gray-200 bg-white'}`}>
            <Text className="text-[22px]">{pl.e}</Text>
            <View className="flex-1"><Text className="text-[14.5px] font-body-bold text-gray-900">{pl.h}</Text><Text className="text-[12.5px] text-stone-500">{pl.p}</Text></View>
          </Pressable>
        ))}
      </View>
    </>
  );
}

function TimeStep({ title, hint, options, value, onChange }: { title: string; hint: string; options: [number, string][]; value: number; onChange: (n: number) => void }) {
  return (
    <>
      <Q title={title} hint={hint} />
      <View className="flex-row bg-stone-100 rounded-xl p-1" style={{ gap: 6 }}>
        {options.map(([v, t]) => (
          <Pressable key={v} onPress={() => onChange(v)} className={`flex-1 py-2.5 rounded-lg items-center ${value === v ? 'bg-white' : ''}`} style={value === v ? { shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 3, shadowOffset: { width: 0, height: 1 } } : undefined}>
            <Text className={`text-[13px] font-body-bold ${value === v ? 'text-gray-900' : 'text-stone-500'}`}>{t}</Text>
          </Pressable>
        ))}
      </View>
    </>
  );
}

function Reveal({ kind, capital, rate, days, years }: { kind: GoalKind; capital: number; rate: number; days: number; years: number }) {
  const Eye = ({ s }: { s: string }) => <Text className="font-body text-[10px] text-stone-400 mb-2" style={{ letterSpacing: 1.4, textTransform: 'uppercase' }}>Your mission · {s}</Text>;
  const Stat = ({ v, delta, flat }: { v: string; delta?: string; flat?: boolean }) => (
    <View className="flex-row items-baseline" style={{ gap: 10 }}>
      <Text className="text-[30px] font-body-bold text-gray-900" style={{ fontVariant: ['tabular-nums'] }}>{v}</Text>
      {delta != null && <Text className={`text-sm font-body-bold ${flat ? 'text-stone-400' : 'text-emerald-600'}`}>{delta}</Text>}
    </View>
  );
  const Sub = ({ children }: { children: React.ReactNode }) => <Text className="text-[12.5px] text-stone-600 mt-2" style={{ lineHeight: 18 }}>{children}</Text>;

  if (kind === 'number') {
    const target = Math.round(capital * rate / 50) * 50, end = capital + target, pct = Math.round(rate * 100);
    const tf = (AGG_TF.find(t => t[0] === days) || AGG_TF[0])[1].toLowerCase(); const per = Math.round(target / days);
    return <View><Eye s={tf} /><Stat v={`$${fmt(end)}`} delta={`+$${fmt(target)} · ${pct}%`} /><Sub>From your ${fmt(capital)} — about ${fmt(per)}/day. Aggressive means real swings; I size tight and bank profits.</Sub></View>;
  }
  if (kind === 'grow') {
    const fv = Math.round(capital * Math.pow(1.08, years)), gain = fv - capital, pct = Math.round(gain / capital * 100), fill = Math.min(100, Math.round(capital / fv * 100));
    return (
      <View>
        <Eye s={`${years} years`} /><Stat v={`$${fmt(fv)}`} delta={`+$${fmt(gain)} · ${pct}%`} />
        <Sub>${fmt(capital)} compounding at ~8%/yr. Boring, and it works.</Sub>
        <View className="mt-3.5 rounded-full bg-stone-200 overflow-hidden" style={{ height: 8 }}><View className="h-full rounded-full bg-emerald-600" style={{ width: `${fill}%` }} /></View>
        <View className="flex-row justify-between mt-1.5"><Text className="text-[11px] text-stone-400">${fmt(capital)} today</Text><Text className="text-[11px] text-stone-400">${fmt(fv)} in {years}y</Text></View>
      </View>
    );
  }
  if (kind === 'income') {
    const mo = Math.round(capital * 0.03 / 12), modest = mo < 75;
    return <View><Eye s="monthly income" /><Stat v={`$${fmt(mo)}/mo`} /><Sub>Realistic on ${fmt(capital)} at a safe ~3% yield.{modest ? ' Honestly modest — growing the base first gets you a lot more.' : ' Covered calls can nudge it higher.'}</Sub></View>;
  }
  return <View><Eye s="watch & protect" /><Stat v={`$${fmt(capital)}`} delta="on watch" flat /><Sub>I'll keep eyes on your book 24/7 and only ping you when it matters — big drops, earnings, unusual moves. No noise.</Sub></View>;
}
