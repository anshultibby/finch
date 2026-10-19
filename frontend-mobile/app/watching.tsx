import React, { useCallback, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, RefreshControl, StyleSheet, Alert, Switch, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { ChevronRight, Plus, Clock, Pause, ArrowUp } from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import {
  watchlistApi, marketApi, jobsApi, accountApi,
  type ScheduledJob, type UserPreferences,
} from '@/lib/api';
import { useStartChat } from '@/hooks/useStartChat';
import { COLORS, formatCurrency, formatPct, formatRelativeTime } from '@/lib/constants';
import ScreenHeader from '@/components/ui/ScreenHeader';
import SignInPrompt from '@/components/SignInPrompt';
import MiniSparkline from '@/components/shared/MiniSparkline';

// Everything Finch keeps an eye on, in one place: the stocks, the recurring
// checks (each stated as a plain-English rule you can pause), and how often
// Finch is allowed to reach out. Proactivity you can see and control.

const TEMPLATES: { name: string; message: string; recurrence: 'daily' | 'weekly' | 'weekdays'; hour: number; label: string }[] = [
  {
    label: 'Tell me when anything I own or watch moves 5%+, and why',
    name: 'Big-move watch',
    message: 'Check my holdings and watchlist. For anything that moved 5% or more since the last check, tell me what moved it (cite the source) and whether it changes the thesis. If nothing moved that much, do not notify me.',
    recurrence: 'weekdays',
    hour: 15,
  },
  {
    label: 'Every Friday, review my portfolio against my goal',
    name: 'Weekly goal review',
    message: 'Review my portfolio against my mission and profile: performance this week vs. SPY, pace toward my goal, concentration and risk, and the one change you would make. Take a clear stance.',
    recurrence: 'weekly',
    hour: 16,
  },
  {
    label: 'Flag news that changes the story on my holdings',
    name: 'Thesis-change watch',
    message: 'Scan news, filings and analyst actions on my holdings since the last check. Only report items that materially change the bull or bear case, with the source quoted. Skip routine noise; if nothing qualifies, do not notify me.',
    recurrence: 'weekdays',
    hour: 8,
  },
];

function nextAt(hour: number, weekly = false): string {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  if (d.getTime() <= Date.now()) d.setDate(d.getDate() + 1);
  if (weekly) while (d.getDay() !== 5) d.setDate(d.getDate() + 1);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  return d.toISOString();
}

function cadence(r: string | null) {
  if (!r) return 'Once';
  if (r === 'weekdays') return 'Weekdays';
  const m = /^every_(\d+)m$/.exec(r);
  if (m) {
    const mins = Number(m[1]);
    if (mins === 1440) return 'Daily';
    return mins % 60 === 0 ? `Every ${mins / 60}h` : `Every ${mins} min`;
  }
  return r.charAt(0).toUpperCase() + r.slice(1);
}

export default function WatchingScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const startChat = useStartChat();
  const [stocks, setStocks] = useState<{ symbol: string; price?: number; change_pct?: number }[]>([]);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [custom, setCustom] = useState('');
  const [adding, setAdding] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) return;
    await Promise.all([
      watchlistApi.getWatchlist(user.id).then(async d => {
        const raw: any[] = d.symbols || d.watchlist || [];
        if (raw.length && typeof raw[0] === 'object') {
          setStocks(raw.map(i => ({ symbol: i.symbol, price: i.price, change_pct: i.changesPercentage ?? i.change_pct })));
          return;
        }
        const syms = raw.map(String);
        if (!syms.length) { setStocks([]); return; }
        const quotes = await marketApi.getBatchQuotes(syms.slice(0, 30)).catch(() => []);
        const m = new Map((Array.isArray(quotes) ? quotes : []).map((q: any) => [q.symbol, q]));
        setStocks(syms.map(s => ({ symbol: s, price: (m.get(s) as any)?.price, change_pct: (m.get(s) as any)?.changesPercentage })));
      }).catch(() => {}),
      jobsApi.list().then(d => setJobs((d.jobs || []).filter(j => j.status !== 'cancelled' && j.status !== 'done'))).catch(() => {}),
      accountApi.getPreferences(user.id).then(setPrefs).catch(() => {}),
    ]);
  }, [user]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  if (!user) {
    return (
      <SafeAreaView style={styles.safe} edges={['top']}>
        <ScreenHeader title="Watching" />
        <SignInPrompt title="Let Finch keep watch" description="Sign in to have Finch track your stocks and tell you only when something matters." />
      </SafeAreaView>
    );
  }

  const addTemplate = async (t: typeof TEMPLATES[number]) => {
    setAdding(t.name);
    try {
      await jobsApi.create({ name: t.name, message: t.message, recurrence: t.recurrence, run_at: nextAt(t.hour, t.recurrence === 'weekly') });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      await load();
    } catch (e: any) {
      Alert.alert("Couldn't add that check", e?.response?.data?.detail || "You may have reached your plan's limit.");
    } finally {
      setAdding(null);
    }
  };

  const manageJob = (j: ScheduledJob) => {
    const isPaused = j.status === 'paused';
    const actions: any[] = [
      { text: isPaused ? 'Resume' : 'Pause', onPress: () => (isPaused ? jobsApi.resume(j.id) : jobsApi.pause(j.id)).then(load).catch(() => {}) },
    ];
    if (j.run_chat_id) actions.push({ text: 'See last run', onPress: () => router.push(`/(tabs)/chat/${j.run_chat_id}`) });
    if (!j.system_key) {
      actions.push({ text: 'Delete', style: 'destructive', onPress: () => jobsApi.cancel(j.id).then(load).catch(() => {}) });
    }
    actions.push({ text: 'Cancel', style: 'cancel' });
    Alert.alert(j.name, j.message.length > 240 ? `${j.message.slice(0, 240)}…` : j.message, actions);
  };

  const setPref = async (patch: Partial<UserPreferences>) => {
    if (!prefs) return;
    const prev = prefs;
    setPrefs({ ...prefs, ...patch });
    try {
      setPrefs(await accountApi.updatePreferences(user.id, patch));
    } catch {
      setPrefs(prev);
    }
  };

  const submitCustom = () => {
    const t = custom.trim();
    if (!t) return;
    setCustom('');
    startChat(`Set up a recurring check for me: "${t}". Restate it as a precise rule, pick a sensible schedule, confirm with me, then schedule it. Only notify me when the rule actually fires.`);
  };

  const activeCount = jobs.filter(j => j.status !== 'paused').length;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScreenHeader title="Watching" subtitle={`${stocks.length} stocks · ${activeCount} active check${activeCount === 1 ? '' : 's'}`} />
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {/* Checks */}
        <Text style={styles.section}>Checks Finch runs for you</Text>
        {jobs.length > 0 && (
          <View style={styles.list}>
            {jobs.map((j, i) => (
              <TouchableOpacity key={j.id} onPress={() => manageJob(j)} style={[styles.row, i > 0 && styles.divider]} activeOpacity={0.7}>
                {j.status === 'paused' ? <Pause size={15} color={COLORS.gray400} /> : <Clock size={15} color={COLORS.emerald} />}
                <View style={{ flex: 1 }}>
                  <Text style={[styles.jobName, j.status === 'paused' && { color: COLORS.gray400 }]} numberOfLines={1}>{j.name}</Text>
                  <Text style={styles.jobMeta} numberOfLines={1}>
                    {cadence(j.recurrence as string)}
                    {j.status === 'paused' ? ' · paused' : j.run_at ? ` · next ${new Date(j.run_at).toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}` : ''}
                    {j.last_run_at ? ` · ran ${formatRelativeTime(j.last_run_at)}` : ''}
                  </Text>
                </View>
                <ChevronRight size={16} color={COLORS.gray400} />
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* Add a check: plain English or a one-tap template */}
        <View style={[styles.addCard, jobs.length > 0 && { marginTop: 10 }]}>
          <View style={styles.askRow}>
            <TextInput
              value={custom}
              onChangeText={setCustom}
              placeholder="Tell Finch what to watch for…"
              placeholderTextColor={COLORS.gray400}
              style={styles.askInput}
              returnKeyType="send"
              onSubmitEditing={submitCustom}
            />
            <TouchableOpacity onPress={submitCustom} disabled={!custom.trim()} style={[styles.send, { backgroundColor: custom.trim() ? COLORS.emerald : COLORS.gray200 }]} accessibilityLabel="Set up check">
              <ArrowUp size={16} color="#fff" strokeWidth={2.6} />
            </TouchableOpacity>
          </View>
          {TEMPLATES.filter(t => !jobs.some(j => j.name === t.name)).map(t => (
            <TouchableOpacity key={t.name} onPress={() => addTemplate(t)} disabled={!!adding} style={styles.template} activeOpacity={0.7}>
              {adding === t.name ? <ActivityIndicator size="small" color={COLORS.emerald} /> : <Plus size={14} color={COLORS.emerald} />}
              <Text style={styles.templateText}>{t.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* How often Finch reaches out */}
        {prefs && (
          <>
            <Text style={styles.section}>Check-ins</Text>
            <View style={styles.list}>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.jobName}>Morning brief</Text>
                  <Text style={styles.jobMeta}>What changed overnight, before the open · {prefs.morning_brief_time}</Text>
                </View>
                <Switch value={prefs.morning_brief_enabled} onValueChange={v => setPref({ morning_brief_enabled: v })} trackColor={{ true: '#10b981' }} />
              </View>
              <View style={[styles.row, styles.divider]}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.jobName}>Daily portfolio watch</Text>
                  <Text style={styles.jobMeta}>Finch reviews your book and the news, and pings you only if it matters</Text>
                </View>
                <Switch value={prefs.heartbeat_enabled} onValueChange={v => setPref({ heartbeat_enabled: v })} trackColor={{ true: '#10b981' }} />
              </View>
            </View>
          </>
        )}

        {/* Stocks */}
        <View style={styles.stocksHead}>
          <Text style={[styles.section, { marginBottom: 0 }]}>Stocks</Text>
          <TouchableOpacity onPress={() => router.push('/watchlist')}><Text style={styles.link}>Manage</Text></TouchableOpacity>
        </View>
        {stocks.length === 0 ? (
          <TouchableOpacity onPress={() => router.push('/watchlist')} style={styles.emptyCard} activeOpacity={0.8}>
            <Text style={styles.emptyText}>No stocks yet. Add a few, or import from a screenshot or Robinhood, and Finch starts watching them.</Text>
          </TouchableOpacity>
        ) : (
          <View style={styles.list}>
            {stocks.slice(0, 12).map((s, i) => (
              <TouchableOpacity key={s.symbol} onPress={() => router.push(`/stock/${s.symbol}`)} style={[styles.row, i > 0 && styles.divider]} activeOpacity={0.6}>
                <Text style={[styles.jobName, { flex: 1 }]}>{s.symbol}</Text>
                <MiniSparkline symbol={s.symbol} width={52} height={20} days={30} />
                <View style={{ alignItems: 'flex-end', minWidth: 76 }}>
                  <Text style={styles.price}>{formatCurrency(s.price, false, s.symbol)}</Text>
                  {s.change_pct != null && (
                    <Text style={[styles.chg, { color: s.change_pct >= 0 ? COLORS.emerald : COLORS.red }]}>{formatPct(s.change_pct)}</Text>
                  )}
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fafaf9' },
  scroll: { paddingHorizontal: 16, paddingBottom: 40, maxWidth: 760, width: '100%', alignSelf: 'center' },
  section: { fontFamily: 'DMSans-Bold', fontSize: 12, color: COLORS.gray500, textTransform: 'uppercase', letterSpacing: 0.6, marginTop: 18, marginBottom: 8 },
  list: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 14, paddingVertical: 12 },
  divider: { borderTopWidth: 1, borderTopColor: COLORS.gray100 },
  jobName: { fontFamily: 'DMSans-Bold', fontSize: 14.5, color: COLORS.gray900 },
  jobMeta: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.gray500, marginTop: 1, lineHeight: 17 },
  addCard: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: '#d1fae5', padding: 12 },
  askRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingLeft: 4 },
  askInput: { flex: 1, fontFamily: 'DMSans', fontSize: 15, color: COLORS.gray900, paddingVertical: 8 },
  send: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  template: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 8, paddingHorizontal: 4 },
  templateText: { flex: 1, fontFamily: 'DMSans-Medium', fontSize: 13.5, color: COLORS.gray700 },
  stocksHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 10, marginBottom: 8 },
  link: { fontFamily: 'DMSans-Bold', fontSize: 13, color: COLORS.emerald },
  price: { fontFamily: 'DMSans-Medium', fontSize: 14.5, color: COLORS.gray900, fontVariant: ['tabular-nums'] },
  chg: { fontFamily: 'DMSans', fontSize: 12.5, fontVariant: ['tabular-nums'] },
  emptyCard: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, padding: 16 },
  emptyText: { fontFamily: 'DMSans', fontSize: 13.5, color: COLORS.gray500, lineHeight: 19 },
});
