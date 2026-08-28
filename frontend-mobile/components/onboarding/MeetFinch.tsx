/**
 * MeetFinch (mobile) — conversational, character-driven onboarding, the native
 * mirror of web's MeetFinch. You meet Finch, say what you want your money to do
 * (a tap or a line), Finch "thinks" (real LLM interpret), reacts with a specific
 * take, and reveals a live mission (counting-up target, nudgeable values).
 * "Let's go" persists via goalApi. Warm, alive, ~one choice. Replaces the old
 * stepped GoalOnboarding in the gate.
 */
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, TextInput, ScrollView, ActivityIndicator, Animated, Easing } from 'react-native';
import Svg, { Path, Circle } from 'react-native-svg';
import * as Haptics from 'expo-haptics';
import FinchLogo from '@/components/FinchLogo';
import { useAuth } from '@/contexts/AuthContext';
import { goalApi, type MissionDraft, type SetGoalRequest, type GoalKind } from '@/lib/api';

const EMERALD = '#059669';
const fmt = (n: number) => n.toLocaleString('en-US');
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

function useTyped(text: string, speed = 16) {
  const [n, setN] = useState(0);
  useEffect(() => {
    setN(0); let i = 0;
    const id = setInterval(() => { i++; setN(i); if (i >= text.length) clearInterval(id); }, speed);
    return () => clearInterval(id);
  }, [text]);
  return text.slice(0, n);
}
function useCountUp(target: number, run: boolean, dur = 800) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!run) { setV(target); return; }
    let raf = 0; const start = Date.now();
    const tick = () => { const p = Math.min(1, (Date.now() - start) / dur); setV(Math.round(target * (1 - Math.pow(1 - p, 3)))); if (p < 1) raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, run]);
  return v;
}

function Says({ children }: { children: React.ReactNode }) {
  return (
    <View className="flex-row gap-3 items-start mb-6">
      <View className="rounded-[11px] overflow-hidden"><FinchLogo size={38} /></View>
      <View className="flex-1">
        <Text className="font-body text-[10px] tracking-[1.4px] text-gray-400 mb-1.5" style={{ textTransform: 'uppercase' }}>Finch</Text>
        <Text className="font-body-bold text-gray-900 text-[25px]" style={{ lineHeight: 30, letterSpacing: -0.4 }}>{children}</Text>
      </View>
    </View>
  );
}
function Stepper({ onDec, onInc, children }: { onDec: () => void; onInc: () => void; children: React.ReactNode }) {
  const tap = (fn: () => void) => () => { Haptics.selectionAsync(); fn(); };
  return (
    <View className="flex-row items-center gap-3">
      <Pressable onPress={tap(onDec)} className="w-9 h-9 rounded-full border border-black/10 bg-white items-center justify-center"><Text className="text-xl text-gray-500">−</Text></Pressable>
      {children}
      <Pressable onPress={tap(onInc)} className="w-9 h-9 rounded-full border border-black/10 bg-white items-center justify-center"><Text className="text-xl text-gray-500">+</Text></Pressable>
    </View>
  );
}

export default function MeetFinch({ onDone, onSkip }: { onDone: (g: SetGoalRequest) => Promise<void> | void; onSkip?: () => void }) {
  const { user } = useAuth();
  const [phase, setPhase] = useState<'ask' | 'thinking' | 'reveal' | 'saving'>('ask');
  const [greeted, setGreeted] = useState(false);
  const [draft, setDraft] = useState<MissionDraft | null>(null);
  const [input, setInput] = useState('');
  const [amt, setAmt] = useState(1000);
  const [days, setDays] = useState(21);
  const [income, setIncome] = useState(300);
  const [years, setYears] = useState(10);

  const greeting = useTyped(greeted ? '' : "Hey — I'm Finch.");
  useEffect(() => { if (!greeted) { const t = setTimeout(() => setGreeted(true), 1300); return () => clearTimeout(t); } }, [greeted]);

  const submit = async (text: string) => {
    if (!text.trim() || phase !== 'ask') return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setPhase('thinking');
    let d: MissionDraft;
    try { d = user ? await goalApi.interpret(user.id, text) : fallbackDraft(text); } catch { d = fallbackDraft(text); }
    setDraft(d);
    if (d.target_amount) setAmt(d.target_amount);
    if (d.days) setDays(d.days);
    if (d.monthly_income) setIncome(d.monthly_income);
    if (d.horizon_years) setYears(d.horizon_years);
    setPhase('reveal');
  };

  const build = (): SetGoalRequest => {
    const d = draft!;
    const base: SetGoalRequest = { kind: d.kind, options_enabled: d.options_enabled, risk: d.risk ?? null, preferences: {}, config: {} };
    if (d.kind === 'number') return { ...base, target_amount: amt, deadline: daysFromNowISO(days), title: `Make $${fmt(amt)} in ${dayLabel(days)}` };
    if (d.kind === 'grow') return { ...base, horizon_years: years, options_enabled: false, title: `Grow steadily over ${years} years` };
    if (d.kind === 'income') return { ...base, monthly_income: income, title: `Generate ~$${fmt(income)}/mo income` };
    return { ...base, risk: null, title: 'Watch & protect my portfolio', config: { watch: ['big drops in my holdings', 'earnings for what I own'], notify: 'both' } };
  };
  const lockIn = async () => { if (draft) { setPhase('saving'); await onDone(build()); } };

  return (
    <View className="flex-1 bg-[#fbfbfa]">
      <View className="px-[22px] pt-16 flex-row items-center">
        <FinchLogo size={30} showText />
        {onSkip && <Pressable onPress={onSkip} className="ml-auto" hitSlop={10}><Text className="text-[12.5px] text-gray-400">Skip for now</Text></Pressable>}
      </View>

      <ScrollView contentContainerClassName="px-[22px] pt-10 pb-24 flex-grow justify-center" showsVerticalScrollIndicator={false}>
        {phase === 'ask' && (
          <View>
            <Says>{greeted ? 'What do you want your money to do?' : greeting}</Says>
            {greeted && (
              <View className="ml-[50px]">
                <Text className="text-[14.5px] text-gray-500 -mt-3 mb-4">Say it however — a number, a vibe, or “just don&apos;t lose it.”</Text>
                <View className="flex-row items-center gap-2.5 bg-white border-[1.5px] border-black/10 rounded-2xl pl-[18px] pr-1.5 py-1.5">
                  <TextInput value={input} onChangeText={setInput} placeholder="e.g. make $1k this month…" placeholderTextColor="#a8a29e"
                    className="flex-1 text-base text-gray-900 py-3" returnKeyType="go" onSubmitEditing={() => submit(input)} />
                  <Pressable onPress={() => submit(input)} disabled={!input.trim()}
                    className={`w-10 h-10 rounded-xl items-center justify-center ${input.trim() ? 'bg-gray-900' : 'bg-gray-300'}`}><Text className="text-white text-lg">↑</Text></Pressable>
                </View>
                <View className="flex-row flex-wrap gap-2.5 mt-3.5">
                  {CHIPS.map(c => (
                    <Pressable key={c.label} onPress={() => submit(c.text)}
                      className="flex-row items-center gap-2 bg-white border-[1.5px] border-black/10 rounded-2xl px-4 py-3">
                      <Text className="text-lg">{c.e}</Text><Text className="text-[14.5px] font-body-bold text-gray-900">{c.label}</Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            )}
          </View>
        )}

        {phase === 'thinking' && (
          <View>
            <Says>Give me a sec…</Says>
            <View className="ml-[50px]"><ActivityIndicator color={EMERALD} /></View>
          </View>
        )}

        {phase === 'reveal' && draft && (
          <View>
            <Reaction text={draft.reaction} />
            <View className="ml-[50px]">
              <Instrument kind={draft.kind} amt={amt} setAmt={setAmt} days={days} setDays={setDays} income={income} setIncome={setIncome} years={years} setYears={setYears} />
              {!!draft.stance && (
                <View className="items-center mt-3">
                  <Text className="text-xs text-gray-600 bg-stone-50 border border-black/10 px-3.5 py-1.5 rounded-full">{draft.stance}</Text>
                </View>
              )}
              <Pressable onPress={lockIn} className="mt-4 bg-emerald-600 rounded-2xl py-4 items-center">
                <Text className="text-white text-[15px] font-body-bold">Let&apos;s go →</Text>
              </Pressable>
              {onSkip && <Pressable onPress={onSkip} className="items-center mt-2 py-1"><Text className="text-[13px] text-gray-400">Not now</Text></Pressable>}
            </View>
          </View>
        )}

        {phase === 'saving' && (
          <View className="items-center py-10">
            <FinchLogo size={52} />
            <Text className="text-lg font-body-bold text-gray-900 mt-4">Mission set.</Text>
            <Text className="text-sm text-gray-500 mt-1">Building your cockpit…</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

function Reaction({ text }: { text: string }) {
  const shown = useTyped(text);
  return <Says>{shown}</Says>;
}

function Projection({ bow }: { bow: number }) {
  const my = 64 - (64 - 14) * bow;
  return (
    <Svg width="100%" height={70} viewBox="0 0 378 78" style={{ marginVertical: 6 }}>
      <Path d={`M6 64 Q 190 ${my - 8} 372 14`} stroke={EMERALD} strokeWidth={2.5} fill="none" strokeLinecap="round" />
      <Circle cx={372} cy={14} r={4} fill="#fff" stroke={EMERALD} strokeWidth={2.5} />
    </Svg>
  );
}

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View className="bg-white border border-black/[0.06] rounded-[20px] p-5">
      <View className="flex-row items-center justify-between mb-3.5">
        <Text className="font-body text-[10.5px] text-emerald-700" style={{ letterSpacing: 1.4, textTransform: 'uppercase' }}>{label}</Text>
        <Text className="font-body text-[10px] text-gray-400" style={{ textTransform: 'uppercase' }}>live</Text>
      </View>
      {children}
    </View>
  );
}

function Instrument(p: {
  kind: GoalKind; amt: number; setAmt: (n: number) => void; days: number; setDays: (n: number) => void;
  income: number; setIncome: (n: number) => void; years: number; setYears: (n: number) => void;
}) {
  const amtShown = useCountUp(p.amt, p.kind === 'number');
  const incShown = useCountUp(p.income, p.kind === 'income');
  if (p.kind === 'protect') {
    return <Card label="on watch"><Text className="text-[15px] text-gray-900 leading-6 py-1">I&apos;ll keep eyes on your book 24/7 and only ping you when it actually matters — big drops, earnings, unusual moves. No noise.</Text></Card>;
  }
  if (p.kind === 'grow') {
    const fv = Math.round(5000 * Math.pow(1.08, p.years) / 1000);
    return (
      <Card label="the long game">
        <Text className="text-center text-[48px] font-body-bold text-gray-900" style={{ fontVariant: ['tabular-nums'] }}>${fmt(fv)}k</Text>
        <Projection bow={0.7} />
        <View className="flex-row items-center justify-center gap-3 mt-2">
          <Text className="text-[13px] text-gray-500">over</Text>
          <Stepper onDec={() => p.setYears(Math.max(1, p.years - 1))} onInc={() => p.setYears(Math.min(30, p.years + 1))}>
            <Text className="text-[22px] font-body-bold text-gray-900 text-center" style={{ minWidth: 96, fontVariant: ['tabular-nums'] }}>{p.years} yrs</Text>
          </Stepper>
        </View>
        <Text className="text-center text-[13px] text-gray-500 mt-3">steady, low-stress, no hype</Text>
      </Card>
    );
  }
  if (p.kind === 'income') {
    return (
      <Card label="monthly income">
        <View className="flex-row items-center justify-center mb-1">
          <Stepper onDec={() => p.setIncome(Math.max(50, p.income - 50))} onInc={() => p.setIncome(Math.min(2000, p.income + 50))}>
            <Text className="text-[44px] font-body-bold text-gray-900" style={{ fontVariant: ['tabular-nums'] }}>${fmt(incShown)}<Text className="text-[18px] text-gray-400">/mo</Text></Text>
          </Stepper>
        </View>
        <Text className="text-center text-[13px] text-gray-500 mt-2">≈ ${fmt(p.income * 12)}/yr · covered calls &amp; dividends do the work</Text>
      </Card>
    );
  }
  const per = Math.round(p.amt / p.days);
  return (
    <Card label="the target">
      <View className="flex-row items-center justify-center mb-1">
        <Stepper onDec={() => p.setAmt(Math.max(200, p.amt - 100))} onInc={() => p.setAmt(Math.min(5000, p.amt + 100))}>
          <Text className="text-[46px] font-body-bold text-gray-900" style={{ fontVariant: ['tabular-nums'] }}>${fmt(amtShown)}</Text>
        </Stepper>
      </View>
      <View className="flex-row gap-1 bg-stone-100 rounded-xl p-1 my-3">
        {([[7, '1 wk'], [21, '3 wks'], [30, '1 mo'], [90, '3 mo']] as const).map(([d, t]) => (
          <Pressable key={d} onPress={() => p.setDays(d)} className={`flex-1 py-2 rounded-lg items-center ${p.days === d ? 'bg-white' : ''}`} style={p.days === d ? { shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 3, shadowOffset: { width: 0, height: 1 } } : undefined}>
            <Text className={`text-xs font-body-bold ${p.days === d ? 'text-gray-900' : 'text-gray-500'}`}>{t}</Text>
          </Pressable>
        ))}
      </View>
      <Projection bow={0.5 + (p.amt / 5000) * 0.5} />
      <Text className="text-center text-[13px] text-gray-500 mt-1">≈ ${per}/day to hit ${fmt(p.amt)} in {dayLabel(p.days)}. I&apos;ll pace you.</Text>
    </Card>
  );
}
