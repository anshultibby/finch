import { View, Text, TextInput, TouchableOpacity, FlatList, KeyboardAvoidingView, Platform, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { useChatStream } from '@/hooks/useChatStream';
import { chatApi } from '@/lib/api';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Square, ArrowLeft, Loader } from 'lucide-react-native';
import type { Message } from '@/lib/types';

function ChatBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  return (
    <View className={`mb-3 ${isUser ? 'items-end' : 'items-start'}`}>
      <View className={`max-w-[85%] rounded-2xl px-4 py-3 ${isUser ? 'bg-slate-900' : 'bg-white border border-black/5'}`}>
        <Text className={`text-[15px] font-body leading-6 ${isUser ? 'text-white' : 'text-slate-800'}`}>
          {message.content}
        </Text>
        {message.toolCalls && message.toolCalls.length > 0 && (
          <View className="mt-2 pt-2 border-t border-black/5">
            {message.toolCalls.map((tc) => (
              <View key={tc.tool_call_id} className="flex-row items-center gap-2 py-1">
                <View className={`w-2 h-2 rounded-full ${tc.status === 'completed' ? 'bg-emerald-500' : tc.status === 'error' ? 'bg-red-500' : 'bg-amber-500'}`} />
                <Text className="text-xs font-body text-slate-500">
                  {tc.tool_name.replace(/_/g, ' ')}
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>
    </View>
  );
}

function StreamingBubble({ text, tools }: { text: string; tools: Array<{ tool_call_id: string; tool_name: string; status: string }> }) {
  return (
    <View className="items-start mb-3">
      {tools.length > 0 && (
        <View className="bg-white rounded-2xl px-4 py-3 mb-2 border border-black/5 max-w-[85%]">
          {tools.map((tc) => (
            <View key={tc.tool_call_id} className="flex-row items-center gap-2 py-1">
              {tc.status === 'calling' || tc.status === 'detected' ? (
                <Loader size={12} color="#f59e0b" />
              ) : (
                <View className={`w-2 h-2 rounded-full ${tc.status === 'completed' ? 'bg-emerald-500' : 'bg-red-500'}`} />
              )}
              <Text className="text-xs font-body text-slate-500">
                {tc.tool_name.replace(/_/g, ' ')}
              </Text>
            </View>
          ))}
        </View>
      )}
      {text.length > 0 && (
        <View className="bg-white rounded-2xl px-4 py-3 border border-black/5 max-w-[85%]">
          <Text className="text-[15px] font-body text-slate-800 leading-6">{text}</Text>
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
  const [input, setInput] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(true);
  const flatListRef = useRef<FlatList>(null);

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
        }
      } catch {
        // New chat, no history
      } finally {
        setLoadingHistory(false);
      }
    };
    loadHistory();
  }, [id, setMessages]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput('');
    sendMessage(text);
  }, [input, isStreaming, sendMessage]);

  const allItems = [...messages];

  return (
    <SafeAreaView className="flex-1 bg-finch-bg" edges={['top']}>
      {/* Header */}
      <View className="flex-row items-center px-4 py-3 border-b border-black/5">
        <TouchableOpacity onPress={() => router.back()} className="mr-3 p-1" activeOpacity={0.7}>
          <ArrowLeft size={22} color="#0f172a" />
        </TouchableOpacity>
        <Text className="text-lg font-body-medium text-slate-900 flex-1" numberOfLines={1}>
          Chat
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
        ) : (
          <FlatList
            ref={flatListRef}
            data={allItems}
            keyExtractor={(_, index) => index.toString()}
            renderItem={({ item }) => <ChatBubble message={item} />}
            contentContainerClassName="px-4 pt-4 pb-2"
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
            ListFooterComponent={
              isStreaming ? (
                <StreamingBubble text={streamingText} tools={streamingTools} />
              ) : error ? (
                <View className="bg-red-50 rounded-2xl p-4 mb-3">
                  <Text className="text-sm font-body text-red-600">{error}</Text>
                </View>
              ) : null
            }
            ListEmptyComponent={
              <View className="flex-1 items-center justify-center py-20">
                <Text className="text-slate-400 font-body text-center">
                  Ask anything about markets, stocks, or your portfolio
                </Text>
              </View>
            }
          />
        )}

        {/* Input */}
        <View className="px-4 py-3 border-t border-black/5 bg-finch-bg">
          <View className="flex-row items-end gap-2">
            <TextInput
              value={input}
              onChangeText={setInput}
              placeholder="Message..."
              placeholderTextColor="#94a3b8"
              multiline
              maxLength={10000}
              className="flex-1 bg-white rounded-2xl px-4 py-3 text-[15px] font-body text-slate-900 border border-black/5 max-h-32"
              editable={!isStreaming}
              onSubmitEditing={handleSend}
              blurOnSubmit={false}
            />
            {isStreaming ? (
              <TouchableOpacity
                onPress={stopStream}
                className="bg-red-500 rounded-full w-10 h-10 items-center justify-center"
                activeOpacity={0.8}
              >
                <Square size={16} color="#ffffff" fill="#ffffff" />
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                onPress={handleSend}
                disabled={!input.trim()}
                className={`rounded-full w-10 h-10 items-center justify-center ${input.trim() ? 'bg-slate-900' : 'bg-slate-200'}`}
                activeOpacity={0.8}
              >
                <Send size={16} color={input.trim() ? '#ffffff' : '#94a3b8'} />
              </TouchableOpacity>
            )}
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
