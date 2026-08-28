/**
 * GoalOnboarding (mobile) — traditional stepped goal/profile capture, the native
 * mirror of web's ProfileWizard. Explicit kind picker → numbers → risk → options
 * → preferences, across the same spectrum (number / grow / income / protect),
 * persisted via goalApi (with the shared `preferences` bag). `onSkip` lets the
 * user in without a profile (soft gate). Field components live in ./fields.
 */
import React, { useMemo, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import type { SetGoalRequest } from '@/lib/api';
import {
  Draft, emptyDraft, draftToRequest,
  IntentGrid, NumberFields, RiskCards, OptionsCards, PreferencesBlock,
} from './fields';

const EMERALD = '#059669';
type StepKey = 'kind' | 'numbers' | 'risk' | 'options' | 'prefs';

const HEADING: Record<StepKey, string> = {
  kind: 'What are we doing with your money?',
  numbers: 'The numbers',
  risk: 'How hard should I push?',
  options: 'Options too, or stocks only?',
  prefs: 'A bit about you',
};

function stepsFor(kind: Draft['kind'], picked: boolean): StepKey[] {
  const s: StepKey[] = ['kind'];
  if (!picked) return s;
  s.push('numbers');
  if (kind !== 'protect') s.push('risk');
  if (kind === 'number') s.push('options');
  s.push('prefs');
  return s;
}

export default function GoalOnboarding({ onDone, onSkip }: {
  onDone: (goal: SetGoalRequest) => Promise<void> | void;
  onSkip?: () => void;
}) {
  const [draft, setDraft] = useState<Draft>(emptyDraft());
  const [picked, setPicked] = useState(false);
  const [i, setI] = useState(0);
  const [saving, setSaving] = useState(false);

  const steps = useMemo(() => stepsFor(draft.kind, picked), [draft.kind, picked]);
  const key = steps[Math.min(i, steps.length - 1)];
  const set = (patch: Partial<Draft>) => setDraft(d => ({ ...d, ...patch }));

  const canNext = key === 'options' ? draft.options !== null : true;
  const isLast = key === 'prefs';

  const finish = async () => {
    setSaving(true);
    try { await onDone(draftToRequest(draft)); } finally { setSaving(false); }
  };
  const next = () => { if (isLast) finish(); else setI(v => Math.min(v + 1, steps.length - 1)); };
  const back = () => setI(v => Math.max(0, v - 1));

  return (
    <View className="flex-1 bg-[#fafaf9]">
      {/* top bar */}
      <View className="px-6 pt-16 flex-row items-center justify-between">
        <View className="flex-row items-center gap-2">
          <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: EMERALD }} />
          <Text className="text-[10px] font-body text-gray-400 uppercase" style={{ letterSpacing: 2 }}>Finch · Onboarding</Text>
        </View>
        {onSkip && (
          <Pressable onPress={onSkip} hitSlop={10}><Text className="text-xs font-body text-gray-400">Skip for now →</Text></Pressable>
        )}
      </View>

      {/* progress dots */}
      <View className="px-6 mt-5 flex-row items-center gap-1.5">
        {steps.map((_, idx) => (
          <View key={idx} style={{ height: 6, borderRadius: 3, width: idx === i ? 32 : 24, backgroundColor: idx < i ? '#34d399' : idx === i ? '#111827' : '#e7e5e4' }} />
        ))}
      </View>

      <ScrollView contentContainerClassName="px-6 pt-5 pb-40" showsVerticalScrollIndicator={false}>
        <Text className="text-[22px] font-body-bold text-gray-900 mb-5">{HEADING[key]}</Text>

        {key === 'kind' && <IntentGrid value={picked ? draft.kind : null} onChange={(k) => { set({ kind: k }); setPicked(true); setI(1); }} />}
        {key === 'numbers' && <NumberFields draft={draft} set={set} />}
        {key === 'risk' && <RiskCards value={draft.risk} onChange={(risk) => set({ risk })} />}
        {key === 'options' && <OptionsCards value={draft.options} onChange={(options) => set({ options })} />}
        {key === 'prefs' && <PreferencesBlock draft={draft} set={set} />}
      </ScrollView>

      {/* footer nav */}
      {i > 0 && (
        <View className="absolute bottom-0 left-0 right-0 px-6 pb-10 pt-3 bg-[#fafaf9] border-t border-black/[0.06] flex-row items-center gap-3">
          <Pressable onPress={back} className="px-5 py-3.5"><Text className="text-sm font-body-medium text-gray-500">Back</Text></Pressable>
          <View className="flex-1" />
          <Pressable onPress={next} disabled={saving || !canNext}
            className={`px-7 py-3.5 rounded-xl ${saving || !canNext ? 'bg-gray-300' : 'bg-gray-900'}`}>
            {saving
              ? <ActivityIndicator color="#fff" />
              : <Text className="text-sm font-body-bold text-white">{isLast ? 'Set my mission' : 'Continue'}</Text>}
          </Pressable>
        </View>
      )}
    </View>
  );
}
