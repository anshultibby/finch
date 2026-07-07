import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useDrawer } from '@/contexts/DrawerContext';
import { useRouter } from 'expo-router';
import { chatApi } from '@/lib/api';
import { Menu, SquarePen, ArrowUpRight, Sparkles } from 'lucide-react-native';
import FinchLogo from '@/components/FinchLogo';
import SignInPrompt from '@/components/SignInPrompt';

// First-run should read like the analyst offering to work, not a blank page.
const STARTER_PROMPTS = [
  "What's moving the market today?",
  'Analyze my portfolio and flag anything unusual',
  'Give me a bull vs. bear case on NVDA',
  'Find quality dividend stocks under $50',
];

export default function ChatIndexScreen() {
  const { user } = useAuth();
  const { openDrawer } = useDrawer();
  const router = useRouter();

  const createNewChat = async (seed?: string) => {
    if (!user) {
      router.push('/(auth)/login');
      return;
    }
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(
        seed
          ? `/(tabs)/chat/${chatId}?seed=${encodeURIComponent(seed)}`
          : `/(tabs)/chat/${chatId}`
      );
    } catch {}
  };

  return (
    <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={openDrawer} style={styles.iconBtn} activeOpacity={0.7}>
          <Menu size={22} color="#111827" />
        </TouchableOpacity>
        <FinchLogo size={22} showText />
        <TouchableOpacity onPress={() => createNewChat()} style={styles.iconBtn} activeOpacity={0.7}>
          <SquarePen size={20} color="#6b7280" />
        </TouchableOpacity>
      </View>

      {user ? (
        <View className="flex-1 justify-center px-6">
          <View style={styles.iconCircle}>
            <Sparkles size={24} color="#059669" />
          </View>
          <Text style={styles.title}>What should I look into?</Text>
          <Text style={styles.subtitle}>
            Ask about stocks, your portfolio, or the market — or start with one of these.
          </Text>

          <View style={styles.promptList}>
            {STARTER_PROMPTS.map(prompt => (
              <TouchableOpacity
                key={prompt}
                onPress={() => createNewChat(prompt)}
                style={styles.promptRow}
                activeOpacity={0.7}
              >
                <Text style={styles.promptText} numberOfLines={1}>{prompt}</Text>
                <ArrowUpRight size={15} color="#9ca3af" />
              </TouchableOpacity>
            ))}
          </View>

          <TouchableOpacity onPress={() => createNewChat()} style={styles.newChatBtn} activeOpacity={0.8}>
            <Text style={styles.newChatText}>New Chat</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <SignInPrompt
          title="Chat with your AI research desk"
          description="Sign in to ask questions, run research, and analyze your portfolio with Finch's AI agent."
        />
      )}
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
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#ecfdf5',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
  },
  title: {
    fontSize: 20,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: 'DMSans',
    color: '#9ca3af',
    lineHeight: 20,
    marginBottom: 20,
  },
  promptList: {
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    overflow: 'hidden',
    marginBottom: 20,
  },
  promptRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 13,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#f3f4f6',
  },
  promptText: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'DMSans-Medium',
    color: '#374151',
  },
  newChatBtn: {
    backgroundColor: '#111827',
    paddingVertical: 13,
    borderRadius: 12,
    alignItems: 'center',
  },
  newChatText: {
    fontSize: 14,
    fontFamily: 'DMSans-Medium',
    color: '#fff',
  },
});
