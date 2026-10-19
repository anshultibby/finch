import React, { useCallback, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { SquarePen, ArrowUpRight, ChevronRight, ListChecks, LayoutGrid, Bot } from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { chatApi, ideasApi, watchlistApi, type TradeIdea } from '@/lib/api';
import type { UserChatsResponse } from '@/lib/types';
import { useStartChat } from '@/hooks/useStartChat';
import { COLORS, formatRelativeTime } from '@/lib/constants';
import ScreenHeader from '@/components/ui/ScreenHeader';
import SignInPrompt from '@/components/SignInPrompt';
import AskBar from '@/components/chat/AskBar';

// The assistant never opens on a blank page: Finch's own ideas first, then
// prompts shaped around the user's stocks, then the conversation history
// (which used to live in the drawer).

type ChatRow = UserChatsResponse['chats'][number];

function prompts(sym?: string) {
  const s = sym || 'NVDA';
  return [
    'What changed in my portfolio this week, and what should I do about it?',
    `Give me a bull vs. bear case on ${s} — and pick a side`,
    `Help me write my thesis on ${s} — why I own it and what would make me wrong`,
    'Review my recent trades and tell me what I keep getting wrong',
    'Show me strategies that fit my goal, and help me adopt one',
  ];
}

export default function AssistantScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const startChat = useStartChat();
  const [ideas, setIdeas] = useState<TradeIdea[]>([]);
  const [chats, setChats] = useState<ChatRow[]>([]);
  const [runs, setRuns] = useState<ChatRow[]>([]);
  const [topSymbol, setTopSymbol] = useState<string | undefined>();
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!user) return;
    await Promise.all([
      ideasApi.list(20).then(d => setIdeas((d.ideas || []).filter(i => i.status === 'proposed' && i.outcome === 'pending'))).catch(() => {}),
      chatApi.getUserChats(user.id).then(d => setChats(d.chats || [])).catch(() => {}),
      chatApi.getUserChats(user.id, { source: 'automation' }).then(d => setRuns(d.chats || [])).catch(() => {}),
      watchlistApi.getWatchlist(user.id).then(d => {
        const first = (d.symbols || d.watchlist || [])[0];
        setTopSymbol(first ? (typeof first === 'string' ? first : first.symbol) : undefined);
      }).catch(() => {}),
    ]);
  }, [user]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const deleteChat = (c: ChatRow) => {
    Alert.alert('Delete chat?', c.title || 'This conversation', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive',
        onPress: () => chatApi.deleteChat(c.chat_id).then(() => setChats(prev => prev.filter(x => x.chat_id !== c.chat_id))).catch(() => {}),
      },
    ]);
  };

  const newChatBtn = (
    <TouchableOpacity onPress={() => startChat()} accessibilityLabel="New chat" style={{ padding: 6 }}>
      <SquarePen size={20} color={COLORS.gray700} />
    </TouchableOpacity>
  );

  if (!user) {
    return (
      <SafeAreaView style={styles.safe} edges={['top']}>
        <ScreenHeader title="Ask Finch" />
        <SignInPrompt title="Your personal stock analyst" description="Sign in to chat with Finch about your portfolio, any stock, or the market." />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScreenHeader title="Ask Finch" subtitle="Your analyst — it takes a stance" right={newChatBtn} />
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {ideas.length > 0 && (
          <>
            <Text style={styles.section}>Ideas from Finch</Text>
            <View style={styles.list}>
              {ideas.slice(0, 4).map((i, idx) => (
                <TouchableOpacity
                  key={i.id}
                  onPress={() => startChat(`Walk me through your ${i.direction} idea on ${i.symbol}: "${i.catalyst_summary}". What's the thesis, the bear case, and how would you size it for me?`)}
                  style={[styles.row, idx > 0 && styles.divider]}
                  activeOpacity={0.7}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.rowTitle}>
                      <Text style={{ color: i.direction === 'long' ? COLORS.emerald : COLORS.red }}>{i.direction === 'long' ? '▲ ' : '▼ '}</Text>
                      {i.symbol}
                    </Text>
                    <Text style={styles.rowBody} numberOfLines={2}>{i.catalyst_summary}</Text>
                  </View>
                  <ArrowUpRight size={15} color={COLORS.gray400} />
                </TouchableOpacity>
              ))}
            </View>
          </>
        )}

        <Text style={styles.section}>Try asking</Text>
        <View style={styles.list}>
          {prompts(topSymbol).map((p, idx) => (
            <TouchableOpacity key={p} onPress={() => startChat(p)} style={[styles.row, idx > 0 && styles.divider]} activeOpacity={0.7}>
              <Text style={[styles.rowBody, { flex: 1, color: COLORS.gray900, marginTop: 0, fontSize: 14 }]}>{p}</Text>
              <ArrowUpRight size={15} color={COLORS.gray400} />
            </TouchableOpacity>
          ))}
        </View>

        {chats.length > 0 && (
          <>
            <Text style={styles.section}>Recent</Text>
            <View style={styles.list}>
              {chats.slice(0, 25).map((c, idx) => (
                <TouchableOpacity
                  key={c.chat_id}
                  onPress={() => router.push(`/(tabs)/chat/${c.chat_id}`)}
                  onLongPress={() => deleteChat(c)}
                  style={[styles.row, idx > 0 && styles.divider]}
                  activeOpacity={0.6}
                >
                  <Text style={[styles.rowTitle, { flex: 1, fontFamily: 'DMSans-Medium' }]} numberOfLines={1}>
                    {c.icon ? `${c.icon} ` : ''}{c.title || 'New chat'}
                  </Text>
                  <Text style={styles.when}>{formatRelativeTime(c.updated_at)}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </>
        )}

        {runs.length > 0 && (
          <>
            <Text style={styles.section}>Automation runs</Text>
            <View style={styles.list}>
              {runs.slice(0, 8).map((r, idx) => (
                <TouchableOpacity key={r.chat_id} onPress={() => router.push(`/(tabs)/chat/${r.chat_id}`)} style={[styles.row, idx > 0 && styles.divider]} activeOpacity={0.6}>
                  <Bot size={15} color={COLORS.gray400} />
                  <Text style={[styles.rowBody, { flex: 1, marginTop: 0, color: COLORS.gray700 }]} numberOfLines={1}>{r.title || 'Automation'}</Text>
                  <Text style={styles.when}>{formatRelativeTime(r.updated_at)}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </>
        )}

        <View style={[styles.list, { marginTop: 18 }]}>
          <TouchableOpacity onPress={() => router.push('/tasks')} style={styles.row} activeOpacity={0.7}>
            <ListChecks size={16} color={COLORS.gray500} />
            <Text style={[styles.rowTitle, { flex: 1, fontFamily: 'DMSans-Medium' }]}>Finch's tasks</Text>
            <ChevronRight size={16} color={COLORS.gray400} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.push('/widgets')} style={[styles.row, styles.divider]} activeOpacity={0.7}>
            <LayoutGrid size={16} color={COLORS.gray500} />
            <Text style={[styles.rowTitle, { flex: 1, fontFamily: 'DMSans-Medium' }]}>Boards Finch built</Text>
            <ChevronRight size={16} color={COLORS.gray400} />
          </TouchableOpacity>
        </View>
      </ScrollView>
      <AskBar placeholder="Ask Finch anything…" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fafaf9' },
  scroll: { paddingHorizontal: 16, paddingBottom: 24, maxWidth: 760, width: '100%', alignSelf: 'center' },
  section: { fontFamily: 'DMSans-Bold', fontSize: 15, color: '#1c1917', marginTop: 18, marginBottom: 8 },
  list: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 14, paddingVertical: 12 },
  divider: { borderTopWidth: 1, borderTopColor: COLORS.gray100 },
  rowTitle: { fontFamily: 'DMSans-Bold', fontSize: 14.5, color: COLORS.gray900 },
  rowBody: { fontFamily: 'DMSans', fontSize: 13, color: COLORS.gray500, marginTop: 2, lineHeight: 18 },
  when: { fontFamily: 'DMSans', fontSize: 12, color: COLORS.gray400 },
});
