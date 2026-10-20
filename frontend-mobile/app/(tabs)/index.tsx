import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, RefreshControl, StyleSheet, KeyboardAvoidingView, Platform, useWindowDimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import * as Haptics from 'expo-haptics';
import {
  Sparkles, SlidersHorizontal, Zap, FileText, CalendarDays, Eye, Bell, Settings, ChevronRight, Search,
} from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import {
  activityApi, insightsApi, marketApi, notificationsApi, pendingTradesApi, watchlistApi, jobsApi, ideasApi, thesesApi,
  type ActivityRecap, type PortfolioDigest, type PendingTradeItem, type ScheduledJob, type TradeIdea, type MoveVerdict,
  VERDICT_META, THESIS_STATUS_META, type ThesisStatus, type Thesis,
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
  verdict?: MoveVerdict;
  thesis?: ThesisStatus;
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
  icon: React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }>;
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

function earningsPreviewPrompt(sym: string, thesis?: Thesis) {
  const base = `Give me an earnings preview for ${sym}: consensus EPS and revenue, the options-implied move, the 2-3 things that will decide the reaction, and what it means for my position or watchlist interest. Take a stance.`;
  return thesis
    ? `${base} My thesis: "${thesis.why}". I said I'd be wrong if: "${thesis.breaks || 'not stated'}". Tell me exactly what in this report would confirm or break it.`
    : base;
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
  // null = not loaded yet, so card lines never claim "0 stocks" or "No reports"
  // before the data has actually arrived.
  const [earnings, setEarnings] = useState<any[] | null>(null);
  const [watchlist, setWatchlist] = useState<string[] | null>(null);
  const [jobs, setJobs] = useState<ScheduledJob[] | null>(null);
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [owned, setOwned] = useState<string[]>([]);
  const [ideas, setIdeas] = useState<TradeIdea[]>([]);
  const [pulse, setPulse] = useState<Record<string, any>>({});

  // The brief renders as soon as the fast, decisive sources land (approvals,
  // the user's symbols, the earnings calendar). Slower sources — the activity
  // recap, ideas, and the LLM-written digest — join it when they arrive.
  const load = useCallback(async () => {
    const core: Promise<unknown>[] = [
      marketApi.getEarnings().then(d => setEarnings(Array.isArray(d) ? d : d?.earnings || [])).catch(() => setEarnings([])),
    ];
    marketApi.getBatchQuotes(PULSE.map(p => p.symbol)).then(rows => {
      if (!Array.isArray(rows)) return;
      const m: Record<string, any> = {};
      rows.forEach((q: any) => { if (q?.symbol) m[q.symbol] = q; });
      setPulse(m);
    }).catch(() => {});
    if (user) {
      core.push(
        pendingTradesApi.list().then(d => setPending(
          (d.pending_trades || []).filter(t => !t.expires_at || new Date(t.expires_at).getTime() > Date.now())
        )).catch(() => {}),
        watchlistApi.getWatchlist(user.id).then(d => {
          const raw = d.symbols || d.watchlist || [];
          setWatchlist(raw.map((i: any) => (typeof i === 'string' ? i : i.symbol)).filter(Boolean));
        }).catch(() => setWatchlist([])),
      );
      insightsApi.getPortfolioDigest(user.id).then(setDigest).catch(() => {});
      activityApi.getRecap().then(setRecap).catch(() => {});
      jobsApi.list().then(d => setJobs(d.jobs || [])).catch(() => setJobs([]));
      ideasApi.list(20).then(d => setIdeas(d.ideas || [])).catch(() => {});
      thesesApi.list().then(d => { setTheses(d.theses || []); setOwned(d.owned || []); }).catch(() => {});
      notificationsApi.getUnreadCount().then(d => {
        const n = d.unread_count || 0;
        setUnread(n);
        syncBadgeCount(n);
      }).catch(() => {});
    }
    await Promise.all(core);
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
    const s = new Set<string>((watchlist || []).map(x => x.toUpperCase()));
    owned.forEach(x => s.add(x.toUpperCase()));
    (digest?.movers || []).forEach(m => s.add(m.symbol.toUpperCase()));
    return s;
  }, [watchlist, digest, owned]);

  const myEarnings = useMemo(
    () => (earnings || [])
      .filter(e => e?.symbol && mySymbols.has(String(e.symbol).toUpperCase()))
      .filter(e => { const d = dayDiff(e.date || e.reportDate); return d >= 0 && d <= 7; })
      .sort((a, b) => String(a.date).localeCompare(String(b.date))),
    [earnings, mySymbols],
  );

  const thesisBySymbol = useMemo(() => new Map(theses.map(t => [t.symbol, t])), [theses]);
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
    // Agent signals that cleared the bar. Routine noise stays in the ledger,
    // and a story change outranks everything but an approval.
    const signals = (recap?.events || [])
      .filter(e => (e.event_type === 'alert' || e.event_type === 'insight') && e.data?.verdict !== 'noise');
    // A thesis the user wrote that's now weakened/broken is the most personal
    // signal there is; then a market-level story change.
    const shift = signals.find(e => e.data?.thesis_status === 'broken' || e.data?.thesis_status === 'weakened')
      || signals.find(e => e.data?.verdict === 'narrative_shift');
    const signal = shift || signals[0];
    const signalItem: BriefItem | undefined = signal && {
      key: `evt-${signal.id}`,
      tone: shift ? 'action' : 'heads-up',
      verdict: signal.data?.verdict as MoveVerdict | undefined,
      thesis: (signal.data?.thesis_status || undefined) as ThesisStatus | undefined,
      title: signal.title,
      body: signal.body || undefined,
      onPress: () => (signal.data?.chat_id ? router.push(`/(tabs)/chat/${signal.data.chat_id}`)
        : signal.data?.symbol ? router.push(`/stock/${signal.data.symbol}`) : router.push('/activity')),
    };
    if (signalItem && shift) items.push(signalItem);
    const soon = myEarnings.filter(e => dayDiff(e.date || e.reportDate) <= 2)[0];
    if (soon) {
      const t = thesisBySymbol.get(String(soon.symbol).toUpperCase());
      items.push({
        key: `earn-${soon.symbol}`,
        tone: 'heads-up',
        title: `${soon.symbol} reports ${whenLabel(soon.date || soon.reportDate, soon.time)}`,
        // With a thesis, the heads-up is about *their* line in the sand.
        body: t?.breaks
          ? `You said you'd ${t.stance === 'own' ? 'sell' : 'reconsider'} if: ${t.breaks}`
          : 'Want the setup — what the street expects, the implied move, and what it means for you?',
        cta: 'Preview it',
        onPress: () => startChat(earningsPreviewPrompt(soon.symbol, t)),
      });
    }
    if (signalItem && !shift) items.push(signalItem);
    if (digest?.narrative && digest.mode !== 'empty') {
      items.push({
        key: 'digest',
        tone: 'info',
        title: digest.mode === 'portfolio' ? 'Your book today' : 'Your watchlist today',
        body: digest.narrative,
        onPress: () => router.push(digest.mode === 'portfolio' ? '/portfolio' : '/watching'),
      });
    }
    // Held stocks first — a thesis matters most where real money is.
    const heldUncovered = owned.find(sym => !thesisBySymbol.has(sym));
    const firstUncovered = heldUncovered || (watchlist || []).find(sym => !thesisBySymbol.has(sym.toUpperCase()));
    if (theses.length === 0 && firstUncovered && items.length < 3) {
      items.push({
        key: 'thesis-nudge',
        tone: 'info',
        title: heldUncovered ? `Why do you own ${firstUncovered}?` : `Why are you watching ${firstUncovered}?`,
        body: heldUncovered
          ? 'Write one line on why, and what would make you sell. Every alert on it gets judged against your words.'
          : 'Write one line on why, and what would make you buy. Every alert on it gets judged against your words.',
        cta: 'Write it',
        onPress: () => router.push(`/stock/${firstUncovered}`),
      });
    }
    return items.slice(0, 3);
  }, [user, pending, myEarnings, recap, digest, router, startChat, thesisBySymbol, theses, watchlist, owned]);

  // ── Six cards, each with a live line ──
  // Next of the user's own reports, as "NFLX Tue, META Wed".
  const nextReports = myEarnings.slice(0, 2).map(e => {
    const d = new Date(`${e.date || e.reportDate}T12:00:00`);
    return `${e.symbol} ${d.toLocaleDateString('en-US', { weekday: 'short' })}`;
  }).join(', ');
  const loaded = !!user && watchlist !== null && jobs !== null;

  // Each tile's second line is live state — what's there right now — rather
  // than a tagline describing the tool.
  const cards: CardSpec[] = [
    {
      key: 'assistant', title: 'Ask Finch', icon: Sparkles, href: '/(tabs)/chat',
      line: openIdeas.length > 0 ? `${openIdeas.length} idea${openIdeas.length > 1 ? 's' : ''} waiting` : 'Ask about anything',
      attention: openIdeas.length > 0,
    },
    {
      key: 'screener', title: 'Screener', icon: SlidersHorizontal, href: '/screener',
      line: 'Describe the stocks you want',
    },
    {
      key: 'trader', title: 'Trader', icon: Zap, href: '/trader',
      line: pending.length > 0
        ? `${pending.length} trade${pending.length > 1 ? 's' : ''} to approve`
        : jobs === null ? 'Approvals and automations' : 'Nothing to approve',
      attention: pending.length > 0,
    },
    {
      key: 'financials', title: 'Financials', icon: FileText, href: '/research',
      line: 'Statements and filings',
    },
    {
      key: 'calendar', title: 'Calendar', icon: CalendarDays, href: '/calendar',
      line: earnings === null || (user && watchlist === null)
        ? 'Earnings and Finch’s schedule'
        : nextReports || `${earnings.length || 'No'} reports this week`,
      attention: myEarnings.some(e => dayDiff(e.date || e.reportDate) <= 1),
    },
    {
      key: 'watching', title: 'Watching', icon: Eye, href: '/watching',
      line: loaded
        ? `${watchlist!.length} stock${watchlist!.length === 1 ? '' : 's'}, ${theses.length} thes${theses.length === 1 ? 'is' : 'es'}`
        : 'Stocks, theses and checks',
    },
  ];

  const cols = width >= 700 ? 3 : 2;
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
              {status ? <Text style={styles.status}>{status}</Text> : null}
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
          ) : (
            // The one bold surface on the page: Finch speaking. Everything below is quiet.
            <View style={styles.brief}>
              <View style={styles.briefMark}><FinchLogo size={26} /></View>
              <View style={{ flex: 1 }}>
                {loading ? (
                  <View style={{ gap: 8, paddingTop: 4 }}>
                    <Skeleton width={'85%' as any} height={16} radius={4} />
                    <Skeleton width={'60%' as any} height={14} radius={4} />
                  </View>
                ) : brief.length === 0 ? (
                  <Text style={styles.quiet}>
                    {mySymbols.size > 0
                      ? `Nothing needs you right now. I'm watching ${mySymbols.size} stock${mySymbols.size === 1 ? '' : 's'} and will tell you if something changes.`
                      : 'Add a few stocks to Watching or connect a brokerage, and I\'ll start keeping an eye on them for you.'}
                  </Text>
                ) : (
                  brief.map((b, i) => (
                    <TouchableOpacity key={b.key} onPress={b.onPress} activeOpacity={0.7} style={[styles.briefItem, i > 0 && styles.briefDivider]}>
                      {b.thesis && b.thesis !== 'intact' ? (
                        <Text style={[styles.tag, { color: THESIS_STATUS_META[b.thesis].fg }]}>{THESIS_STATUS_META[b.thesis].label}</Text>
                      ) : b.verdict && b.verdict !== 'noise' ? (
                        <Text style={[styles.tag, { color: VERDICT_META[b.verdict].fg }]}>{VERDICT_META[b.verdict].label}</Text>
                      ) : null}
                      <Text style={styles.briefTitle}>{b.title}</Text>
                      {b.body ? <Text style={styles.briefBody} numberOfLines={3}>{b.body}</Text> : null}
                      {b.cta ? (
                        <View style={[styles.cta, b.tone === 'action' && styles.ctaAction]}>
                          <Text style={[styles.ctaText, b.tone === 'action' && { color: '#fff' }]}>{b.cta}</Text>
                        </View>
                      ) : null}
                    </TouchableOpacity>
                  ))
                )}
                {!loading && recap?.next_run?.run_at && (
                  <Text style={styles.nextRun}>
                    Next check: {recap.next_run.name.toLowerCase()}, {new Date(recap.next_run.run_at).toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}
                  </Text>
                )}
              </View>
            </View>
          )}

          {/* The six tools: one quiet panel, hairline dividers, monochrome icons.
              Emerald only where something needs the user. */}
          <View style={styles.panel}>
            {cards.map((c, i) => {
              const Icon = c.icon;
              const lastRow = i >= cards.length - (cards.length % cols || cols);
              const lastCol = (i + 1) % cols === 0;
              return (
                <TouchableOpacity
                  key={c.key}
                  testID={`home-card-${c.key}`}
                  onPress={() => { Haptics.selectionAsync(); router.push(c.href as any); }}
                  activeOpacity={0.6}
                  style={[styles.tile, { width: `${100 / cols}%` as any }, !lastRow && styles.tileBottom, !lastCol && styles.tileRight]}
                >
                  <View style={styles.tileHead}>
                    <Icon size={17} color={c.attention ? COLORS.emerald : '#57534e'} strokeWidth={1.9} />
                    {c.attention && <View style={styles.attnDot} />}
                  </View>
                  <Text style={styles.tileTitle}>{c.title}</Text>
                  <Text style={[styles.tileLine, c.attention && styles.tileLineOn]} numberOfLines={2}>{c.line}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {/* Market line — a glance; tap for the full markets view */}
          <TouchableOpacity onPress={() => router.push('/markets')} activeOpacity={0.6} style={styles.pulse}>
            {PULSE.map(p => {
              const chg = pulse[p.symbol]?.changesPercentage;
              return (
                <Text key={p.symbol} style={styles.pulseItem}>
                  {p.label}{' '}
                  <Text style={{ color: chg == null ? COLORS.gray400 : chg >= 0 ? COLORS.emerald : COLORS.red, fontFamily: 'DMSans-Bold' }}>
                    {chg == null ? '—' : formatPct(chg)}
                  </Text>
                </Text>
              );
            })}
            <View style={{ marginLeft: 'auto' }}><ChevronRight size={15} color={COLORS.gray400} /></View>
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
  status: { fontFamily: 'DMSans-Medium', fontSize: 12, color: COLORS.gray500 },
  hello: { fontFamily: 'DMSans-Bold', fontSize: 28, color: '#1c1917', letterSpacing: -0.7, marginTop: 4 },
  iconBtn: { width: 38, height: 38, alignItems: 'center', justifyContent: 'center' },
  badge: { position: 'absolute', top: 4, right: 3, minWidth: 16, height: 16, borderRadius: 8, backgroundColor: COLORS.red, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 3 },
  badgeText: { color: '#fff', fontSize: 9.5, fontFamily: 'DMSans-Bold' },

  book: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, paddingHorizontal: 16, paddingVertical: 14, marginBottom: 10 },
  bookLabel: { fontFamily: 'DMSans-Medium', fontSize: 12, color: COLORS.gray500 },
  bookValue: { fontFamily: 'DMSans-Bold', fontSize: 26, color: COLORS.gray900, letterSpacing: -0.6, marginTop: 2, fontVariant: ['tabular-nums'] },
  bookChange: { fontFamily: 'DMSans-Bold', fontSize: 16, fontVariant: ['tabular-nums'] },
  bookSub: { fontFamily: 'DMSans', fontSize: 11.5, color: COLORS.gray400 },

  brief: { flexDirection: 'row', gap: 12, backgroundColor: '#fff', borderRadius: 22, padding: 18, marginBottom: 18,
    shadowColor: '#1c1917', shadowOpacity: 0.06, shadowRadius: 18, shadowOffset: { width: 0, height: 6 }, elevation: 2 },
  briefMark: { paddingTop: 2 },
  briefItem: { paddingVertical: 10 },
  briefDivider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: '#e7e5e4' },
  tag: { fontFamily: 'DMSans-Bold', fontSize: 12.5, marginBottom: 2 },
  briefTitle: { fontFamily: 'DMSans-Bold', fontSize: 17, color: '#1c1917', lineHeight: 23, letterSpacing: -0.2 },
  briefBody: { fontFamily: 'DMSans', fontSize: 14.5, color: '#57534e', lineHeight: 21, marginTop: 3 },
  cta: { alignSelf: 'flex-start', paddingHorizontal: 14, paddingVertical: 7, borderRadius: 999, backgroundColor: '#ecfdf5', marginTop: 10 },
  ctaAction: { backgroundColor: COLORS.emerald },
  ctaText: { fontFamily: 'DMSans-Bold', fontSize: 13, color: '#047857' },
  quiet: { fontFamily: 'DMSans-Medium', fontSize: 16, color: '#1c1917', lineHeight: 23, paddingVertical: 4 },
  nextRun: { fontFamily: 'DMSans', fontSize: 12.5, color: '#a8a29e', marginTop: 10 },

  guest: { backgroundColor: '#fff', borderRadius: 18, borderWidth: 1, borderColor: '#d1fae5', padding: 18, marginBottom: 14 },
  guestTitle: { fontFamily: 'DMSans-Bold', fontSize: 18, color: COLORS.gray900, lineHeight: 24, letterSpacing: -0.3 },
  guestBody: { fontFamily: 'DMSans', fontSize: 14, color: COLORS.gray500, lineHeight: 20, marginTop: 6 },
  guestBtn: { alignSelf: 'flex-start', backgroundColor: COLORS.emerald, borderRadius: 999, paddingHorizontal: 18, paddingVertical: 10, marginTop: 14 },
  guestBtnText: { color: '#fff', fontFamily: 'DMSans-Bold', fontSize: 14 },

  panel: { flexDirection: 'row', flexWrap: 'wrap', backgroundColor: '#fff', borderRadius: 18, borderWidth: StyleSheet.hairlineWidth, borderColor: '#e7e5e4', overflow: 'hidden' },
  tile: { paddingHorizontal: 16, paddingVertical: 16, minHeight: 104 },
  tileBottom: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: '#e7e5e4' },
  tileRight: { borderRightWidth: StyleSheet.hairlineWidth, borderRightColor: '#e7e5e4' },
  tileHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  attnDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#10b981' },
  tileTitle: { fontFamily: 'DMSans-Bold', fontSize: 15.5, color: '#1c1917', marginTop: 12, letterSpacing: -0.1 },
  tileLine: { fontFamily: 'DMSans', fontSize: 13, color: '#78716c', marginTop: 2, lineHeight: 18 },
  tileLineOn: { color: '#047857', fontFamily: 'DMSans-Medium' },

  pulse: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: 4, paddingVertical: 14, marginTop: 4 },
  pulseItem: { fontFamily: 'DMSans-Medium', fontSize: 13, color: '#78716c', fontVariant: ['tabular-nums'] },
});
