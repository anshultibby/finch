import { View, Text, FlatList, KeyboardAvoidingView, Platform, ActivityIndicator, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { useChatStream } from '@/hooks/useChatStream';
import { chatApi } from '@/lib/api';
import { useState, useEffect, useRef, useCallback } from 'react';
import { ArrowLeft } from 'lucide-react-native';
import type { Message, ImageAttachment } from '@/lib/types';
import ChatMessage from '@/components/ChatMessage';
import ChatInput from '@/components/ChatInput';
import ToolCallCard from '@/components/ToolCallCard';
import NewChatWelcome from '@/components/NewChatWelcome';
import Markdown from 'react-native-markdown-display';

const streamingMarkdownStyles = {
  body: { color: '#1e293b', fontSize: 15, lineHeight: 24, fontFamily: 'DMSans' },
  strong: { fontWeight: '700' as const, fontFamily: 'DMSans-Bold' },
  code_inline: { backgroundColor: '#f1f5f9', color: '#475569', fontSize: 13, fontFamily: 'SpaceMono', paddingHorizontal: 4, borderRadius: 4 },
  fence: { backgroundColor: '#1e293b', color: '#e2e8f0', fontSize: 13, fontFamily: 'SpaceMono', padding: 12, borderRadius: 8, marginVertical: 8 },
  link: { color: '#2563eb' },
  paragraph: { marginVertical: 4 },
};

function StreamingView({ text, tools }: { text: string; tools: Array<{ tool_call_id: string; tool_name: string; status: string; arguments?: Record<string, any>; result_summary?: string; error?: string }> }) {
  return (
    <View className="items-start mb-3">
      {tools.length > 0 && (
        <View className="w-full max-w-[90%] mb-2">
          {tools.map((tc) => (
            <ToolCallCard key={tc.tool_call_id} toolCall={tc as any} />
          ))}
        </View>
      )}
      {text.length > 0 && (
        <View className="bg-white rounded-2xl px-4 py-3 border border-black/5 max-w-[90%]">
          <Markdown style={streamingMarkdownStyles}>{text}</Markdown>
        </View>
      )}
      {text.length === 0 && tools.length === 0 && (
        <View className="bg-white rounded-2xl px-4 py-3 border border-black/5">
          <ActivityIndicator size="small" color="#94a3b8" />
        </View>
      )}
    </View>
  );
}

export default function ChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [chatTitle, setChatTitle] = useState('Chat');
  const flatListRef = useRef<FlatList>(null);
  const hasGeneratedTitle = useRef(false);

  const {
    messages,
    streamingText,
    streamingTools,
    isStreaming,
    error,
    setMessages,
    sendMessage,
    stopStream,
  } = useChatStream(user?.id || '', id);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const data = await chatApi.getChatHistoryForDisplay(id);
        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages.map(m => ({
            role: m.role,
            content: m.content,
            timestamp: m.timestamp || new Date().toISOString(),
            toolCalls: m.tool_calls,
          })));
          hasGeneratedTitle.current = true;
        }
      } catch {
        // New chat
      } finally {
        setLoadingHistory(false);
      }
    };
    loadHistory();
  }, [id, setMessages]);

  // Auto-generate title after first user message
  useEffect(() => {
    if (hasGeneratedTitle.current) return;
    const userMessages = messages.filter(m => m.role === 'user');
    if (userMessages.length === 1 && !isStreaming) {
      hasGeneratedTitle.current = true;
      chatApi.generateTitle(id, userMessages[0].content)
        .then(data => setChatTitle(data.title))
        .catch(() => {});
    }
  }, [messages, isStreaming, id]);

  const handleSend = useCallback((text: string, images?: ImageAttachment[]) => {
    if (!text.trim() || isStreaming) return;
    sendMessage(text, images);
  }, [isStreaming, sendMessage]);

  const handleWelcomeSend = useCallback((text: string, investorPersona?: string) => {
    if (!text.trim() || isStreaming) return;
    sendMessage(text);
  }, [isStreaming, sendMessage]);

  const showWelcome = !loadingHistory && messages.length === 0 && !isStreaming;

  return (
    <SafeAreaView className="flex-1 bg-finch-bg" edges={['top']}>
      {/* Header */}
      <View className="flex-row items-center px-4 py-3 border-b border-black/5">
        <TouchableOpacity onPress={() => router.back()} className="mr-3 p-1" activeOpacity={0.7}>
          <ArrowLeft size={22} color="#0f172a" />
        </TouchableOpacity>
        <Text className="text-lg font-body-medium text-slate-900 flex-1" numberOfLines={1}>
          {chatTitle}
        </Text>
      </View>

      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        {loadingHistory ? (
          <View className="flex-1 items-center justify-center">
            <ActivityIndicator size="large" color="#0f172a" />
          </View>
        ) : showWelcome ? (
          <NewChatWelcome onSendMessage={handleWelcomeSend} disabled={isStreaming} />
        ) : (
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(_, index) => index.toString()}
            renderItem={({ item }) => <ChatMessage message={item} />}
            contentContainerClassName="px-4 pt-4 pb-2"
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
            ListFooterComponent={
              isStreaming ? (
                <StreamingView text={streamingText} tools={streamingTools} />
              ) : error ? (
                <View className="bg-red-50 rounded-2xl p-4 mb-3">
                  <Text className="text-sm font-body text-red-600">{error}</Text>
                </View>
              ) : null
            }
          />
        )}

        {!showWelcome && (
          <ChatInput
            onSend={handleSend}
            onStop={stopStream}
            isStreaming={isStreaming}
          />
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
