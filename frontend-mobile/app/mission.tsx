/**
 * Mission edit screen (mobile) — the editable view of the user's mission +
 * profile, the native mirror of web's Settings "Your mission & profile" section.
 * Single scrolling form (no steps): change kind, numbers, risk, options and
 * preferences, then save via goalApi.setGoal (which refreshes profile.md).
 */
import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useAuth } from '@/contexts/AuthContext';
import { goalApi } from '@/lib/api';
import {
  Draft, emptyDraft, goalToDraft, draftToRequest, INTENTS,
  NumberFields, RiskCards, OptionsCards, PreferencesBlock,
} from '@/components/onboarding/fields';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View className="mb-6">
      <Text className="text-[11px] font-body-medium text-emerald-700 uppercase mb-3" style={{ letterSpacing: 1 }}>◆ {title}</Text>
      {children}
    </View>
  );
}

export default function MissionScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    goalApi.getGoal(user.id)
      .then(g => { if (!cancelled) setDraft(g ? goalToDraft(g) : { ...emptyDraft(), kind: 'number' }); })
      .catch(() => { if (!cancelled) setDraft({ ...emptyDraft(), kind: 'number' }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [user]);

  const set = (patch: Partial<Draft>) => setDraft(d => (d ? { ...d, ...patch } : d));

  const save = async () => {
    if (!user || !draft) return;
    setSaving(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      await goalApi.setGoal(user.id, draftToRequest(draft));
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      router.back();
    } catch {
      Alert.alert('Could not save', 'Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !draft) {
    return <SafeAreaView className="flex-1 bg-[#fafaf9] items-center justify-center" edges={[]}><ActivityIndicator color="#059669" /></SafeAreaView>;
  }

  return (
    <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={[]}>
      <ScrollView contentContainerClassName="px-5 pt-4 pb-40" showsVerticalScrollIndicator={false}>
        <Section title="mission">
          <View className="flex-row flex-wrap gap-2">
            {INTENTS.map(it => (
              <Pressable key={it.kind} onPress={() => set({ kind: it.kind })}
                className={`px-3.5 py-2.5 rounded-xl border bg-white ${draft.kind === it.kind ? 'border-emerald-500' : 'border-black/[0.06]'}`}>
                <Text className="text-sm font-body-medium text-gray-900">{it.icon}  {it.title}</Text>
              </Pressable>
            ))}
          </View>
        </Section>

        <Section title="the numbers"><NumberFields draft={draft} set={set} /></Section>
        {draft.kind !== 'protect' && <Section title="how hard to push"><RiskCards value={draft.risk} onChange={(risk) => set({ risk })} /></Section>}
        {draft.kind === 'number' && <Section title="options"><OptionsCards value={draft.options} onChange={(options) => set({ options })} /></Section>}

        <PreferencesBlock draft={draft} set={set} />

        <Pressable onPress={save} disabled={saving}
          className={`mt-7 py-3.5 rounded-full items-center ${saving ? 'bg-gray-300' : 'bg-emerald-600'}`}>
          {saving ? <ActivityIndicator color="#fff" /> : <Text className="text-sm font-body-bold text-white">Save profile</Text>}
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}
