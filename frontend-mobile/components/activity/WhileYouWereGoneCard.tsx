import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withSequence, withTiming } from 'react-native-reanimated';
import { useRouter } from 'expo-router';
import { ChevronRight } from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { activityApi, ActivityRecap, AgentEvent } from '@/lib/api';
import ApprovalCard from './ApprovalCard';
import { formatRelativeTime } from '@/lib/constants';

const TYPE_DOTS: Record<string, string> = {
  job_run: '#10b981',
  alert: '#f59e0b',
  trade_proposed: '#059669',
  trade_decided: '#9ca3af',
  brief: '#0ea5e9',
  insight: '#8b5cf6',
};

function timeUntil(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return 'any moment';
  const m = Math.round(ms / 60000);
  if (m < 60) return `in ${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `in ${h}h ${m % 60}m`;
  return new Date(iso).toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' });
}

/** The agent, live: a job is executing right now. One tap lands in the run
 *  chat where the full activity trail is streaming. */
function RunningStrip({ run, onOpen }: {
  run: NonNullable<ActivityRecap['running_now']>;
  onOpen: () => void;
}) {
  const pulse = useSharedValue(1);
  useEffect(() => {
    pulse.value = withRepeat(
      withSequence(withTiming(0.35, { duration: 700 }), withTiming(1, { duration: 700 })),
      -1,
    );
  }, [pulse]);
  const dotStyle = useAnimatedStyle(() => ({ opacity: pulse.value }));

  const startedMin = run.started_at
    ? Math.max(0, Math.round((Date.now() - new Date(run.started_at).getTime()) / 60000))
    : null;

  return (
    <TouchableOpacity
      onPress={onOpen}
      disabled={!run.chat_id}
      activeOpacity={0.75}
      className="flex-row items-center rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2.5 mb-2.5"
      style={{ gap: 8 }}
    >
      <Animated.View style={[{ width: 7, height: 7, borderRadius: 4, backgroundColor: '#10b981' }, dotStyle]} />
      <Text className="text-xs font-body-bold text-emerald-800 flex-1" numberOfLines={1}>
        Working now: {run.name}
        {startedMin !== null ? ` · ${startedMin === 0 ? 'just started' : `${startedMin}m in`}` : ''}
      </Text>
      {run.chat_id && <ChevronRight size={13} color="#047857" />}
    </TouchableOpacity>
  );
}

/** Ghost ledger for pre-connect users: what this surface looks like alive. */
function GhostLedger({ onConnect }: { onConnect: () => void }) {
  const sample = ['#10b981', '#f59e0b', '#059669'];
  return (
    <View className="mx-4 mt-3 mb-1 rounded-2xl bg-white border border-gray-100 p-4">
      <View className="flex-row items-center mb-2.5" style={{ gap: 6 }}>
        <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: '#d1d5db' }} />
        <Text className="text-[10px] font-body-bold text-gray-400 uppercase tracking-widest">
          Your agent&apos;s ledger
        </Text>
      </View>
      {sample.map((dot, i) => (
        <View key={i} className="flex-row items-center py-1.5" style={{ gap: 10, opacity: 0.55 }}>
          <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: dot }} />
          <View className="flex-1 h-2.5 rounded bg-gray-100" style={{ maxWidth: i === 1 ? '70%' : '85%' }} />
          <View className="w-9 h-2.5 rounded bg-gray-100" />
        </View>
      ))}
      <Text className="text-xs font-body text-gray-500 mt-2.5 leading-4">
        Every check, alert, and proposed trade Finch makes for you — with the dollars at stake — gets recorded here.
      </Text>
      <TouchableOpacity
        onPress={onConnect}
        activeOpacity={0.85}
        className="mt-3 rounded-xl bg-emerald-600 py-2.5 items-center"
      >
        <Text className="text-xs font-body-bold text-white">Connect brokerage</Text>
      </TouchableOpacity>
    </View>
  );
}

/**
 * "While you were gone" — the agent accounts for itself at the top of home:
 * what it did since the user last looked, anything waiting on approval, and
 * when it checks next. Signed-out users see nothing (guest mode untouched).
 */
export default function WhileYouWereGoneCard({
  hasBrokerage,
  onConnect,
}: {
  hasBrokerage?: boolean;
  onConnect?: () => void;
} = {}) {
  const { user } = useAuth();
  const router = useRouter();
  const [recap, setRecap] = useState<ActivityRecap | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [decided, setDecided] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    activityApi.getRecap()
      .then(r => { if (!cancelled) setRecap(r); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [user]);

  // While a run is in flight, keep the card live: the strip's elapsed time
  // ticks and the run's results land in the ledger as they're written.
  const isRunning = Boolean(recap?.running_now);
  useEffect(() => {
    if (!isRunning) return;
    const t = setInterval(() => {
      activityApi.getRecap().then(setRecap).catch(() => {});
    }, 15_000);
    return () => clearInterval(t);
  }, [isRunning]);

  const dismiss = useCallback(() => {
    setDismissed(true);
    activityApi.markSeen().catch(() => {});
  }, []);

  const onDecided = useCallback((id: string, status: string) => {
    setDecided(d => ({ ...d, [id]: status }));
  }, []);

  const openEvent = useCallback((e: AgentEvent) => {
    const chatId = e.data?.chat_id as string | undefined;
    const symbol = e.data?.symbol as string | undefined;
    if (chatId) router.push(`/(tabs)/chat/${chatId}`);
    else if (symbol) router.push(`/stock/${symbol}`);
  }, [router]);

  if (!user || !recap) return null;

  const pending = (recap.pending_trades || []).filter(t => !decided[t.id]);

  const openRun = () => {
    if (recap?.running_now?.chat_id) router.push(`/(tabs)/chat/${recap.running_now.chat_id}`);
  };

  if (!recap.has_content) {
    // A run in flight beats the quiet line — show the agent working.
    if (recap.running_now) {
      return (
        <View className="mx-4 mt-3 mb-1">
          <RunningStrip run={recap.running_now} onOpen={openRun} />
        </View>
      );
    }
    // Connected but quiet: one honest line — watching, and when it checks next.
    if (recap.next_run?.run_at) {
      return (
        <View className="px-4 mb-2 flex-row items-center" style={{ gap: 6 }}>
          <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#10b981' }} />
          <Text className="text-[11px] font-body text-gray-400">
            Finch is watching — next check ({recap.next_run.name}) {timeUntil(recap.next_run.run_at)}.
          </Text>
        </View>
      );
    }
    // Nothing set up yet: show the ghost of the ledger they'd have.
    if (hasBrokerage === false && onConnect) return <GhostLedger onConnect={onConnect} />;
    return null;
  }

  if (dismissed && pending.length === 0) return null;

  const events = (recap.events || []).slice(0, 3);

  return (
    <View className="mx-4 mt-3 mb-1 rounded-2xl bg-white border border-gray-100 overflow-hidden">
      <View className="flex-row items-center justify-between px-4 pt-3 pb-1.5">
        <View className="flex-row items-center" style={{ gap: 6 }}>
          <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: '#10b981' }} />
          <Text className="text-[10px] font-body-bold text-gray-500 uppercase tracking-widest">
            While you were gone
          </Text>
        </View>
        {!dismissed && (
          <TouchableOpacity onPress={dismiss} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Text className="text-[11px] font-body-bold text-gray-400">Caught up ✓</Text>
          </TouchableOpacity>
        )}
      </View>

      <View className="px-4 pb-3.5">
        {/* Live run — the agent is working right now; tap to watch the stream */}
        {recap.running_now && <RunningStrip run={recap.running_now} onOpen={openRun} />}

        {!dismissed && !!recap.headline && (
          <Text className="text-[15px] font-body-bold text-gray-900 leading-5 mb-2.5">
            {recap.headline}
          </Text>
        )}

        {pending.map(t => (
          <ApprovalCard key={t.id} trade={t} onDecided={onDecided} />
        ))}
        {(recap.pending_trades || []).filter(t => decided[t.id]).map(t => (
          <View
            key={t.id}
            className={`rounded-xl px-3 py-2 mb-2 ${decided[t.id] === 'approved' ? 'bg-emerald-50' : 'bg-gray-50'}`}
          >
            <Text className={`text-xs font-body-bold ${decided[t.id] === 'approved' ? 'text-emerald-700' : 'text-gray-500'}`}>
              {decided[t.id] === 'approved' ? '✓ Order sent to Robinhood — ' : 'Rejected — no order placed. '}
              {t.summary}
            </Text>
          </View>
        ))}

        {!dismissed && events.map((e, i) => (
          <TouchableOpacity
            key={e.id}
            onPress={() => openEvent(e)}
            disabled={!e.data?.chat_id && !e.data?.symbol}
            activeOpacity={0.6}
            className="flex-row py-1.5"
            style={{ gap: 10 }}
          >
            <View className="items-center pt-1.5">
              <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: TYPE_DOTS[e.event_type] || '#d1d5db' }} />
              {i < events.length - 1 && <View style={{ width: 1, flex: 1, backgroundColor: '#f3f4f6', marginTop: 3 }} />}
            </View>
            <View className="flex-1 flex-row justify-between items-baseline" style={{ gap: 8 }}>
              <Text className="text-[13px] font-body-bold text-gray-700 flex-1" numberOfLines={1}>
                {e.title}
              </Text>
              <Text className="text-[11px] font-body text-gray-400">
                {e.value_cents ? (
                  <Text className="font-body-bold text-gray-600">
                    ${Math.round(e.value_cents / 100).toLocaleString()}{'  '}
                  </Text>
                ) : null}
                {formatRelativeTime(e.created_at)}
              </Text>
            </View>
          </TouchableOpacity>
        ))}

        {!dismissed && (
          <TouchableOpacity
            onPress={() => router.push('/activity' as any)}
            className="flex-row items-center mt-1.5"
            style={{ gap: 2 }}
            activeOpacity={0.7}
          >
            <Text className="text-[11px] font-body-bold text-emerald-700">Full ledger</Text>
            <ChevronRight size={12} color="#047857" />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}
