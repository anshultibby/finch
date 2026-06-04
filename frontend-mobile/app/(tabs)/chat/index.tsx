import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useDrawer } from '@/contexts/DrawerContext';
import { useRouter } from 'expo-router';
import { chatApi } from '@/lib/api';
import { Menu, SquarePen, MessageSquare } from 'lucide-react-native';
import FinchLogo from '@/components/FinchLogo';

export default function ChatIndexScreen() {
  const { user } = useAuth();
  const { openDrawer } = useDrawer();
  const router = useRouter();

  const createNewChat = async () => {
    if (!user) return;
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}`);
    } catch {}
  };

  return (
    <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={openDrawer} style={styles.iconBtn} activeOpacity={0.7}>
          <Menu size={22} color="#111827" />
        </TouchableOpacity>
        <FinchLogo size={22} showText />
        <TouchableOpacity onPress={createNewChat} style={styles.iconBtn} activeOpacity={0.7}>
          <SquarePen size={20} color="#6b7280" />
        </TouchableOpacity>
      </View>

      <View className="flex-1 items-center justify-center px-8">
        <View style={styles.iconCircle}>
          <MessageSquare size={28} color="#9ca3af" />
        </View>
        <Text style={styles.title}>Start a conversation</Text>
        <Text style={styles.subtitle}>
          Ask about stocks, analyze your portfolio, or get investment research.
        </Text>
        <TouchableOpacity onPress={createNewChat} style={styles.newChatBtn} activeOpacity={0.8}>
          <Text style={styles.newChatText}>New Chat</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    height: 48,
  },
  iconBtn: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 18,
  },
  iconCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#f3f4f6',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: 'DMSans',
    color: '#9ca3af',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
  },
  newChatBtn: {
    backgroundColor: '#111827',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  newChatText: {
    fontSize: 14,
    fontFamily: 'DMSans-Medium',
    color: '#fff',
  },
});
