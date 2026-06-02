import { View, Text, FlatList, KeyboardAvoidingView, Platform, ActivityIndicator, TouchableOpacity, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { useDrawer } from '@/contexts/DrawerContext';
import { useChatStream } from '@/hooks/useChatStream';
import { chatApi } from '@/lib/api';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Menu, SquarePen } from 'lucide-react-native';
import type { ImageAttachment, ModelOption } from '@/lib/types';
import ChatMessage from '@/components/chat/ChatMessage';
import ChatInput from '@/components/chat/ChatInput';
import StreamingView from '@/components/chat/StreamingView';
import NewChatWelcome from '@/components/chat/NewChatWelcome';
import ModelPicker from '@/components/chat/ModelPicker';
import { COLORS } from '@/lib/constants';

export default function ChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const { openDrawer } = useDrawer();
  const router = useRouter();
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [chatTitle, setChatTitle] = useState('Chat');
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | undefined>(undefined);
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
    chatApi.getModels().then(setModels).catch(() => {});
  }, []);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const data = await chatApi.getChatHistoryForDisplay(id);
        setSelectedModel((data as any).model || undefined);
        if (data.messages?.length > 0) {
          setMessages(data.messages.map(m => ({
            role: m.role,
            content: m.content,
            timestamp: m.timestamp || new Date().toISOString(),
            toolCalls: m.tool_calls,
          })));
          hasGeneratedTitle.current = true;
        }
      } catch {
      } finally {
        setLoadingHistory(false);
      }
    };
    loadHistory();
  }, [id, setMessages]);

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
    sendMessage(text, images, selectedModel);
  }, [isStreaming, sendMessage, selectedModel]);

  const handleWelcomeSend = useCallback((text: string) => {
    if (!text.trim() || isStreaming) return;
    sendMessage(text, undefined, selectedModel);
  }, [isStreaming, sendMessage, selectedModel]);

  const showWelcome = !loadingHistory && messages.length === 0 && !isStreaming;

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      {/* Header */}
      <View style={chatStyles.header}>
        <TouchableOpacity onPress={openDrawer} style={chatStyles.iconBtn} activeOpacity={0.7}>
          <Menu size={22} color={COLORS.gray900} />
        </TouchableOpacity>
        <Text style={chatStyles.headerTitle} numberOfLines={1}>
          {chatTitle}
        </Text>
        <TouchableOpacity
          onPress={async () => {
            if (!user) return;
            try {
              const newId = await chatApi.createChat(user.id);
              router.push(`/(tabs)/chat/${newId}`);
            } catch {}
          }}
          style={chatStyles.iconBtn}
          activeOpacity={0.7}
        >
          <SquarePen size={20} color="#6b7280" />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        {loadingHistory ? (
          <View className="flex-1 items-center justify-center">
            <ActivityIndicator color={COLORS.gray400} />
          </View>
        ) : showWelcome ? (
          <NewChatWelcome onSendMessage={handleWelcomeSend} disabled={isStreaming} models={models} model={selectedModel} onModelChange={setSelectedModel} />
        ) : (
          <>
            <FlatList
              ref={flatListRef}
              data={messages}
              keyExtractor={(_, index) => index.toString()}
              renderItem={({ item, index }) => <ChatMessage message={item} chatId={id} messageIndex={index} />}
              contentContainerClassName="px-4 pt-3 pb-4"
              onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
              ListFooterComponent={
                isStreaming ? (
                  <StreamingView text={streamingText} tools={streamingTools} />
                ) : error ? (
                  <View className="bg-red-50 rounded-xl p-3 mb-3">
                    <Text className="text-[13px] font-body text-red-600">{error}</Text>
                    {(error.toLowerCase().includes('credit') || error.toLowerCase().includes('daily limit')) && (
                      <TouchableOpacity
                        onPress={() => router.push('/settings')}
                        className="mt-2 bg-blue-600 rounded-lg py-2 px-4 self-start"
                      >
                        <Text className="text-white text-[13px] font-body-semibold">Add Credits</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                ) : null
              }
            />
            {models.length > 0 && (
              <View className="px-3 pt-1">
                <ModelPicker models={models} value={selectedModel} onChange={setSelectedModel} disabled={isStreaming} />
              </View>
            )}
            <ChatInput onSend={handleSend} onStop={stopStream} isStreaming={isStreaming} />
          </>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const chatStyles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    height: 48,
  },
  iconBtn: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 18,
  },
  headerTitle: {
    flex: 1,
    fontSize: 16,
    fontFamily: 'DMSans-Medium',
    color: '#111827',
    textAlign: 'center',
    marginHorizontal: 8,
  },
});
