import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, RefreshControl, StyleSheet, KeyboardAvoidingView, Platform, useWindowDimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import Animated, { FadeInDown } from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';
import {
  Sparkles, SlidersHorizontal, Zap, FileText, CalendarDays, Eye, Bell, Settings, ChevronRight, Search,
} from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import {
  activityApi, insightsApi, marketApi, notificationsApi, pendingTradesApi, watchlistApi, jobsApi, ideasApi,
  type ActivityRecap, type PortfolioDigest, type PendingTradeItem, type ScheduledJob, type TradeIdea,
} from '@/lib/api';
import { isCacheFresh, touchCache } from '@/hooks/useCachedResource';
import { useStartChat } from '@/hooks/useStartChat';
import { syncBadgeCount } from '@/lib/pushNotifications';
import { COLORS, formatCurrency, formatPct } from '@/lib/constants';
import FinchLogo from '@/components/FinchLogo';
import AskBar from '@/components/chat/AskBar';
import { Skeleton } from '@/components/ui/Skeleton';

// ── Home ─────────────────────────────────────────────────────────────────────
// One page. Finch speaks first (the brief: what changed for *you*, ranked, and
// hidden when there's nothing worth saying), then six cards — one per tool —
// each carrying a live line about what Finch did with that tool while you were
// away. The cards are the navigation; there is no drawer and no tab bar.

const PULSE = [
  { symbol: 'SPY', label: 'S&P 500' },
  { symbol: 'QQQ', label: 'Nasdaq' },
  { symbol: 'DIA', label: 'Dow' },
];

type BriefItem = {
  key: string;
  tone: 'action' | 'heads-up' | 'info';
  title: string;
  body?: string;
  cta?: string;
  onPress: () => void;
};

type CardSpec = {
  key: string;
  title: string;
  line: string;
  attention?: boolean;
  icon: React.ComponentType<{ size?: number; color?: string }>;
  tint: string;
  fg: string;
  href: string;
};

function greeting(d = new Date()) {
  const h = d.getHours();
  if (h < 5) return 'Up late';
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

// US regular session, evaluated in New York time. Holidays aren't modelled —
// this is a header hint, not a trading gate.
function marketStatus(): string {
  try {
    const ny = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const day = ny.getDay();
    const mins = ny.getHours() * 60 + ny.getMinutes();
    if (day === 0 || day === 6) return 'Markets closed';
    if (mins >= 570 && mins < 960) return 'Markets open';
    if (mins >= 240 && mins < 570) return 'Pre-market';
    if (mins >= 960 && mins < 1200) return 'After hours';
    return 'Markets closed';
  } catch {
    return '';
  }
}

function dayDiff(dateStr: string): number {
  const d = new Date(`${dateStr}T12:00:00`);
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  return Math.round((d.getTime() - today.getTime()) / 86_400_000);
}

function whenLabel(dateStr: string, time?: string) {
  const diff = dayDiff(dateStr);
  const day = diff === 0 ? 'today' : diff === 1 ? 'tomorrow' : new Date(`${dateStr}T12:00:00`).toLocaleDateString('en-US', { weekday: 'long' });
  const t = (time || '').toLowerCase();
  const slot = t === 'bmo' ? ' before the open' : t === 'amc' ? ' after the close' : '';
  return `${day}${slot}`;
}

export default function HomeScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const startChat = useStartChat();
  const { width } = useWindowDimensions();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [unread, setUnread] = useState(0);
  const [pending, setPending] = useState<PendingTradeItem[]>([]);
  const [recap, setRecap] = useState<ActivityRecap | null>(null);
  const [digest, setDigest] = useState<PortfolioDigest | null>(null);
  const [earnings, setEarnings] = useState<any[]>([]);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [ideas, setIdeas] = useState<TradeIdea[]>([]);
  const [pulse, setPulse] = useState<Record<string, any>>({});

  const load = useCallback(async () => {
    const tasks: Promise<unknown>[] = [
      marketApi.getEarnings().then(d => setEarnings(Array.isArray(d) ? d : d?.earnings || [])).catch(() => {}),
      marketApi.getBatchQuotes(PULSE.map(p => p.symbol)).then(rows => {
        if (!Array.isArray(rows)) return;
        const m: Record<string, any> = {};
        rows.forEach((q: any) => { if (q?.symbol) m[q.symbol] = q; });
        setPulse(m);
      }).catch(() => {}),
    ];
    if (user) {
      tasks.push(
        pendingTradesApi.list().then(d => setPending(
          (d.pending_trades || []).filter(t => !t.expires_at || new Date(t.expires_at).getTime() > Date.now())
        )).catch(() => {}),
        activityApi.getRecap().then(setRecap).catch(() => {}),
        insightsApi.getPortfolioDigest(user.id).then(setDigest).catch(() => {}),
        watchlistApi.getWatchlist(user.id).then(d => {
          const raw = d.symbols || d.watchlist || [];
          setWatchlist(raw.map((i: any) => (typeof i === 'string' ? i : i.symbol)).filter(Boolean));
        }).catch(() => {}),
        jobsApi.list().then(d => setJobs(d.jobs || [])).catch(() => {}),
        ideasApi.list(20).then(d => setIdeas(d.ideas || [])).catch(() => {}),
        notificationsApi.getUnreadCount().then(d => {
          const n = d.unread_count || 0;
          setUnread(n);
          syncBadgeCount(n);
        }).catch(() => {}),
      );
    }
    await Promise.all(tasks);
    setLoading(false);
  }, [user]);

  // Approvals are time-boxed, so they're re-checked on every focus; the rest
  // refetches only when older than a minute.
  useFocusEffect(useCallback(() => {
    const key = `home:${user?.id ?? 'guest'}`;
    if (!isCacheFresh(key, 60_000)) load().then(() => touchCache(key));
    else if (user) {
      pendingTradesApi.list().then(d => setPending(
        (d.pending_trades || []).filter(t => !t.expires_at || new Date(t.expires_at).getTime() > Date.now())
      )).catch(() => {});
    }
  }, [user, load]));

  const onRefresh = useCallback(async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  // The user's own symbols: holdings Finch already priced in the digest, plus the watchlist.
  const mySymbols = useMemo(() => {
    const s = new Set<string>(watchlist.map(x => x.toUpperCase()));
    (digest?.movers || []).forEach(m => s.add(m.symbol.toUpperCase()));
    return s;
  }, [watchlist, digest]);

  const myEarnings = useMemo(
    () => earnings
      .filter(e => e?.symbol && mySymbols.has(String(e.symbol).toUpperCase()))
      .filter(e => { const d = dayDiff(e.date || e.reportDate); return d >= 0 && d <= 7; })
      .sort((a, b) => String(a.date).localeCompare(String(b.date))),
    [earnings, mySymbols],
  );

  const activeJobs = jobs.filter(j => j.status === 'pending' || j.status === 'running');
  const openIdeas = ideas.filter(i => i.status === 'proposed' && i.outcome === 'pending');

  // ── The brief: ranked, capped at three, never filler ──
  const brief: BriefItem[] = useMemo(() => {
    if (!user) return [];
    const items: BriefItem[] = [];
    if (pending.length > 0) {
      items.push({
        key: 'approvals',
        tone: 'action',
        title: pending.length === 1 ? 'A trade needs your approval' : `${pending.length} trades need your approval`,
        body: pending[0].summary || undefined,
        cta: 'Review',
        onPress: () => router.push('/trader'),
      });
    }
    const soon = myEarnings.filter(e => dayDiff(e.date || e.reportDate) <= 2)[0];
    if (soon) {
      items.push({
        key: `earn-${soon.symbol}`,
        tone: 'heads-up',
        title: `${soon.symbol} reports ${whenLabel(soon.date || soon.reportDate, soon.time)}`,
        body: 'Want the setup — what the street expects, the implied move, and what it means for you?',
        cta: 'Preview it',
        onPress: () => startChat(
          `Give me an earnings preview for ${soon.symbol}: consensus EPS and revenue, the options-implied move, the 2-3 things that will decide the reaction, and what it means for my position or watchlist interest. Take a stance.`,
        ),
      });
    }
    const signal = (recap?.events || []).find(e => e.event_type === 'alert' || e.event_type === 'insight');
    if (signal) {
      items.push({
        key: `evt-${signal.id}`,
        tone: 'heads-up',
        title: signal.title,
        body: signal.body || undefined,
        onPress: () => router.push('/activity'),
      });
    }
    if (digest?.narrative && digest.mode !== 'empty') {
      items.push({
        key: 'digest',
        tone: 'info',
        title: digest.mode === 'portfolio' ? 'Your book today' : 'Your watchlist today',
        body: digest.narrative,
        onPress: () => router.push(digest.mode === 'portfolio' ? '/portfolio' : '/watching'),
      });
    }
    return items.slice(0, 3);
  }, [user, pending, myEarnings, recap, digest, router, startChat]);

  // ── Six cards, each with a live line ──
  const cards: CardSpec[] = [
    {
      key: 'assistant', title: 'Ask Finch', icon: Sparkles, tint: '#ecfdf5', fg: COLORS.emerald, href: '/(tabs)/chat',
      line: openIdeas.length > 0 ? `${openIdeas.length} idea${openIdeas.length > 1 ? 's' : ''} for you` : 'Research, explain, plan',
      attention: openIdeas.length > 0,
    },
    {
      key: 'screener', title: 'Screener', icon: SlidersHorizontal, tint: '#eff6ff', fg: COLORS.blue, href: '/screener',
      line: 'Describe it, Finch finds it',
    },
    {
      key: 'trader', title: 'Trader', icon: Zap, tint: '#fffbeb', fg: '#d97706', href: '/trader',
      line: pending.length > 0 ? `${pending.length} awaiting approval` : activeJobs.length > 0 ? `${activeJobs.length} automation${activeJobs.length > 1 ? 's' : ''} running` : 'Your agent, on a leash',
      attention: pending.length > 0,
    },
    {
      key: 'financials', title: 'Financials', icon: FileText, tint: '#f5f3ff', fg: COLORS.violet, href: '/research',
      line: 'Statements, filings, calls',
    },
    {
      key: 'calendar', title: 'Calendar', icon: CalendarDays, tint: '#fdf2f8', fg: '#db2777', href: '/calendar',
      line: myEarnings.length > 0
        ? `${myEarnings.length} of yours report${myEarnings.length === 1 ? 's' : ''} this week`
        : `${earnings.length || 'No'} reports this week`,
      attention: myEarnings.some(e => dayDiff(e.date || e.reportDate) <= 1),
    },
    {
      key: 'watching', title: 'Watching', icon: Eye, tint: '#f0fdfa', fg: '#0d9488', href: '/watching',
      line: user
        ? `${watchlist.length} stock${watchlist.length === 1 ? '' : 's'} · ${activeJobs.length} check${activeJobs.length === 1 ? '' : 's'}`
        : 'What Finch keeps an eye on',
    },
  ];

  const cols = width >= 700 ? 3 : 2;
  const contentW = Math.min(width, 760);
  const cardW = (contentW - 16 * 2 - 10 * (cols - 1)) / cols;
  const firstName = (user?.user_metadata?.full_name || user?.user_metadata?.name || '').split(' ')[0];
  const status = marketStatus();

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView
          contentContainerStyle={[styles.scroll, { maxWidth: 760, alignSelf: 'center', width: '100%' }]}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {/* Header */}
          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <View style={styles.brandRow}>
                <FinchLogo size={18} />
                {status ? <Text style={styles.status}>{status}</Text> : null}
              </View>
              <Text style={styles.hello}>{greeting()}{firstName ? `, ${firstName}` : ''}</Text>
            </View>
            <TouchableOpacity onPress={() => router.push('/research')} style={styles.iconBtn} activeOpacity={0.7} accessibilityLabel="Search stocks">
              <Search size={20} color={COLORS.gray500} />
            </TouchableOpacity>
            {user && (
              <TouchableOpacity onPress={() => router.push('/notifications')} style={styles.iconBtn} activeOpacity={0.7} accessibilityLabel="Notifications">
                <Bell size={20} color={COLORS.gray500} />
                {unread > 0 && (
                  <View style={styles.badge}><Text style={styles.badgeText}>{unread > 9 ? '9+' : unread}</Text></View>
                )}
              </TouchableOpacity>
            )}
            <TouchableOpacity
              onPress={() => router.push(user ? '/settings' : '/(auth)/login')}
              style={styles.iconBtn}
              activeOpacity={0.7}
              accessibilityLabel={user ? 'Settings' : 'Sign in'}
            >
              <Settings size={20} color={COLORS.gray500} />
            </TouchableOpacity>
          </View>

          {/* Book strip — the one number that matters, if Finch has it */}
          {user && digest?.mode === 'portfolio' && digest.total_value != null && (
            <TouchableOpacity onPress={() => router.push('/portfolio')} activeOpacity={0.8} style={styles.book}>
              <View>
                <Text style={styles.bookLabel}>Your book</Text>
                <Text style={styles.bookValue}>{formatCurrency(digest.total_value)}</Text>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <Text style={[styles.bookChange, { color: (digest.day_change_pct ?? 0) >= 0 ? COLORS.emerald : COLORS.red }]}>
                  {formatPct(digest.day_change_pct)}
                </Text>
                <Text style={styles.bookSub}>today</Text>
              </View>
            </TouchableOpacity>
          )}

          {/* The brief */}
          {!user ? (
            <View style={styles.guest}>
              <Text style={styles.guestTitle}>Finch watches your stocks so you don't have to.</Text>
              <Text style={styles.guestBody}>
                It reads the news, earnings and filings for what you own, tells you what matters before it moves, and only acts with your approval.
              </Text>
              <TouchableOpacity onPress={() => router.push('/(auth)/login')} style={styles.guestBtn} activeOpacity={0.85}>
                <Text style={styles.guestBtnText}>Get started</Text>
              </TouchableOpacity>
            </View>
          ) : loading ? (
            <View style={styles.briefCard}>
              <Skeleton width={120} height={12} radius={4} />
              <View style={{ height: 10 }} />
              <Skeleton width={'90%' as any} height={16} radius={4} />
              <View style={{ height: 6 }} />
              <Skeleton width={'70%' as any} height={14} radius={4} />
            </View>
          ) : (
            <View style={styles.briefCard}>
              <View style={styles.briefHead}>
                <View style={styles.liveDot} />
                <Text style={styles.briefLabel}>{brief.length > 0 ? 'Finch noticed' : 'All quiet'}</Text>
              </View>
              {brief.length === 0 ? (
                <Text style={styles.quiet}>
                  {mySymbols.size > 0
                    ? `Nothing needs you right now. I'm watching ${mySymbols.size} stock${mySymbols.size === 1 ? '' : 's'} and will ping you if something moves.`
                    : 'Add a few stocks to Watching or connect a brokerage, and I\'ll start keeping an eye on them for you.'}
                </Text>
              ) : (
                brief.map((b, i) => (
                  <Animated.View key={b.key} entering={FadeInDown.delay(i * 60).springify().damping(16)}>
                    <TouchableOpacity onPress={b.onPress} activeOpacity={0.75} style={[styles.briefItem, i > 0 && styles.briefDivider]}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.briefTitle}>{b.title}</Text>
                        {b.body ? <Text style={styles.briefBody} numberOfLines={3}>{b.body}</Text> : null}
                      </View>
                      {b.cta ? (
                        <View style={[styles.cta, b.tone === 'action' && styles.ctaAction]}>
                          <Text style={[styles.ctaText, b.tone === 'action' && { color: '#fff' }]}>{b.cta}</Text>
                        </View>
                      ) : (
                        <ChevronRight size={16} color={COLORS.gray400} />
                      )}
                    </TouchableOpacity>
                  </Animated.View>
                ))
              )}
              {recap?.next_run?.run_at && (
                <Text style={styles.nextRun}>
                  Next: {recap.next_run.name} · {new Date(recap.next_run.run_at).toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}
                </Text>
              )}
            </View>
          )}

          {/* Six cards */}
          <View style={styles.grid}>
            {cards.map((c, i) => {
              const Icon = c.icon;
              return (
                <Animated.View key={c.key} entering={FadeInDown.delay(80 + i * 40).springify().damping(16)}>
                  <TouchableOpacity
                    testID={`home-card-${c.key}`}
                    onPress={() => { Haptics.selectionAsync(); router.push(c.href as any); }}
                    activeOpacity={0.8}
                    style={[styles.card, { width: cardW }, c.attention && styles.cardAttention]}
                  >
                    <View style={styles.cardTop}>
                      <View style={[styles.cardIcon, { backgroundColor: c.tint }]}>
                        <Icon size={18} color={c.fg} />
                      </View>
                      {c.attention && <View style={styles.attnDot} />}
                    </View>
                    <Text style={styles.cardTitle}>{c.title}</Text>
                    <Text style={[styles.cardLine, c.attention && { color: COLORS.emerald }]} numberOfLines={2}>{c.line}</Text>
                  </TouchableOpacity>
                </Animated.View>
              );
            })}
          </View>

          {/* Market pulse — a glance, tap through for the full markets view */}
          <TouchableOpacity onPress={() => router.push('/markets')} activeOpacity={0.8} style={styles.pulse}>
            {PULSE.map(p => {
              const q = pulse[p.symbol];
              const chg = q?.changesPercentage;
              return (
                <View key={p.symbol} style={styles.pulseItem}>
                  <Text style={styles.pulseLabel}>{p.label}</Text>
                  <Text style={[styles.pulseChg, { color: chg == null ? COLORS.gray400 : chg >= 0 ? COLORS.emerald : COLORS.red }]}>
                    {chg == null ? '—' : formatPct(chg)}
                  </Text>
                </View>
              );
            })}
            <ChevronRight size={16} color={COLORS.gray400} />
          </TouchableOpacity>
        </ScrollView>

        <AskBar placeholder="Ask Finch anything…" />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fafaf9' },
  scroll: { paddingHorizontal: 16, paddingBottom: 24 },
  header: { flexDirection: 'row', alignItems: 'center', paddingTop: 8, paddingBottom: 14 },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  status: { fontFamily: 'DMSans-Medium', fontSize: 12, color: COLORS.gray500 },
  hello: { fontFamily: 'DMSans-Bold', fontSize: 24, color: COLORS.gray900, letterSpacing: -0.5, marginTop: 6 },
  iconBtn: { width: 38, height: 38, alignItems: 'center', justifyContent: 'center' },
  badge: { position: 'absolute', top: 4, right: 3, minWidth: 16, height: 16, borderRadius: 8, backgroundColor: COLORS.red, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 3 },
  badgeText: { color: '#fff', fontSize: 9.5, fontFamily: 'DMSans-Bold' },

  book: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, paddingHorizontal: 16, paddingVertical: 14, marginBottom: 10 },
  bookLabel: { fontFamily: 'DMSans-Medium', fontSize: 12, color: COLORS.gray500 },
  bookValue: { fontFamily: 'DMSans-Bold', fontSize: 26, color: COLORS.gray900, letterSpacing: -0.6, marginTop: 2, fontVariant: ['tabular-nums'] },
  bookChange: { fontFamily: 'DMSans-Bold', fontSize: 16, fontVariant: ['tabular-nums'] },
  bookSub: { fontFamily: 'DMSans', fontSize: 11.5, color: COLORS.gray400 },

  briefCard: { backgroundColor: '#fff', borderRadius: 18, borderWidth: 1, borderColor: '#d1fae5', padding: 16, marginBottom: 14 },
  briefHead: { flexDirection: 'row', alignItems: 'center', gap: 7, marginBottom: 8 },
  liveDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#10b981' },
  briefLabel: { fontFamily: 'DMSans-Bold', fontSize: 12, color: COLORS.emerald, textTransform: 'uppercase', letterSpacing: 0.6 },
  briefItem: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 8 },
  briefDivider: { borderTopWidth: 1, borderTopColor: COLORS.gray100 },
  briefTitle: { fontFamily: 'DMSans-Bold', fontSize: 15, color: COLORS.gray900, lineHeight: 20 },
  briefBody: { fontFamily: 'DMSans', fontSize: 13.5, color: COLORS.gray500, lineHeight: 19, marginTop: 2 },
  cta: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, backgroundColor: '#ecfdf5' },
  ctaAction: { backgroundColor: COLORS.emerald },
  ctaText: { fontFamily: 'DMSans-Bold', fontSize: 12.5, color: COLORS.emerald },
  quiet: { fontFamily: 'DMSans', fontSize: 14, color: COLORS.gray700, lineHeight: 20 },
  nextRun: { fontFamily: 'DMSans', fontSize: 12, color: COLORS.gray400, marginTop: 8 },

  guest: { backgroundColor: '#fff', borderRadius: 18, borderWidth: 1, borderColor: '#d1fae5', padding: 18, marginBottom: 14 },
  guestTitle: { fontFamily: 'DMSans-Bold', fontSize: 18, color: COLORS.gray900, lineHeight: 24, letterSpacing: -0.3 },
  guestBody: { fontFamily: 'DMSans', fontSize: 14, color: COLORS.gray500, lineHeight: 20, marginTop: 6 },
  guestBtn: { alignSelf: 'flex-start', backgroundColor: COLORS.emerald, borderRadius: 999, paddingHorizontal: 18, paddingVertical: 10, marginTop: 14 },
  guestBtnText: { color: '#fff', fontFamily: 'DMSans-Bold', fontSize: 14 },

  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  card: { backgroundColor: '#fff', borderRadius: 18, borderWidth: 1, borderColor: COLORS.gray100, padding: 14, height: 128 },
  cardAttention: { borderColor: '#a7f3d0' },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardIcon: { width: 36, height: 36, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  attnDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#10b981', marginTop: 4 },
  cardTitle: { fontFamily: 'DMSans-Bold', fontSize: 16, color: COLORS.gray900, marginTop: 14, letterSpacing: -0.2 },
  cardLine: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.gray500, marginTop: 3, lineHeight: 17 },

  pulse: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 14, borderWidth: 1, borderColor: COLORS.gray100, paddingHorizontal: 14, paddingVertical: 12, marginTop: 14 },
  pulseItem: { flex: 1 },
  pulseLabel: { fontFamily: 'DMSans-Medium', fontSize: 11.5, color: COLORS.gray500 },
  pulseChg: { fontFamily: 'DMSans-Bold', fontSize: 14, marginTop: 1, fontVariant: ['tabular-nums'] },
});
