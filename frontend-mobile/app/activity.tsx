import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, FlatList, ActivityIndicator, RefreshControl, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Stack, useRouter } from 'expo-router';
import { Activity as ActivityIcon } from 'lucide-react-native';
import { activityApi, pendingTradesApi, AgentEvent, PendingTradeItem } from '@/lib/api';
import ApprovalCard from '@/components/activity/ApprovalCard';
import { COLORS, formatRelativeTime } from '@/lib/constants';

const TYPE_DOTS: Record<string, string> = {
  job_run: '#10b981',
  alert: '#f59e0b',
  trade_proposed: '#059669',
  trade_decided: '#9ca3af',
  brief: '#0ea5e9',
  insight: '#8b5cf6',
};

/**
 * The agent's full ledger: every check, alert, brief, and trade decision —
 * append-only and honest, including runs where nothing needed attention.
 * Pending approvals pin to the top; push notifications deep-link here.
 */
export default function ActivityScreen() {
  const router = useRouter();
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [pending, setPending] = useState<PendingTradeItem[]>([]);
  const [decided, setDecided] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [feed, pt] = await Promise.all([
        activityApi.getFeed(50),
        pendingTradesApi.list(),
      ]);
      setEvents(feed.events || []);
      setPending(pt.pending_trades || []);
      activityApi.markSeen().catch(() => {});
    } catch {} finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const onDecided = useCallback((id: string, status: string) => {
    setDecided(d => ({ ...d, [id]: status }));
  }, []);

  const openEvent = useCallback((e: AgentEvent) => {
    const chatId = e.data?.chat_id as string | undefined;
    const symbol = e.data?.symbol as string | undefined;
    if (chatId) router.push(`/(tabs)/chat/${chatId}`);
    else if (symbol) router.push(`/stock/${symbol}`);
  }, [router]);

  const livePending = pending.filter(t => !decided[t.id]);

  return (
    <>
      <Stack.Screen options={{ headerTitle: 'Agent Activity', headerStyle: { backgroundColor: '#fff' } }} />
      <SafeAreaView style={{ flex: 1, backgroundColor: '#fff' }} edges={['bottom']}>
        {loading ? (
          <View className="flex-1 items-center justify-center">
            <ActivityIndicator color={COLORS.gray400} />
          </View>
        ) : (
          <FlatList
            data={events}
            keyExtractor={item => item.id}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
            contentContainerStyle={{ padding: 16, paddingBottom: 32 }}
            ListHeaderComponent={
              <>
                {livePending.map(t => (
                  <ApprovalCard key={t.id} trade={t} onDecided={onDecided} />
                ))}
                {pending.filter(t => decided[t.id]).map(t => (
                  <View
                    key={t.id}
                    className={`rounded-xl px-3 py-2 mb-3 ${decided[t.id] === 'approved' ? 'bg-emerald-50' : 'bg-gray-50'}`}
                  >
                    <Text className={`text-xs font-body-bold ${decided[t.id] === 'approved' ? 'text-emerald-700' : 'text-gray-500'}`}>
                      {decided[t.id] === 'approved' ? '✓ Order sent to Robinhood — ' : 'Rejected — no order placed. '}
                      {t.summary}
                    </Text>
                  </View>
                ))}
              </>
            }
            renderItem={({ item }) => {
              const clickable = Boolean(item.data?.chat_id || item.data?.symbol);
              return (
                <TouchableOpacity
                  onPress={() => openEvent(item)}
                  disabled={!clickable}
                  activeOpacity={0.6}
                  className="flex-row py-2.5"
                  style={{ gap: 12 }}
                >
                  <View className="items-center pt-1.5">
                    <View
                      style={{
                        width: 8, height: 8, borderRadius: 4,
                        backgroundColor: TYPE_DOTS[item.event_type] || '#d1d5db',
                      }}
                    />
                    <View style={{ width: 1, flex: 1, backgroundColor: '#f3f4f6', marginTop: 4 }} />
                  </View>
                  <View className="flex-1">
                    <View className="flex-row justify-between items-baseline" style={{ gap: 8 }}>
                      <Text className="text-[13px] font-body-bold text-gray-800 flex-1" numberOfLines={1}>
                        {item.title}
                      </Text>
                      <Text className="text-[11px] font-body text-gray-400">
                        {item.value_cents ? (
                          <Text className="font-body-bold text-gray-600">
                            ${Math.round(item.value_cents / 100).toLocaleString()}{'  '}
                          </Text>
                        ) : null}
                        {formatRelativeTime(item.created_at)}
                      </Text>
                    </View>
                    {!!item.body && (
                      <Text className="text-xs font-body text-gray-500 mt-0.5" numberOfLines={2}>
                        {item.body}
                      </Text>
                    )}
                  </View>
                </TouchableOpacity>
              );
            }}
            ListEmptyComponent={
              livePending.length === 0 ? (
                <View className="py-20 items-center">
                  <ActivityIcon size={48} color="#e5e7eb" />
                  <Text className="text-base font-body-bold text-gray-400 mt-4">No activity yet</Text>
                  <Text className="text-[13px] font-body text-gray-300 text-center mt-1.5 px-10 leading-[18px]">
                    Every check, alert, and trade your agent makes will be recorded here.
                  </Text>
                </View>
              ) : null
            }
          />
        )}
      </SafeAreaView>
    </>
  );
}
