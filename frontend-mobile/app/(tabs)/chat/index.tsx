import { View, Text, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { useState, useEffect, useCallback } from 'react';
import { chatApi } from '@/lib/api';
import { Plus, MessageSquare } from 'lucide-react-native';

interface ChatItem {
  chat_id: string;
  title: string | null;
  icon: string | null;
  created_at: string;
  updated_at: string;
  last_message?: string;
}

export default function ChatListScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [chats, setChats] = useState<ChatItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchChats = useCallback(async () => {
    if (!user) return;
    try {
      const data = await chatApi.getUserChats(user.id);
      setChats(data.chats || []);
    } catch (err) {
      console.error('Failed to fetch chats:', err);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchChats(); }, [fetchChats]);

  const createNewChat = async () => {
    if (!user) return;
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}`);
    } catch (err) {
      console.error('Failed to create chat:', err);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <SafeAreaView className="flex-1 bg-finch-bg" edges={['top']}>
      <View className="flex-row items-center justify-between px-5 py-3">
        <Text className="text-2xl font-body-bold text-slate-900">Chats</Text>
        <TouchableOpacity
          onPress={createNewChat}
          className="bg-slate-900 rounded-full w-10 h-10 items-center justify-center"
          activeOpacity={0.8}
        >
          <Plus size={20} color="#ffffff" />
        </TouchableOpacity>
      </View>

      {loading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator size="large" color="#0f172a" />
        </View>
      ) : chats.length === 0 ? (
        <View className="flex-1 items-center justify-center px-8">
          <MessageSquare size={48} color="#cbd5e1" />
          <Text className="text-lg font-body-medium text-slate-400 mt-4 text-center">
            No chats yet
          </Text>
          <Text className="text-sm font-body text-slate-400 mt-1 text-center">
            Start a conversation to get AI-powered trading insights
          </Text>
          <TouchableOpacity
            onPress={createNewChat}
            className="mt-6 bg-slate-900 rounded-2xl px-6 py-3"
            activeOpacity={0.8}
          >
            <Text className="text-white font-body-medium">Start a Chat</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={chats}
          keyExtractor={(item) => item.chat_id}
          contentContainerClassName="px-5 pb-4"
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() => router.push(`/(tabs)/chat/${item.chat_id}`)}
              className="bg-white rounded-2xl p-4 mb-3 border border-black/5"
              activeOpacity={0.7}
            >
              <View className="flex-row items-start justify-between">
                <View className="flex-1 mr-3">
                  <Text className="text-base font-body-medium text-slate-900" numberOfLines={1}>
                    {item.icon ? `${item.icon} ` : ''}{item.title || 'New Chat'}
                  </Text>
                  {item.last_message && (
                    <Text className="text-sm font-body text-slate-500 mt-1" numberOfLines={2}>
                      {item.last_message}
                    </Text>
                  )}
                </View>
                <Text className="text-xs font-body text-slate-400">
                  {formatDate(item.updated_at)}
                </Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}
