import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, RefreshControl, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { Clock, Sparkles } from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { marketApi, watchlistApi, jobsApi, thesesApi, type ScheduledJob, type Thesis } from '@/lib/api';
import { useStartChat } from '@/hooks/useStartChat';
import { COLORS, formatCurrency } from '@/lib/constants';
import ScreenHeader from '@/components/ui/ScreenHeader';
import SegmentedControl from '@/components/ui/SegmentedControl';
import DataError from '@/components/ui/DataError';
import { SkeletonRows } from '@/components/ui/Skeleton';

// Two kinds of time on one page: when the market will tell you something
// (earnings for what you own and watch), and when Finch will (its scheduled
// checks and briefs).

type Scope = 'yours' | 'all';

const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

function dayHeading(dateStr: string) {
  const d = new Date(`${dateStr}T12:00:00`);
  const today = new Date(); today.setHours(12, 0, 0, 0);
  const diff = Math.round((d.getTime() - today.getTime()) / 86_400_000);
  const label = d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
  return diff === 0 ? `Today · ${label}` : diff === 1 ? `Tomorrow · ${label}` : label;
}

const SLOT: Record<string, string> = { bmo: 'Before open', amc: 'After close', dmh: 'During hours' };

export default function CalendarScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const startChat = useStartChat();
  const [scopePick, setScope] = useState<Scope>('yours');
  // Guests have no "yours"; auth can also resolve after first render.
  const scope: Scope = user ? scopePick : 'all';
  const [earnings, setEarnings] = useState<any[]>([]);
  const [mine, setMine] = useState<Set<string>>(new Set());
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Earnings render as soon as they land; "yours" fills in as the watchlist and
  // the (slower) brokerage sync resolve, rather than gating the whole screen.
  const load = useCallback(async () => {
    const from = new Date();
    const to = new Date(); to.setDate(to.getDate() + 14);
    const addMine = (syms: string[]) => setMine(prev => new Set([...prev, ...syms.map(x => x.toUpperCase())]));
    if (user) {
      watchlistApi.getWatchlist(user.id)
        .then(d => addMine((d.symbols || d.watchlist || []).map((i: any) => String(typeof i === 'string' ? i : i.symbol))))
        .catch(() => {});
      // Holdings come from the backend's cached brokerage sync — no live SnapTrade call.
      thesesApi.list().then(d => { setTheses(d.theses || []); addMine(d.owned || []); }).catch(() => {});
      jobsApi.list().then(d => setJobs(d.jobs || [])).catch(() => {});
    }
    await marketApi.getEarnings(ymd(from), ymd(to))
      .then(d => { setEarnings(Array.isArray(d) ? d : d?.earnings || []); setError(false); })
      .catch(() => setError(true));
    setLoading(false);
  }, [user]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const visible = useMemo(
    () => (scope === 'yours' ? earnings.filter(e => mine.has(String(e.symbol).toUpperCase())) : earnings.slice(0, 80)),
    [scope, earnings, mine],
  );

  const byDay = useMemo(() => {
    const m = new Map<string, any[]>();
    visible.forEach(e => { const k = e.date; if (!m.has(k)) m.set(k, []); m.get(k)!.push(e); });
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [visible]);

  const schedule = useMemo(() => {
    const horizon = Date.now() + 7 * 86_400_000;
    return jobs
      .filter(j => (j.status === 'pending' || j.status === 'running') && j.run_at && new Date(j.run_at).getTime() <= horizon)
      .sort((a, b) => a.run_at.localeCompare(b.run_at))
      .slice(0, 6);
  }, [jobs]);

  const preview = (sym: string) => {
    const t = theses.find(x => x.symbol === sym.toUpperCase());
    const base = `Give me an earnings preview for ${sym}: consensus EPS and revenue, the options-implied move, the 2-3 things that will decide the reaction, and what it means for my position or watchlist interest. Take a stance.`;
    startChat(t
      ? `${base} My thesis: "${t.why}". I said I'd be wrong if: "${t.breaks || 'not stated'}". Tell me exactly what in this report would confirm or break it.`
      : base);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScreenHeader title="Calendar" subtitle="Next two weeks" />
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
        showsVerticalScrollIndicator={false}
      >
        {/* Finch's own schedule */}
        {user && schedule.length > 0 && (
          <>
            <Text style={styles.section}>Finch's schedule</Text>
            <View style={styles.list}>
              {schedule.map((j, i) => (
                <TouchableOpacity
                  key={j.id}
                  onPress={() => router.push('/watching')}
                  style={[styles.row, i > 0 && styles.divider]}
                  activeOpacity={0.7}
                >
                  <Clock size={15} color={COLORS.emerald} />
                  <Text style={styles.jobName} numberOfLines={1}>{j.name}</Text>
                  <Text style={styles.jobWhen}>
                    {new Date(j.run_at).toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </>
        )}

        <View style={styles.earnHead}>
          <Text style={[styles.section, { marginTop: 0, marginBottom: 0 }]}>Earnings</Text>
          {user && (
            <View style={{ width: 170 }}>
              <SegmentedControl<Scope>
                options={['yours', 'all']}
                selected={scope}
                onChange={setScope}
                labels={{ yours: 'Yours', all: 'All' }}
              />
            </View>
          )}
        </View>

        {loading ? (
          <SkeletonRows count={6} />
        ) : error && earnings.length === 0 ? (
          <DataError message="Couldn't load the earnings calendar" onRetry={onRefresh} />
        ) : byDay.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyText}>
              {scope === 'yours'
                ? mine.size === 0
                  ? 'Add stocks to Watching or connect a brokerage and their earnings show up here — with a preview from Finch the day before.'
                  : 'None of your stocks report in the next two weeks.'
                : 'No earnings scheduled.'}
            </Text>
            {scope === 'yours' && earnings.length > 0 && (
              <TouchableOpacity onPress={() => setScope('all')}><Text style={styles.link}>See all {earnings.length} reports</Text></TouchableOpacity>
            )}
          </View>
        ) : (
          byDay.map(([day, rows]) => (
            <View key={day} style={{ marginBottom: 14 }}>
              <Text style={styles.day}>{dayHeading(day)}</Text>
              <View style={styles.list}>
                {rows.map((e: any, i: number) => {
                  const yours = mine.has(String(e.symbol).toUpperCase());
                  return (
                    <TouchableOpacity
                      key={`${e.symbol}-${i}`}
                      onPress={() => router.push(`/stock/${e.symbol}`)}
                      style={[styles.row, i > 0 && styles.divider]}
                      activeOpacity={0.6}
                    >
                      <View style={{ flex: 1 }}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                          <Text style={styles.sym}>{e.symbol}</Text>
                          {yours && scope === 'all' && <View style={styles.yoursPill}><Text style={styles.yoursText}>Yours</Text></View>}
                        </View>
                        <Text style={styles.meta} numberOfLines={1}>
                          {SLOT[String(e.time || '').toLowerCase()] || 'Time TBD'}
                          {e.epsEstimated != null ? ` · EPS est. ${formatCurrency(e.epsEstimated)}` : ''}
                        </Text>
                      </View>
                      {yours && (
                        <TouchableOpacity onPress={() => preview(e.symbol)} style={styles.previewBtn} activeOpacity={0.8}>
                          <Sparkles size={12} color={COLORS.emerald} />
                          <Text style={styles.previewText}>Preview</Text>
                        </TouchableOpacity>
                      )}
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fafaf9' },
  scroll: { paddingHorizontal: 16, paddingBottom: 40, maxWidth: 760, width: '100%', alignSelf: 'center' },
  section: { fontFamily: 'DMSans-Bold', fontSize: 15, color: '#1c1917', marginTop: 8, marginBottom: 8 },
  earnHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 18, marginBottom: 12 },
  day: { fontFamily: 'DMSans-Bold', fontSize: 13.5, color: COLORS.gray900, marginBottom: 6 },
  list: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 14, paddingVertical: 12 },
  divider: { borderTopWidth: 1, borderTopColor: COLORS.gray100 },
  sym: { fontFamily: 'DMSans-Bold', fontSize: 15, color: COLORS.gray900 },
  meta: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.gray500, marginTop: 1 },
  yoursPill: { paddingHorizontal: 6, paddingVertical: 1, borderRadius: 6, backgroundColor: '#ecfdf5' },
  yoursText: { fontFamily: 'DMSans-Bold', fontSize: 10, color: COLORS.emerald },
  previewBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, backgroundColor: '#ecfdf5' },
  previewText: { fontFamily: 'DMSans-Bold', fontSize: 12, color: COLORS.emerald },
  jobName: { flex: 1, fontFamily: 'DMSans-Medium', fontSize: 14, color: COLORS.gray900 },
  jobWhen: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.gray500 },
  emptyCard: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, padding: 16 },
  emptyText: { fontFamily: 'DMSans', fontSize: 13.5, color: COLORS.gray500, lineHeight: 19 },
  link: { fontFamily: 'DMSans-Bold', fontSize: 13, color: COLORS.emerald, marginTop: 10 },
});
