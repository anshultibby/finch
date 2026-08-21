import React, { useState, useEffect, useRef } from 'react';
import { View, Text, ScrollView, ActivityIndicator, StyleSheet, TouchableOpacity } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { Bell, Sparkles, ChevronRight } from 'lucide-react-native';
import Markdown from 'react-native-markdown-display';
import type { ToolCallStatus, TodoItem } from '@/lib/types';
import ToolCallCard from './ToolCallCard';
import TodoChecklist from './TodoChecklist';
import { stripLegacyMarkers } from '@/lib/messageMarkers';

const streamMdStyles = {
  body: { color: '#374151', fontSize: 14, lineHeight: 21, fontFamily: 'DMSans' },
  strong: { fontWeight: '700' as const, color: '#111827', fontFamily: 'DMSans-Bold' },
  code_inline: { backgroundColor: '#f3f4f6', color: '#374151', fontSize: 12.5, fontFamily: 'SpaceMono', paddingHorizontal: 5, borderRadius: 4 },
  fence: { backgroundColor: '#1f2937', color: '#e5e7eb', fontSize: 12.5, fontFamily: 'SpaceMono', padding: 14, borderRadius: 10, marginVertical: 8 },
  link: { color: '#2563eb' },
  paragraph: { marginTop: 0, marginBottom: 8 },
  table: { borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, overflow: 'hidden' as const, marginVertical: 8 },
  thead: { backgroundColor: '#f9fafb' },
  th: { paddingVertical: 6, paddingHorizontal: 10, fontWeight: '600' as const, fontSize: 12, fontFamily: 'DMSans-Medium', color: '#6b7280' },
  td: { paddingVertical: 6, paddingHorizontal: 10, fontSize: 12.5, borderTopWidth: 1, borderTopColor: '#f3f4f6', color: '#374151' },
  tr: { borderBottomWidth: 0 },
};

const streamRules = {
  table: (node: any, children: any, _parent: any, styles: any) => (
    <ScrollView key={node.key} horizontal showsHorizontalScrollIndicator style={{ marginVertical: 8 }}>
      <View style={[styles.table, { minWidth: 320 }]}>{children}</View>
    </ScrollView>
  ),
};

interface StreamingViewProps {
  text: string;
  tools: ToolCallStatus[];
  todos?: TodoItem[];
  thinkingText?: string;
}

export default function StreamingView({ text, tools, todos = [], thinkingText = '' }: StreamingViewProps) {
  const [showNotifBanner, setShowNotifBanner] = useState(false);
  const isWorking = tools.some(tc => tc.status === 'calling' || tc.status === 'detected');

  useEffect(() => {
    if (!isWorking && !text) return;
    const timer = setTimeout(() => setShowNotifBanner(true), 15000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <View className="items-start mb-3">
      {todos.length > 0 && <TodoChecklist items={todos} />}
      {tools.length > 0 && (
        <View className="w-full mb-1.5">
          {tools.map((tc, i) => (
            // Sub-agent (delegated) tools are indented under their parent.
            <View key={tc.tool_call_id || `${tc.tool_name}-${i}`} style={tc.task_id || tc.parent_agent_id ? { paddingLeft: 16 } : undefined}>
              <ToolCallCard toolCall={tc} />
            </View>
          ))}
        </View>
      )}
      {thinkingText.length > 0 && <ThinkingPanel text={thinkingText} />}
      {text.length > 0 && (
        <View className="w-full">
          <Markdown style={streamMdStyles} rules={streamRules}>{stripLegacyMarkers(text)}</Markdown>
        </View>
      )}
      {text.length === 0 && tools.length === 0 && thinkingText.length === 0 && todos.length === 0 && (
        <View className="flex-row items-center gap-1.5 py-2">
          <ActivityIndicator size="small" color="#9ca3af" />
        </View>
      )}
      {showNotifBanner && isWorking && (
        <View style={svStyles.notifBanner}>
          <Bell size={13} color="#059669" />
          <Text style={svStyles.notifText}>You'll be notified when this completes</Text>
        </View>
      )}
    </View>
  );
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return sec > 0 ? `${min}m ${sec}s` : `${min}m`;
}

/** The live reasoning stream, shown as readable content in a bounded,
 *  auto-scrolling panel with a progress header (elapsed + char count). Persists
 *  across tool calls; cleared by the hook only when the final answer starts. */
function ThinkingPanel({ text }: { text: string }) {
  const pulse = useSharedValue(0.5);
  const scrollRef = useRef<ScrollView>(null);
  const startRef = useRef<number>(Date.now());
  const [elapsed, setElapsed] = useState(0);
  // Tap the header to expand the reading area so the whole trace is readable.
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    pulse.value = withRepeat(
      withTiming(1, { duration: 900, easing: Easing.inOut(Easing.ease) }),
      -1,
      true
    );
  }, [pulse]);
  const dotStyle = useAnimatedStyle(() => ({ opacity: pulse.value }));

  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startRef.current) / 1000)), 1000);
    return () => clearInterval(id);
  }, []);

  const clean = text.replace(/\n{3,}/g, '\n\n').trimEnd();

  return (
    <View style={svStyles.thinkingPanel}>
      <TouchableOpacity onPress={() => setExpanded(v => !v)} activeOpacity={0.6} style={svStyles.thinkingHeader}>
        <Animated.View style={dotStyle}>
          <Sparkles size={13} color="#059669" />
        </Animated.View>
        <Text style={svStyles.thinkingLabel}>Thinking</Text>
        <View style={{ flex: 1 }} />
        {clean.length > 0 && <Text style={svStyles.thinkingMeta}>{clean.length.toLocaleString()} chars</Text>}
        {elapsed > 0 && <Text style={svStyles.thinkingMeta}>{formatElapsed(elapsed)}</Text>}
        <ChevronRight size={14} color="#d6d3d1" style={{ transform: [{ rotate: expanded ? '90deg' : '0deg' }] }} />
      </TouchableOpacity>
      <ScrollView
        ref={scrollRef}
        style={[svStyles.thinkingScroll, { maxHeight: expanded ? 440 : 150 }]}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: false })}
        nestedScrollEnabled
        showsVerticalScrollIndicator={false}
      >
        <Text style={svStyles.thinkingText}>{clean}</Text>
      </ScrollView>
    </View>
  );
}

const svStyles = StyleSheet.create({
  thinkingPanel: {
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
    color: '#059669',
  },
  thinkingMeta: {
    fontSize: 11,
    fontFamily: 'DMSans',
    color: '#a8a29e',
    marginLeft: 8,
    fontVariant: ['tabular-nums'],
  },
  thinkingScroll: {
    maxHeight: 150,
    paddingHorizontal: 10,
    paddingBottom: 10,
  },
  thinkingText: {
    fontSize: 12.5,
    lineHeight: 18,
    fontFamily: 'DMSans',
    fontStyle: 'italic',
    color: '#78716c',
  },
  notifBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: '#ecfdf5',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d1fae5',
  },
  notifText: {
    fontSize: 11,
    fontFamily: 'DMSans-Medium',
    color: '#059669',
  },
});
