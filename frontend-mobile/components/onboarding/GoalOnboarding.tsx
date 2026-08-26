/**
 * GoalOnboarding (mobile) — a focused native version of the goal wizard. Not the
 * full generative-chat experience the web has yet, but a real, on-brand goal
 * capture across the same spectrum (number / grow / income / protect) that
 * persists via goalApi. Keep the shape in sync with web GoalWizard.
 */
import React, { useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import type { GoalKind, SetGoalRequest } from '@/lib/api';

const EMERALD = '#059669';

const fmt = (n: number) => n.toLocaleString('en-US');
function daysFromNowISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

const INTENTS: { kind: GoalKind; icon: string; title: string; sub: string }[] = [
  { kind: 'number', icon: '🚀', title: 'Make a number', sub: 'Hit a dollar target by a deadline' },
  { kind: 'grow', icon: '🌱', title: 'Grow long-term', sub: 'Steady, low-stress compounding' },
  { kind: 'income', icon: '💵', title: 'Monthly income', sub: 'Cash flow from what I hold' },
  { kind: 'protect', icon: '🛡️', title: 'Watch & protect', sub: 'Just keep an eye on things' },
];

const RISKS: { label: string; value: number; sub: string }[] = [
  { label: 'Careful', value: 3, sub: 'small size, ask first' },
  { label: 'Balanced', value: 6, sub: 'real swings, capped' },
  { label: 'Full send', value: 9, sub: 'size up, move fast' },
];

const WATCH_OPTS = ['Big drops in my holdings', 'Earnings for what I own', 'Unusual options flow', 'My stop levels'];

function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      className={`px-4 py-2.5 rounded-full border ${selected ? 'bg-gray-900 border-gray-900' : 'bg-white border-black/10'}`}
    >
      <Text className={`text-sm font-body-medium ${selected ? 'text-white' : 'text-gray-600'}`}>{label}</Text>
    </Pressable>
  );
}

function Stepper({ value, onDec, onInc, prefix, suffix }: { value: string; onDec: () => void; onInc: () => void; prefix?: string; suffix?: string }) {
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

const TIMEFRAMES: { label: string; days: number; word: string }[] = [
  { label: '1 wk', days: 7, word: 'this week' },
  { label: '3 wks', days: 21, word: '3 weeks' },
  { label: '1 mo', days: 30, word: 'a month' },
  { label: '3 mo', days: 90, word: '3 months' },
];

export default function GoalOnboarding({ onDone }: { onDone: (goal: SetGoalRequest) => Promise<void> | void }) {
  const [step, setStep] = useState(0);
  const [kind, setKind] = useState<GoalKind>('number');
  const [amt, setAmt] = useState(1000);
  const [days, setDays] = useState(21);
  const [years, setYears] = useState(10);
  const [monthly, setMonthly] = useState(500);
  const [income, setIncome] = useState(300);
  const [watch, setWatch] = useState<string[]>([WATCH_OPTS[0], WATCH_OPTS[1]]);
  const [risk, setRisk] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const hasRiskStep = kind !== 'protect';
  const lastStep = hasRiskStep ? 2 : 1;

  const build = (): SetGoalRequest => {
    const tf = TIMEFRAMES.find(t => t.days === days)!;
    switch (kind) {
      case 'number':
        return { kind, target_amount: amt, deadline: daysFromNowISO(days), risk: risk ?? 6, title: `Make $${fmt(amt)} in ${tf.word}` };
      case 'grow':
        return { kind, horizon_years: years, monthly_contribution: monthly, risk: risk ?? 4, title: `Grow steadily over ${years} years` };
      case 'income':
        return { kind, monthly_income: income, risk: risk ?? 4, title: `Generate ~$${fmt(income)}/mo income` };
      case 'protect':
      default:
        return { kind: 'protect', title: 'Watch & protect my portfolio', config: { watch, notify: 'both' } };
    }
  };

  const finish = async () => {
    setSaving(true);
    try { await onDone(build()); } finally { setSaving(false); }
  };

  const next = () => (step >= lastStep ? finish() : setStep(s => s + 1));

  return (
    <View className="flex-1 bg-[#fafaf9]">
      <ScrollView contentContainerClassName="px-6 pt-16 pb-32" showsVerticalScrollIndicator={false}>
        <View className="items-center mb-8">
          <View className="w-13 h-13 rounded-full mb-3" style={{ width: 52, height: 52, backgroundColor: EMERALD }} />
          <Text className="text-2xl font-body-bold text-gray-900">Let&apos;s set your mission</Text>
          <Text className="text-xs font-body text-gray-400 mt-1 tracking-widest">FINCH · ONBOARDING</Text>
        </View>

        {step === 0 && (
          <View className="gap-3">
            <Text className="text-base font-body-medium text-gray-900 mb-1">What are we doing with your money?</Text>
            {INTENTS.map(it => (
              <Pressable
                key={it.kind}
                onPress={() => { setKind(it.kind); setRisk(null); setStep(1); }}
                className={`flex-row items-center gap-3 p-4 rounded-2xl border bg-white ${kind === it.kind ? 'border-emerald-500' : 'border-black/[0.06]'}`}
              >
                <Text className="text-2xl">{it.icon}</Text>
                <View className="flex-1">
                  <Text className="text-[15px] font-body-bold text-gray-900">{it.title}</Text>
                  <Text className="text-xs font-body text-gray-500">{it.sub}</Text>
                </View>
                <Text className="text-gray-300 text-lg">›</Text>
              </Pressable>
            ))}
          </View>
        )}

        {step === 1 && kind === 'number' && (
          <View>
            <Text className="text-base font-body-medium text-gray-900 mb-2">How much, and by when?</Text>
            <Stepper value={fmt(amt)} prefix="$" onDec={() => setAmt(a => Math.max(200, a - 100))} onInc={() => setAmt(a => Math.min(50000, a + 100))} />
            <View className="flex-row flex-wrap gap-2 justify-center mt-2">
              {TIMEFRAMES.map(t => <Chip key={t.days} label={t.label} selected={days === t.days} onPress={() => setDays(t.days)} />)}
            </View>
          </View>
        )}
        {step === 1 && kind === 'grow' && (
          <View>
            <Text className="text-base font-body-medium text-gray-900 mb-2">Your horizon</Text>
            <Stepper value={String(years)} suffix=" yrs" onDec={() => setYears(y => Math.max(1, y - 1))} onInc={() => setYears(y => Math.min(40, y + 1))} />
            <Text className="text-sm font-body text-gray-500 text-center mt-4 mb-1">Contribute each month</Text>
            <Stepper value={fmt(monthly)} prefix="$" suffix="/mo" onDec={() => setMonthly(m => Math.max(0, m - 100))} onInc={() => setMonthly(m => m + 100)} />
          </View>
        )}
        {step === 1 && kind === 'income' && (
          <View>
            <Text className="text-base font-body-medium text-gray-900 mb-2">How much income each month?</Text>
            <Stepper value={fmt(income)} prefix="$" suffix="/mo" onDec={() => setIncome(v => Math.max(50, v - 50))} onInc={() => setIncome(v => Math.min(5000, v + 50))} />
            <Text className="text-sm font-body text-gray-500 text-center mt-2">≈ ${fmt(income * 12)}/yr · I&apos;d lean on covered calls &amp; dividends</Text>
          </View>
        )}
        {step === 1 && kind === 'protect' && (
          <View>
            <Text className="text-base font-body-medium text-gray-900 mb-3">What should I keep an eye on?</Text>
            <View className="flex-row flex-wrap gap-2">
              {WATCH_OPTS.map(w => (
                <Chip key={w} label={w} selected={watch.includes(w)}
                  onPress={() => setWatch(cur => cur.includes(w) ? cur.filter(x => x !== w) : [...cur, w])} />
              ))}
            </View>
          </View>
        )}

        {step === 2 && hasRiskStep && (
          <View>
            <Text className="text-base font-body-medium text-gray-900 mb-3">How hard should I push?</Text>
            <View className="gap-2.5">
              {RISKS.map(r => (
                <Pressable key={r.value} onPress={() => setRisk(r.value)}
                  className={`p-4 rounded-2xl border bg-white ${risk === r.value ? 'border-emerald-500' : 'border-black/[0.06]'}`}>
                  <Text className="text-[15px] font-body-bold text-gray-900">{r.label}</Text>
                  <Text className="text-xs font-body text-gray-500">{r.sub}</Text>
                </Pressable>
              ))}
            </View>
          </View>
        )}
      </ScrollView>

      {/* footer nav */}
      {step > 0 && (
        <View className="absolute bottom-0 left-0 right-0 px-6 pb-10 pt-3 bg-[#fafaf9] border-t border-black/[0.06] flex-row items-center gap-3">
          <Pressable onPress={() => setStep(s => Math.max(0, s - 1))} className="px-5 py-3.5">
            <Text className="text-sm font-body-medium text-gray-500">Back</Text>
          </Pressable>
          <View className="flex-1" />
          <Pressable
            onPress={next}
            disabled={saving || (step === 2 && hasRiskStep && risk == null)}
            className={`px-7 py-3.5 rounded-xl ${saving || (step === 2 && hasRiskStep && risk == null) ? 'bg-gray-300' : 'bg-gray-900'}`}
          >
            {saving
              ? <ActivityIndicator color="#fff" />
              : <Text className="text-sm font-body-bold text-white">{step >= lastStep ? 'Set my mission' : 'Continue'}</Text>}
          </Pressable>
        </View>
      )}
    </View>
  );
}
