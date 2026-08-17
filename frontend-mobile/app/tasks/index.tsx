import React, { useCallback, useMemo, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LogIn, CalendarClock, ChevronRight } from 'lucide-react-native';
import { tasksApi, type AgentTask, type TaskStatus } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

// Open work first — the board reads top-down, so the order is the priority.
const GROUPS: { status: TaskStatus; label: string; fg: string; bg: string }[] = [
  { status: 'open', label: 'OPEN', fg: '#047857', bg: '#ecfdf5' },
  { status: 'blocked', label: 'BLOCKED', fg: '#b45309', bg: '#fffbeb' },
  { status: 'done', label: 'DONE', fg: '#6b7280', bg: '#f3f4f6' },
  { status: 'dropped', label: 'DROPPED', fg: '#9ca3af', bg: '#f3f4f6' },
];

/** "Due today" / "3d overdue" — the only date framing that matters here. */
export function reviewLabel(iso: string | null): { text: string; overdue: boolean } | null {
  if (!iso) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(`${iso}T00:00:00`);
  const days = Math.round((due.getTime() - today.getTime()) / 86_400_000);
  if (days < 0) return { text: `${Math.abs(days)}d overdue`, overdue: true };
  if (days === 0) return { text: 'Due today', overdue: true };
  if (days === 1) return { text: 'Due tomorrow', overdue: false };
  if (days <= 14) return { text: `Due in ${days}d`, overdue: false };
  return { text: `Due ${due.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`, overdue: false };
}

export default function TasksListScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const [tasks, setTasks] = useState<AgentTask[] | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [showClosed, setShowClosed] = useState(false);

  const load = useCallback(async () => {
    if (!user) { setTasks([]); return; }
    try {
      setTasks((await tasksApi.list()).tasks);
    } catch {
      setTasks([]);
    }
  }, [user]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const grouped = useMemo(() => {
    const by = new Map<TaskStatus, AgentTask[]>();
    for (const t of tasks || []) {
      if (!by.has(t.status)) by.set(t.status, []);
      by.get(t.status)!.push(t);
    }
    return by;
  }, [tasks]);

  if (!user) {
    return (
      <View style={{ flex: 1, backgroundColor: '#fafaf9', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 }}>
        <Text style={{ fontSize: 40, marginBottom: 12 }}>🗂️</Text>
        <Text style={{ fontSize: 17, fontFamily: 'DMSans-Bold', color: '#111827', marginBottom: 6 }}>Tasks</Text>
        <Text style={{ fontSize: 13.5, fontFamily: 'DMSans', color: '#6b7280', textAlign: 'center', marginBottom: 20, lineHeight: 19 }}>
          Sign in to see what Finch is working on across sessions — theses it's tracking, catalysts it's waiting on.
        </Text>
        <TouchableOpacity
          onPress={() => router.push('/(auth)/login')}
          style={{ flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#059669', paddingHorizontal: 20, paddingVertical: 11, borderRadius: 12 }}
          activeOpacity={0.85}
        >
          <LogIn size={16} color="#fff" />
          <Text style={{ fontSize: 14, fontFamily: 'DMSans-Medium', color: '#fff' }}>Sign in</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (tasks === null) {
    return (
      <View style={{ flex: 1, backgroundColor: '#fafaf9', alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color="#059669" />
      </View>
    );
  }

  const visibleGroups = GROUPS.filter(g =>
    (showClosed || (g.status !== 'done' && g.status !== 'dropped')) &&
    (grouped.get(g.status) || []).length > 0
  );
  const hasClosed = (grouped.get('done') || []).length + (grouped.get('dropped') || []).length > 0;

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: '#fafaf9' }}
      contentContainerStyle={{ padding: 16, paddingBottom: insets.bottom + 24 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#059669" />}
    >
      {tasks.length === 0 ? (
        <View style={{ alignItems: 'center', justifyContent: 'center', paddingTop: 96, paddingHorizontal: 24 }}>
          <Text style={{ fontSize: 40, marginBottom: 12 }}>🗂️</Text>
          <Text style={{ fontSize: 17, fontFamily: 'DMSans-Bold', color: '#111827', marginBottom: 6 }}>No tasks yet</Text>
          <Text style={{ fontSize: 13.5, fontFamily: 'DMSans', color: '#6b7280', textAlign: 'center', lineHeight: 19 }}>
            When Finch takes on work that spans more than one sitting — tracking a thesis, watching for a catalyst — it files it here.
          </Text>
        </View>
      ) : (
        <View style={{ gap: 18 }}>
          {visibleGroups.map(group => (
            <View key={group.status}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <View style={{ paddingHorizontal: 7, paddingVertical: 3, borderRadius: 6, backgroundColor: group.bg }}>
                  <Text style={{ fontSize: 10, fontFamily: 'DMSans-Bold', color: group.fg, letterSpacing: 0.5 }}>
                    {group.label}
                  </Text>
                </View>
                <Text style={{ fontSize: 12, fontFamily: 'DMSans', color: '#9ca3af' }}>
                  {(grouped.get(group.status) || []).length}
                </Text>
              </View>

              <View style={{ gap: 8 }}>
                {(grouped.get(group.status) || []).map(task => {
                  const review = reviewLabel(task.review_on);
                  return (
                    <TouchableOpacity
                      key={task.id}
                      activeOpacity={0.7}
                      onPress={() => router.push(`/tasks/${task.slug}` as any)}
                      style={{
                        flexDirection: 'row', alignItems: 'center', gap: 10,
                        backgroundColor: '#fff', borderRadius: 14, borderWidth: 1,
                        borderColor: '#e5e7eb', padding: 14,
                      }}
                    >
                      <View style={{ flex: 1, minWidth: 0 }}>
                        <Text style={{ fontSize: 14.5, fontFamily: 'DMSans-Medium', color: '#111827', lineHeight: 20 }} numberOfLines={3}>
                          {task.title}
                        </Text>
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                          {task.symbols.slice(0, 3).map(sym => (
                            <View key={sym} style={{ paddingHorizontal: 6, paddingVertical: 2, borderRadius: 5, backgroundColor: '#ecfdf5' }}>
                              <Text style={{ fontSize: 10.5, fontFamily: 'DMSans-Bold', color: '#047857' }}>{sym}</Text>
                            </View>
                          ))}
                          {review && (
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
                              <CalendarClock size={11} color={review.overdue ? '#b45309' : '#9ca3af'} />
                              <Text style={{ fontSize: 11.5, fontFamily: review.overdue ? 'DMSans-Medium' : 'DMSans', color: review.overdue ? '#b45309' : '#6b7280' }}>
                                {review.text}
                              </Text>
                            </View>
                          )}
                        </View>
                      </View>
                      <ChevronRight size={16} color="#d1d5db" />
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
          ))}

          {hasClosed && (
            <TouchableOpacity onPress={() => setShowClosed(s => !s)} activeOpacity={0.7} style={{ paddingVertical: 8, alignItems: 'center' }}>
              <Text style={{ fontSize: 13, fontFamily: 'DMSans-Medium', color: '#6b7280' }}>
                {showClosed ? 'Hide closed' : 'Show closed'}
              </Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    </ScrollView>
  );
}
