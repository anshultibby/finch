import React, { useCallback, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, useRouter, useFocusEffect } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Markdown from 'react-native-markdown-display';
import { ArrowLeft, CalendarClock, MessagesSquare } from 'lucide-react-native';
import { tasksApi, type AgentTask } from '@/lib/api';
import { reviewLabel } from './index';

const STATUS_TONE: Record<string, { fg: string; bg: string; label: string }> = {
  open: { fg: '#047857', bg: '#ecfdf5', label: 'OPEN' },
  blocked: { fg: '#b45309', bg: '#fffbeb', label: 'BLOCKED' },
  done: { fg: '#6b7280', bg: '#f3f4f6', label: 'DONE' },
  dropped: { fg: '#9ca3af', bg: '#f3f4f6', label: 'DROPPED' },
};

const mdStyles = {
  body: { color: '#4b5563', fontSize: 14, lineHeight: 21, fontFamily: 'DMSans' },
  heading1: { color: '#111827', fontSize: 18, fontFamily: 'DMSans-Bold', marginTop: 14, marginBottom: 6 },
  heading2: { color: '#111827', fontSize: 15.5, fontFamily: 'DMSans-Bold', marginTop: 16, marginBottom: 5 },
  heading3: { color: '#374151', fontSize: 14, fontFamily: 'DMSans-Medium', marginTop: 12, marginBottom: 4 },
  bullet_list: { marginVertical: 4 },
  code_inline: { backgroundColor: '#f3f4f6', color: '#111827', fontSize: 12.5 },
  fence: { backgroundColor: '#f9fafb', borderColor: '#e5e7eb', borderWidth: 1, borderRadius: 8 },
};

export default function TaskDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [task, setTask] = useState<AgentTask | null>(null);
  const [missing, setMissing] = useState(false);

  const load = useCallback(async () => {
    if (!slug) return;
    try {
      setTask(await tasksApi.get(slug));
    } catch {
      setMissing(true);
    }
  }, [slug]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (missing) {
    return (
      <View style={{ flex: 1, backgroundColor: '#fafaf9', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 }}>
        <Text style={{ fontSize: 15, fontFamily: 'DMSans-Medium', color: '#111827', marginBottom: 6 }}>Task not found</Text>
        <TouchableOpacity onPress={() => router.back()} activeOpacity={0.7}>
          <Text style={{ fontSize: 13.5, fontFamily: 'DMSans-Medium', color: '#059669' }}>Go back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!task) {
    return (
      <View style={{ flex: 1, backgroundColor: '#fafaf9', alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color="#059669" />
      </View>
    );
  }

  const tone = STATUS_TONE[task.status] || STATUS_TONE.open;
  const review = reviewLabel(task.review_on);
  // Frontmatter is machine state — the reader wants the note, not the metadata.
  const body = (task.body || '').replace(/^---[\s\S]*?---\n/, '');

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: '#fafaf9' }}
      contentContainerStyle={{ padding: 16, paddingTop: insets.top + 8, paddingBottom: insets.bottom + 32 }}
    >
      <TouchableOpacity
        onPress={() => router.back()}
        activeOpacity={0.7}
        style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 14 }}
      >
        <ArrowLeft size={18} color="#6b7280" />
        <Text style={{ fontSize: 14, fontFamily: 'DMSans-Medium', color: '#6b7280' }}>Tasks</Text>
      </TouchableOpacity>

      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
        <View style={{ paddingHorizontal: 7, paddingVertical: 3, borderRadius: 6, backgroundColor: tone.bg }}>
          <Text style={{ fontSize: 10, fontFamily: 'DMSans-Bold', color: tone.fg, letterSpacing: 0.5 }}>{tone.label}</Text>
        </View>
        {task.symbols.map(sym => (
          <TouchableOpacity
            key={sym}
            activeOpacity={0.7}
            onPress={() => router.push(`/stock/${sym}` as any)}
            style={{ paddingHorizontal: 6, paddingVertical: 3, borderRadius: 5, backgroundColor: '#ecfdf5' }}
          >
            <Text style={{ fontSize: 10.5, fontFamily: 'DMSans-Bold', color: '#047857' }}>{sym}</Text>
          </TouchableOpacity>
        ))}
        {review && (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
            <CalendarClock size={11} color={review.overdue ? '#b45309' : '#9ca3af'} />
            <Text style={{ fontSize: 11.5, fontFamily: 'DMSans', color: review.overdue ? '#b45309' : '#6b7280' }}>
              {review.text}
            </Text>
          </View>
        )}
      </View>

      <Text style={{ fontSize: 20, fontFamily: 'DMSans-Bold', color: '#111827', lineHeight: 27, marginBottom: 4 }}>
        {task.title}
      </Text>
      {task.opened_on && (
        <Text style={{ fontSize: 12, fontFamily: 'DMSans', color: '#9ca3af', marginBottom: 10 }}>
          Opened {task.opened_on}
        </Text>
      )}

      <View style={{ backgroundColor: '#fff', borderRadius: 14, borderWidth: 1, borderColor: '#e5e7eb', padding: 16, marginTop: 6 }}>
        <Markdown style={mdStyles}>{body}</Markdown>
      </View>

      {task.chat_id && (
        <TouchableOpacity
          activeOpacity={0.7}
          onPress={() => router.push(`/(tabs)?tab=chat&chatId=${task.chat_id}` as any)}
          style={{ flexDirection: 'row', alignItems: 'center', gap: 7, marginTop: 14, paddingVertical: 6 }}
        >
          <MessagesSquare size={14} color="#059669" />
          <Text style={{ fontSize: 13.5, fontFamily: 'DMSans-Medium', color: '#059669' }}>
            Open the conversation this came from
          </Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}
