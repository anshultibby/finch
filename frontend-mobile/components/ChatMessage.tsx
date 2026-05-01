import React from 'react';
import { View, Text } from 'react-native';
import Markdown from 'react-native-markdown-display';
import type { Message } from '@/lib/types';
import ToolCallCard from './ToolCallCard';

const markdownStyles = {
  body: { color: '#1e293b', fontSize: 14, lineHeight: 22, fontFamily: 'DMSans' },
  heading1: { fontSize: 20, fontWeight: '700' as const, color: '#0f172a', marginVertical: 8, fontFamily: 'DMSans-Bold' },
  heading2: { fontSize: 17, fontWeight: '700' as const, color: '#0f172a', marginVertical: 6, fontFamily: 'DMSans-Bold' },
  heading3: { fontSize: 15, fontWeight: '600' as const, color: '#0f172a', marginVertical: 4, fontFamily: 'DMSans-Bold' },
  paragraph: { marginVertical: 3 },
  strong: { fontWeight: '700' as const, fontFamily: 'DMSans-Bold' },
  em: { fontStyle: 'italic' as const },
  link: { color: '#2563eb', textDecorationLine: 'underline' as const },
  blockquote: { backgroundColor: '#f8fafc', borderLeftWidth: 3, borderLeftColor: '#cbd5e1', paddingLeft: 12, paddingVertical: 4, marginVertical: 8 },
  code_inline: { backgroundColor: '#f1f5f9', color: '#475569', fontSize: 13, fontFamily: 'SpaceMono', paddingHorizontal: 4, paddingVertical: 1, borderRadius: 4 },
  code_block: { backgroundColor: '#1e293b', color: '#e2e8f0', fontSize: 13, fontFamily: 'SpaceMono', padding: 12, borderRadius: 8, marginVertical: 8 },
  fence: { backgroundColor: '#1e293b', color: '#e2e8f0', fontSize: 13, fontFamily: 'SpaceMono', padding: 12, borderRadius: 8, marginVertical: 8 },
  bullet_list: { marginVertical: 4 },
  ordered_list: { marginVertical: 4 },
  list_item: { marginVertical: 2 },
  table: { borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 8, marginVertical: 8 },
  thead: { backgroundColor: '#f8fafc' },
  th: { padding: 8, fontWeight: '600' as const, fontSize: 13, fontFamily: 'DMSans-Medium' },
  td: { padding: 8, fontSize: 13, borderTopWidth: 1, borderTopColor: '#e2e8f0' },
  hr: { backgroundColor: '#e2e8f0', height: 1, marginVertical: 12 },
};

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <View className={`mb-3 ${isUser ? 'items-end' : 'items-start'}`}>
      {message.toolCalls && message.toolCalls.length > 0 && !isUser && (
        <View className="w-full mb-2">
          {message.toolCalls.map((tc) => (
            <ToolCallCard key={tc.tool_call_id} toolCall={tc} />
          ))}
        </View>
      )}

      {isUser ? (
        <View className="max-w-[85%] rounded-2xl rounded-br-sm px-4 py-3 bg-green-600">
          <Text className="text-[15px] font-body text-white leading-6">
            {message.content}
          </Text>
        </View>
      ) : (
        <View className="w-full px-3">
          <Markdown style={markdownStyles}>
            {message.content}
          </Markdown>
        </View>
      )}
    </View>
  );
}
