import React, { useEffect, useRef, useState } from 'react';
import { View, Text, TouchableOpacity, Animated, StyleSheet, ScrollView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useDrawer } from '@/contexts/DrawerContext';
import { chatApi } from '@/lib/api';
import { X, SquarePen, Search, Star, BarChart3 } from 'lucide-react-native';
import FinchLogo from '@/components/FinchLogo';

const SIDEBAR_WIDTH = 300;

interface ChatItem {
  chat_id: string;
  title: string | null;
  icon: string | null;
  updated_at: string;
}

export default function Sidebar() {
  const { isOpen, closeDrawer } = useDrawer();
  const { user, signOut } = useAuth();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const translateX = useRef(new Animated.Value(-SIDEBAR_WIDTH)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;
  const [visible, setVisible] = useState(false);
  const [chats, setChats] = useState<ChatItem[]>([]);

  useEffect(() => {
    if (isOpen) {
      setVisible(true);
      fetchChats();
      Animated.parallel([
        Animated.timing(translateX, { toValue: 0, duration: 250, useNativeDriver: true }),
        Animated.timing(backdropOpacity, { toValue: 1, duration: 250, useNativeDriver: true }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(translateX, { toValue: -SIDEBAR_WIDTH, duration: 200, useNativeDriver: true }),
        Animated.timing(backdropOpacity, { toValue: 0, duration: 200, useNativeDriver: true }),
      ]).start(() => setVisible(false));
    }
  }, [isOpen]);

  const fetchChats = async () => {
    if (!user) return;
    try {
      const data = await chatApi.getUserChats(user.id);
      setChats(data.chats || []);
    } catch {}
  };

  const createNewChat = async () => {
    if (!user) return;
    closeDrawer();
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}`);
    } catch {}
  };

  const openChat = (chatId: string) => {
    closeDrawer();
    router.push(`/(tabs)/chat/${chatId}`);
  };

  const navigate = (path: string) => {
    closeDrawer();
    router.push(path as any);
  };

  const handleSignOut = () => {
    closeDrawer();
    if (Platform.OS === 'web') {
      if (window.confirm('Sign out?')) signOut();
    } else {
      signOut();
    }
  };

  if (!visible) return null;

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      <Animated.View style={[styles.backdrop, { opacity: backdropOpacity }]}>
        <TouchableOpacity style={StyleSheet.absoluteFill} onPress={closeDrawer} activeOpacity={1} />
      </Animated.View>

      <Animated.View style={[styles.panel, { transform: [{ translateX }], paddingTop: insets.top + 16, paddingBottom: insets.bottom + 16 }]}>
        {/* Header */}
        <View style={styles.header}>
          <FinchLogo size={24} />
          <TouchableOpacity onPress={closeDrawer} style={styles.closeBtn} activeOpacity={0.7}>
            <X size={20} color="#9ca3af" />
          </TouchableOpacity>
        </View>

        {/* Actions */}
        <View style={styles.actions}>
          <TouchableOpacity style={styles.actionRow} onPress={createNewChat} activeOpacity={0.7}>
            <SquarePen size={18} color="#d1d5db" />
            <Text style={styles.actionText}>New chat</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionRow} onPress={() => navigate('/(tabs)')} activeOpacity={0.7}>
            <Search size={18} color="#d1d5db" />
            <Text style={styles.actionText}>Search stocks</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionRow} onPress={() => navigate('/(tabs)')} activeOpacity={0.7}>
            <BarChart3 size={18} color="#d1d5db" />
            <Text style={styles.actionText}>Markets</Text>
          </TouchableOpacity>
        </View>

        {/* Recents */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Recents</Text>
        </View>

        <ScrollView style={styles.chatList} showsVerticalScrollIndicator={false}>
          {chats.slice(0, 30).map((chat) => (
            <TouchableOpacity
              key={chat.chat_id}
              style={styles.chatRow}
              onPress={() => openChat(chat.chat_id)}
              activeOpacity={0.6}
            >
              <Text style={styles.chatTitle} numberOfLines={1}>
                {chat.icon ? `${chat.icon} ` : ''}{chat.title || 'New Chat'}
              </Text>
            </TouchableOpacity>
          ))}
          {chats.length === 0 && (
            <Text style={styles.emptyText}>No chats yet</Text>
          )}
        </ScrollView>

        {/* Footer - Profile */}
        <View style={styles.footer}>
          <TouchableOpacity
            style={styles.profileRow}
            onPress={() => navigate('/settings')}
            activeOpacity={0.7}
          >
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {(user?.user_metadata?.full_name || 'U')[0].toUpperCase()}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.profileName} numberOfLines={1}>
                {user?.user_metadata?.full_name || 'User'}
              </Text>
            </View>
          </TouchableOpacity>
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  panel: {
    position: 'absolute',
    top: 0,
    left: 0,
    bottom: 0,
    width: SIDEBAR_WIDTH,
    backgroundColor: '#171717',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    marginBottom: 28,
  },
  closeBtn: {
    padding: 4,
  },
  actions: {
    paddingHorizontal: 12,
    marginBottom: 28,
    gap: 2,
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingVertical: 11,
    paddingHorizontal: 12,
    borderRadius: 10,
  },
  actionText: {
    fontSize: 15,
    fontFamily: 'DMSans',
    color: '#e5e7eb',
  },
  sectionHeader: {
    paddingHorizontal: 24,
    marginBottom: 6,
  },
  sectionTitle: {
    fontSize: 12,
    fontFamily: 'DMSans-Bold',
    color: '#6b7280',
    letterSpacing: 0.5,
  },
  chatList: {
    flex: 1,
    paddingHorizontal: 12,
  },
  chatRow: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  chatTitle: {
    fontSize: 14,
    fontFamily: 'DMSans',
    color: '#d1d5db',
  },
  emptyText: {
    fontSize: 13,
    fontFamily: 'DMSans',
    color: '#4b5563',
    paddingHorizontal: 12,
    paddingVertical: 16,
  },
  footer: {
    borderTopWidth: 1,
    borderTopColor: '#262626',
    paddingTop: 16,
    paddingHorizontal: 16,
  },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 8,
  },
  avatar: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: '#059669',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 14,
    fontFamily: 'DMSans-Bold',
    color: '#fff',
  },
  profileName: {
    fontSize: 14,
    fontFamily: 'DMSans-Medium',
    color: '#e5e7eb',
  },
});
