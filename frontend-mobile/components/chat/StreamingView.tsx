import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, ActivityIndicator, StyleSheet } from 'react-native';
import { Bell } from 'lucide-react-native';
import Markdown from 'react-native-markdown-display';
import type { ToolCallStatus } from '@/lib/types';
import ToolCallCard from './ToolCallCard';
import { VisualizationChip } from './VisualizationPreview';
import { parseMessageParts } from '@/lib/messageMarkers';

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
}

export default function StreamingView({ text, tools }: StreamingViewProps) {
  const [showNotifBanner, setShowNotifBanner] = useState(false);
  const isWorking = tools.some(tc => tc.status === 'calling' || tc.status === 'detected');

  useEffect(() => {
    if (!isWorking && !text) return;
    const timer = setTimeout(() => setShowNotifBanner(true), 15000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <View className="items-start mb-3">
      {tools.length > 0 && (
        <View className="w-full mb-1.5">
          {tools.map((tc) => (
            <ToolCallCard key={tc.tool_call_id || tc.tool_name + Math.random()} toolCall={tc} />
          ))}
        </View>
      )}
      {text.length > 0 && (
        <View className="w-full">
          {parseMessageParts(text).map((part, i) =>
            part.type === 'visualization' ? (
              <VisualizationChip key={`viz-${i}`} filename={part.filename} />
            ) : (
              <Markdown key={`md-${i}`} style={streamMdStyles} rules={streamRules}>{part.value}</Markdown>
            )
          )}
        </View>
      )}
      {text.length === 0 && tools.length === 0 && (
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

const svStyles = StyleSheet.create({
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
