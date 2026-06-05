import { View, Text, FlatList, KeyboardAvoidingView, Platform, ActivityIndicator, TouchableOpacity, StyleSheet, Modal, Pressable, Alert, Share, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { useDrawer } from '@/contexts/DrawerContext';
import { useChatStream } from '@/hooks/useChatStream';
import { chatApi } from '@/lib/api';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Menu, Share2, MoreHorizontal, Pencil, Trash2 } from 'lucide-react-native';
import type { ImageAttachment, ModelOption } from '@/lib/types';
import ChatMessage from '@/components/chat/ChatMessage';
import ChatInput from '@/components/chat/ChatInput';
import StreamingView from '@/components/chat/StreamingView';
import NewChatWelcome from '@/components/chat/NewChatWelcome';
import ModelPicker from '@/components/chat/ModelPicker';
import { COLORS } from '@/lib/constants';

// Public share links open the web app (mobile has no in-app shared route).
const WEB_BASE_URL = process.env.EXPO_PUBLIC_WEB_URL || 'https://finchapp.ai';

export default function ChatScreen() {
  const { id, seed } = useLocalSearchParams<{ id: string; seed?: string }>();
  const seededRef = useRef(false);
  const { user } = useAuth();
  const { openDrawer } = useDrawer();
  const router = useRouter();
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [chatTitle, setChatTitle] = useState('Chat');
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | undefined>(undefined);
  const [menuOpen, setMenuOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [busy, setBusy] = useState(false);
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

  // Auto-send a seed question handed off from a docked AskBar (markets / stock).
  useEffect(() => {
    if (loadingHistory || seededRef.current || isStreaming) return;
    if (seed && messages.length === 0) {
      seededRef.current = true;
      handleWelcomeSend(String(seed));
    }
  }, [loadingHistory, seed, messages.length, isStreaming, handleWelcomeSend]);

  const createNewChat = useCallback(async () => {
    if (!user) return;
    try {
      const newId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${newId}`);
    } catch {}
  }, [user, router]);

  const handleShare = useCallback(async () => {
    setMenuOpen(false);
    setBusy(true);
    try {
      const res = await chatApi.shareChat(id);
      if (res.share_token) {
        const url = `${WEB_BASE_URL}/share/chat/${res.share_token}`;
        await Share.share({ url, message: url });
      }
    } catch {} finally { setBusy(false); }
  }, [id]);

  const openRename = useCallback(() => {
    setMenuOpen(false);
    setRenameValue(chatTitle === 'Chat' ? '' : chatTitle);
    setRenameOpen(true);
  }, [chatTitle]);

  const submitRename = useCallback(async () => {
    const next = renameValue.trim();
    if (!next || next === chatTitle) { setRenameOpen(false); return; }
    setBusy(true);
    try {
      await chatApi.renameChat(id, next);
      setChatTitle(next);
      hasGeneratedTitle.current = true;
      setRenameOpen(false);
    } catch {} finally { setBusy(false); }
  }, [renameValue, chatTitle, id]);

  const confirmDelete = useCallback(() => {
    setMenuOpen(false);
    Alert.alert('Delete chat', 'Delete this chat? This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await chatApi.deleteChat(id);
            await createNewChat();
          } catch {}
        },
      },
    ]);
  }, [id, createNewChat]);

  const showWelcome = !loadingHistory && messages.length === 0 && !isStreaming && !seed;

  return (
    <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={['top']}>
      {/* Header */}
      <View style={chatStyles.header}>
        <TouchableOpacity onPress={openDrawer} style={chatStyles.iconBtn} activeOpacity={0.7}>
          <Menu size={22} color={COLORS.gray900} />
        </TouchableOpacity>
        <Text style={chatStyles.headerTitle} numberOfLines={1}>
          {chatTitle}
        </Text>
        <View style={chatStyles.headerActions}>
          <TouchableOpacity
            onPress={handleShare}
            disabled={busy}
            style={chatStyles.iconBtn}
            activeOpacity={0.7}
            hitSlop={{ top: 6, bottom: 6, left: 6, right: 6 }}
          >
            <Share2 size={20} color="#6b7280" />
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => setMenuOpen(true)}
            style={chatStyles.iconBtn}
            activeOpacity={0.7}
            hitSlop={{ top: 6, bottom: 6, left: 6, right: 6 }}
          >
            <MoreHorizontal size={22} color="#6b7280" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Options menu */}
      <Modal visible={menuOpen} transparent animationType="fade" onRequestClose={() => setMenuOpen(false)}>
        <Pressable style={chatStyles.menuOverlay} onPress={() => setMenuOpen(false)}>
          <View style={chatStyles.menuCard}>
            <TouchableOpacity style={chatStyles.menuRow} onPress={handleShare} activeOpacity={0.6}>
              <Share2 size={18} color={COLORS.gray700} />
              <Text style={chatStyles.menuText}>Share</Text>
            </TouchableOpacity>
            <TouchableOpacity style={chatStyles.menuRow} onPress={openRename} activeOpacity={0.6}>
              <Pencil size={18} color={COLORS.gray700} />
              <Text style={chatStyles.menuText}>Rename</Text>
            </TouchableOpacity>
            <View style={chatStyles.menuDivider} />
            <TouchableOpacity style={chatStyles.menuRow} onPress={confirmDelete} activeOpacity={0.6}>
              <Trash2 size={18} color={COLORS.red} />
              <Text style={[chatStyles.menuText, { color: COLORS.red }]}>Delete</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Modal>

      {/* Rename modal */}
      <Modal visible={renameOpen} transparent animationType="fade" onRequestClose={() => setRenameOpen(false)}>
        <Pressable style={chatStyles.menuOverlay} onPress={() => setRenameOpen(false)}>
          <Pressable style={chatStyles.renameCard} onPress={() => {}}>
            <Text style={chatStyles.renameTitle}>Rename chat</Text>
            <TextInput
              value={renameValue}
              onChangeText={setRenameValue}
              autoFocus
              placeholder="Chat title"
              placeholderTextColor={COLORS.gray400}
              style={chatStyles.renameInput}
              onSubmitEditing={submitRename}
              returnKeyType="done"
            />
            <View style={chatStyles.renameActions}>
              <TouchableOpacity onPress={() => setRenameOpen(false)} activeOpacity={0.6} style={chatStyles.renameBtn}>
                <Text style={chatStyles.renameCancel}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={submitRename} disabled={busy} activeOpacity={0.6} style={[chatStyles.renameBtn, chatStyles.renameSave]}>
                <Text style={chatStyles.renameSaveText}>Save</Text>
              </TouchableOpacity>
            </View>
          </Pressable>
        </Pressable>
      </Modal>

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
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  menuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15,23,42,0.28)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  menuCard: {
    width: '100%',
    maxWidth: 280,
    backgroundColor: '#ffffff',
    borderRadius: 16,
    paddingVertical: 6,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  menuRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  menuText: { fontSize: 15, fontFamily: 'DMSans-Medium', color: '#0f172a' },
  menuDivider: { height: 1, backgroundColor: 'rgba(0,0,0,0.06)', marginVertical: 4 },
  renameCard: {
    width: '100%',
    maxWidth: 320,
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 18,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  renameTitle: { fontSize: 15, fontFamily: 'DMSans-Bold', color: '#0f172a', marginBottom: 12 },
  renameInput: {
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.12)',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    fontFamily: 'DMSans',
    color: '#0f172a',
  },
  renameActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 16 },
  renameBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10 },
  renameSave: { backgroundColor: COLORS.emerald },
  renameCancel: { fontSize: 14, fontFamily: 'DMSans-Medium', color: COLORS.gray500 },
  renameSaveText: { fontSize: 14, fontFamily: 'DMSans-Medium', color: '#fff' },
});
