import React, { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Platform, StyleSheet } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import Markdown from 'react-native-markdown-display';
import { Copy, Check, ThumbsUp, ThumbsDown, Sparkles, ChevronRight } from 'lucide-react-native';
import * as Clipboard from 'expo-clipboard';
import * as Haptics from 'expo-haptics';
import type { Message } from '@/lib/types';
import ToolCallCard from './ToolCallCard';
import { stripLegacyMarkers } from '@/lib/messageMarkers';
import { chatApi } from '@/lib/api';

const mdStyles = {
  body: { color: '#374151', fontSize: 14, lineHeight: 21, fontFamily: 'DMSans' },
  heading1: { fontSize: 18, fontWeight: '700' as const, color: '#111827', marginTop: 16, marginBottom: 6, fontFamily: 'DMSans-Bold' },
  heading2: { fontSize: 16, fontWeight: '700' as const, color: '#111827', marginTop: 14, marginBottom: 5, fontFamily: 'DMSans-Bold' },
  heading3: { fontSize: 14, fontWeight: '600' as const, color: '#111827', marginTop: 10, marginBottom: 4, fontFamily: 'DMSans-Bold' },
  paragraph: { marginTop: 0, marginBottom: 8 },
  strong: { fontWeight: '700' as const, color: '#111827', fontFamily: 'DMSans-Bold' },
  em: { fontStyle: 'italic' as const },
  link: { color: '#2563eb', textDecorationLine: 'none' as const },
  blockquote: { backgroundColor: '#f9fafb', borderLeftWidth: 3, borderLeftColor: '#d1d5db', paddingLeft: 12, paddingVertical: 4, marginVertical: 6 },
  code_inline: { backgroundColor: '#f3f4f6', color: '#374151', fontSize: 12.5, fontFamily: 'SpaceMono', paddingHorizontal: 5, paddingVertical: 2, borderRadius: 4 },
  code_block: { backgroundColor: '#1f2937', color: '#e5e7eb', fontSize: 12.5, fontFamily: 'SpaceMono', padding: 14, borderRadius: 10, marginVertical: 8, overflow: 'hidden' as const },
  fence: { backgroundColor: '#1f2937', color: '#e5e7eb', fontSize: 12.5, fontFamily: 'SpaceMono', padding: 14, borderRadius: 10, marginVertical: 8, overflow: 'hidden' as const },
  bullet_list: { marginTop: 2, marginBottom: 6 },
  ordered_list: { marginTop: 2, marginBottom: 6 },
  list_item: { marginVertical: 1.5 },
  table: { borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, overflow: 'hidden' as const, marginVertical: 8 },
  thead: { backgroundColor: '#f9fafb' },
  th: { paddingVertical: 6, paddingHorizontal: 10, fontWeight: '600' as const, fontSize: 12, fontFamily: 'DMSans-Medium', color: '#6b7280' },
  td: { paddingVertical: 6, paddingHorizontal: 10, fontSize: 12.5, borderTopWidth: 1, borderTopColor: '#f3f4f6', color: '#374151' },
  tr: { borderBottomWidth: 0 },
  hr: { backgroundColor: '#e5e7eb', height: 1, marginVertical: 12 },
};

const mdRules = {
  table: (node: any, children: any, _parent: any, styles: any) => (
    <ScrollView key={node.key} horizontal showsHorizontalScrollIndicator style={{ marginVertical: 8 }}>
      <View style={[styles.table, { minWidth: 320 }]}>{children}</View>
    </ScrollView>
  ),
};

export default function ChatMessage({ message, chatId, messageIndex }: {
  message: Message;
  chatId?: string;
  messageIndex?: number;
}) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
  const [showThinking, setShowThinking] = useState(false);
  const reasoning = !isUser ? (message.reasoning || '').trim() : '';

  const handleCopy = async () => {
    if (!message.content) return;
    if (Platform.OS === 'web') {
      await navigator.clipboard.writeText(message.content);
    } else {
      await Clipboard.setStringAsync(message.content);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sendFeedback = (next: 'up' | 'down') => {
    const value = feedback === next ? null : next;
    setFeedback(value);
    Haptics.selectionAsync();
    if (value && chatId != null && messageIndex != null) {
      chatApi
        .submitFeedback(chatId, messageIndex, value === 'up' ? 'like' : 'dislike', undefined, message.content)
        .catch(() => {});
    }
  };

  return (
    <Animated.View entering={FadeInDown.springify().damping(15).mass(0.7)} className={`mb-3 ${isUser ? 'items-end' : 'items-start'}`}>
      {reasoning.length > 0 && (
        <View style={cmStyles.thinkingCard}>
          <TouchableOpacity onPress={() => setShowThinking(v => !v)} activeOpacity={0.6} style={cmStyles.thinkingHeader}>
            <Sparkles size={13} color="#059669" />
            <Text style={cmStyles.thinkingLabel}>Reasoning</Text>
            <View style={{ flex: 1 }} />
            <Text style={cmStyles.thinkingMeta}>{reasoning.length.toLocaleString()} chars</Text>
            <ChevronRight size={14} color="#d6d3d1" style={{ transform: [{ rotate: showThinking ? '90deg' : '0deg' }] }} />
          </TouchableOpacity>
          {/* A preview stays visible in-flow; tap to expand to the full scrollable trace. */}
          {showThinking ? (
            <ScrollView style={cmStyles.thinkingBody} nestedScrollEnabled showsVerticalScrollIndicator={false}>
              <Text style={cmStyles.thinkingText}>{reasoning}</Text>
            </ScrollView>
          ) : (
            <View style={cmStyles.thinkingPreview}>
              <Text style={cmStyles.thinkingText} numberOfLines={5}>{reasoning}</Text>
              <Text style={cmStyles.thinkingMore}>Show full reasoning</Text>
            </View>
          )}
        </View>
      )}
      {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
        <View className="w-full mb-1.5">
          {message.toolCalls.map((tc, i) => (
            // Sub-agent (delegated) tools are indented under their parent.
            <View key={tc.tool_call_id || `${tc.tool_name}-${i}`} style={tc.task_id || tc.parent_agent_id ? { paddingLeft: 16 } : undefined}>
              <ToolCallCard toolCall={tc} />
            </View>
          ))}
        </View>
      )}

      {isUser ? (
        <View className="max-w-[85%] rounded-[18px] rounded-br-[4px] px-3.5 py-2.5 bg-gray-900">
          <Text className="text-[14px] font-body text-white leading-[20px]">{message.content}</Text>
        </View>
      ) : message.content ? (
        <View className="w-full">
          <Markdown style={mdStyles} rules={mdRules}>{stripLegacyMarkers(message.content)}</Markdown>
          {/* Message Actions */}
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4, marginBottom: 4 }}>
            <TouchableOpacity onPress={handleCopy} style={{ padding: 6, borderRadius: 6 }} activeOpacity={0.6}>
              {copied ? <Check size={14} color="#059669" /> : <Copy size={14} color="#d1d5db" />}
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => sendFeedback('up')}
              style={{ padding: 6, borderRadius: 6 }}
              activeOpacity={0.6}
            >
              <ThumbsUp size={14} color={feedback === 'up' ? '#059669' : '#d1d5db'} fill={feedback === 'up' ? '#059669' : 'none'} />
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => sendFeedback('down')}
              style={{ padding: 6, borderRadius: 6 }}
              activeOpacity={0.6}
            >
              <ThumbsDown size={14} color={feedback === 'down' ? '#ef4444' : '#d1d5db'} fill={feedback === 'down' ? '#ef4444' : 'none'} />
            </TouchableOpacity>
          </View>
        </View>
      ) : null}
    </Animated.View>
  );
}

const cmStyles = StyleSheet.create({
  thinkingCard: {
    width: '100%',
    marginBottom: 6,
    borderWidth: 1,
    borderColor: '#f0efec',
    borderRadius: 12,
    backgroundColor: '#fafaf9',
    overflow: 'hidden',
  },
  thinkingHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  thinkingLabel: {
    fontSize: 13,
    fontFamily: 'DMSans-Medium',
    color: '#78716c',
  },
  thinkingBody: {
    maxHeight: 440,
    paddingHorizontal: 10,
    paddingBottom: 10,
  },
  thinkingPreview: {
    paddingHorizontal: 10,
    paddingBottom: 8,
  },
  thinkingText: {
    fontSize: 12.5,
    lineHeight: 18,
    fontFamily: 'DMSans',
    fontStyle: 'italic',
    color: '#78716c',
  },
  thinkingMeta: {
    fontSize: 11,
    fontFamily: 'DMSans',
    color: '#a8a29e',
    marginRight: 6,
    fontVariant: ['tabular-nums'],
  },
  thinkingMore: {
    marginTop: 4,
    fontSize: 11,
    fontFamily: 'DMSans-Medium',
    color: '#a8a29e',
  },
});
