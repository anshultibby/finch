import React, { useCallback, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, RefreshControl, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { ChevronRight, Pause, Play, ShieldCheck, Activity as ActivityIcon } from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import {
  pendingTradesApi, ideasApi, jobsApi, accountApi,
  type PendingTradeItem, type TradeIdea, type IdeaScorecard, type ScheduledJob,
} from '@/lib/api';
import { COLORS, formatCurrency, formatPct } from '@/lib/constants';
import ScreenHeader from '@/components/ui/ScreenHeader';
import ApprovalCard from '@/components/activity/ApprovalCard';
import AgentTabView from '@/components/AgentTabView';
import SignInPrompt from '@/components/SignInPrompt';

// The trust surface. Nothing executes without the user: approvals are
// hold-to-confirm, Finch's calls are graded against SPY whether or not they
// were taken, and one switch pauses every automation.

export default function TraderScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [pending, setPending] = useState<PendingTradeItem[]>([]);
  const [decided, setDecided] = useState<Record<string, string>>({});
  const [ideas, setIdeas] = useState<TradeIdea[]>([]);
  const [score, setScore] = useState<IdeaScorecard | null>(null);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [requireApproval, setRequireApproval] = useState<boolean | null>(null);

  const load = useCallback(async () => {
    if (!user) return;
    await Promise.all([
      pendingTradesApi.list().then(d => setPending(d.pending_trades || [])).catch(() => {}),
      ideasApi.list(50).then(d => { setIdeas(d.ideas || []); setScore(d.scorecard); }).catch(() => {}),
      jobsApi.list().then(d => setJobs(d.jobs || [])).catch(() => {}),
      accountApi.getPreferences(user.id).then(p => setRequireApproval(p.require_trade_approval)).catch(() => {}),
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
        <ScreenHeader title="Trader" />
        <SignInPrompt
          title="Meet your trading agent"
          description="Sign in to let Finch propose trades, grade its own calls, and act only with your approval."
        />
      </SafeAreaView>
    );
  }

  const live = pending.filter(t => !decided[t.id] && (!t.expires_at || new Date(t.expires_at).getTime() > Date.now()));
  const openIdeas = ideas.filter(i => i.status === 'proposed' && i.outcome === 'pending');
  const running = jobs.filter(j => j.status === 'pending' || j.status === 'running');
  const paused = jobs.filter(j => j.status === 'paused');

  const toggleAll = async () => {
    const pausing = running.length > 0;
    const go = async () => {
      setToggling(true);
      try {
        await (pausing ? jobsApi.pauseAll() : jobsApi.resumeAll());
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        await load();
      } catch {
        Alert.alert('Something went wrong', 'Please try again.');
      } finally {
        setToggling(false);
      }
    };
    if (pausing) {
      Alert.alert('Pause everything?', `Stops all ${running.length} automations, including any that can propose trades. You can resume anytime.`, [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Pause all', style: 'destructive', onPress: go },
      ]);
    } else {
      go();
    }
  };

  const decideIdea = (idea: TradeIdea) => {
    Alert.alert(`${idea.direction === 'long' ? 'Buy' : 'Short'} ${idea.symbol}?`, idea.thesis, [
      { text: 'Pass', style: 'destructive', onPress: () => ideasApi.decide(idea.id, false).then(load).catch(() => {}) },
      { text: "I'll place it myself", onPress: () => ideasApi.decide(idea.id, true, 'manual').then(load).catch(() => {}) },
      { text: 'Cancel', style: 'cancel' },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScreenHeader title="Trader" subtitle={requireApproval === false ? 'Unattended trading is on' : 'Nothing executes without you'} />
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
        showsVerticalScrollIndicator={false}
      >
        {/* Kill switch */}
        <View style={styles.killRow}>
          <ShieldCheck size={18} color={running.length > 0 ? COLORS.emerald : COLORS.gray400} />
          <View style={{ flex: 1 }}>
            <Text style={styles.killTitle}>
              {running.length > 0 ? `${running.length} automation${running.length > 1 ? 's' : ''} running` : paused.length > 0 ? 'Everything paused' : 'No automations yet'}
            </Text>
            <TouchableOpacity onPress={() => router.push('/settings')} activeOpacity={0.7}>
              <Text style={[styles.killSub, requireApproval === false && { color: COLORS.red }]}>
                {requireApproval === false ? 'Approvals are OFF — Finch can trade without asking' : 'Approval required for every trade'}
              </Text>
            </TouchableOpacity>
          </View>
          {(running.length > 0 || paused.length > 0) && (
            <TouchableOpacity onPress={toggleAll} disabled={toggling} style={[styles.killBtn, running.length > 0 && styles.killBtnStop]} activeOpacity={0.8}>
              {toggling ? <ActivityIndicator size="small" color={running.length > 0 ? COLORS.red : COLORS.emerald} />
                : running.length > 0 ? <Pause size={14} color={COLORS.red} /> : <Play size={14} color={COLORS.emerald} />}
              <Text style={[styles.killBtnText, { color: running.length > 0 ? COLORS.red : COLORS.emerald }]}>
                {running.length > 0 ? 'Pause all' : 'Resume'}
              </Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Approvals */}
        <Text style={styles.section}>Waiting on you</Text>
        {live.length === 0 ? (
          <Text style={styles.empty}>No trades waiting. When Finch wants to act, it'll ask here first — and ping you.</Text>
        ) : (
          live.map(t => <ApprovalCard key={t.id} trade={t} onDecided={(id, status) => setDecided(d => ({ ...d, [id]: status }))} />)
        )}

        {/* Finch's calls + scorecard */}
        <Text style={styles.section}>Finch's calls</Text>
        {score && score.scored > 0 && (
          <View style={styles.scoreCard}>
            <Stat label="Hit rate" value={score.hit_rate != null ? `${Math.round(score.hit_rate * 100)}%` : '—'} />
            <Stat label="Avg vs SPY" value={formatPct(score.avg_alpha_pct)} color={(score.avg_alpha_pct ?? 0) >= 0 ? COLORS.emerald : COLORS.red} />
            <Stat label="Graded" value={`${score.scored}`} />
          </View>
        )}
        {openIdeas.length === 0 ? (
          <Text style={styles.empty}>
            No open calls. Finch proposes ideas when a catalyst lines up with your goal — every one is graded against the S&P 500, taken or not.
          </Text>
        ) : (
          <View style={styles.list}>
            {openIdeas.map((i, idx) => (
              <TouchableOpacity key={i.id} onPress={() => decideIdea(i)} style={[styles.ideaRow, idx > 0 && styles.divider]} activeOpacity={0.7}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.ideaTitle}>
                    <Text style={{ color: i.direction === 'long' ? COLORS.emerald : COLORS.red }}>{i.direction === 'long' ? '▲ ' : '▼ '}</Text>
                    {i.symbol} · conviction {i.conviction}/5
                  </Text>
                  <Text style={styles.ideaBody} numberOfLines={2}>{i.catalyst_summary}</Text>
                  <Text style={styles.ideaLevels}>
                    Entry {formatCurrency(i.entry_ref)} · Target {formatCurrency(i.target)} · Stop {formatCurrency(i.stop)} · {i.horizon_days}d
                  </Text>
                </View>
                <ChevronRight size={16} color={COLORS.gray400} />
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* The agent's own account */}
        <Text style={styles.section}>Agent account</Text>
        <AgentTabView userId={user.id} />

        <TouchableOpacity onPress={() => router.push('/activity')} style={styles.linkRow} activeOpacity={0.7}>
          <ActivityIcon size={16} color={COLORS.gray500} />
          <Text style={styles.linkText}>Full activity log</Text>
          <ChevronRight size={16} color={COLORS.gray400} />
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <View style={{ flex: 1 }}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, color ? { color } : null]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fafaf9' },
  scroll: { paddingHorizontal: 16, paddingBottom: 40, maxWidth: 760, width: '100%', alignSelf: 'center' },
  killRow: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, padding: 14 },
  killTitle: { fontFamily: 'DMSans-Bold', fontSize: 15, color: COLORS.gray900 },
  killSub: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.gray500, marginTop: 1 },
  killBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, backgroundColor: '#ecfdf5' },
  killBtnStop: { backgroundColor: '#fef2f2' },
  killBtnText: { fontFamily: 'DMSans-Bold', fontSize: 13 },
  section: { fontFamily: 'DMSans-Bold', fontSize: 15, color: '#1c1917', marginTop: 22, marginBottom: 8 },
  empty: { fontFamily: 'DMSans', fontSize: 13.5, color: COLORS.gray500, lineHeight: 19 },
  scoreCard: { flexDirection: 'row', backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, padding: 14, marginBottom: 10 },
  statLabel: { fontFamily: 'DMSans-Medium', fontSize: 11.5, color: COLORS.gray500 },
  statValue: { fontFamily: 'DMSans-Bold', fontSize: 18, color: COLORS.gray900, marginTop: 2, fontVariant: ['tabular-nums'] },
  list: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, overflow: 'hidden' },
  ideaRow: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14 },
  divider: { borderTopWidth: 1, borderTopColor: COLORS.gray100 },
  ideaTitle: { fontFamily: 'DMSans-Bold', fontSize: 14.5, color: COLORS.gray900 },
  ideaBody: { fontFamily: 'DMSans', fontSize: 13, color: COLORS.gray700, marginTop: 3, lineHeight: 18 },
  ideaLevels: { fontFamily: 'DMSans', fontSize: 11.5, color: COLORS.gray400, marginTop: 4, fontVariant: ['tabular-nums'] },
  linkRow: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#fff', borderRadius: 14, borderWidth: 1, borderColor: COLORS.gray100, padding: 14, marginTop: 10 },
  linkText: { flex: 1, fontFamily: 'DMSans-Medium', fontSize: 14, color: COLORS.gray900 },
});
