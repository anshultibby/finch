import React, { useEffect, useRef, useState } from 'react';
import { View, Text, TouchableOpacity, Animated, StyleSheet, ScrollView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useDrawer } from '@/contexts/DrawerContext';
import { chatApi } from '@/lib/api';
import {
  X, SquarePen, Search, Star, BarChart3, Wallet, Settings,
  ChevronDown, MessageSquare,
} from 'lucide-react-native';
import FinchLogo from '@/components/FinchLogo';
import { COLORS } from '@/lib/constants';

const SIDEBAR_WIDTH = 308;

interface ChatItem {
  chat_id: string;
  title: string | null;
  icon: string | null;
  updated_at: string;
}

export default function Sidebar() {
  const { isOpen, closeDrawer } = useDrawer();
  const { user } = useAuth();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const translateX = useRef(new Animated.Value(-SIDEBAR_WIDTH)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;
  const [visible, setVisible] = useState(false);
  const [chats, setChats] = useState<ChatItem[]>([]);
  const [recentsOpen, setRecentsOpen] = useState(true);

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

  const go = (path: string) => {
    closeDrawer();
    router.push(path as any);
  };

  const createNewChat = async () => {
    if (!user) return;
    closeDrawer();
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}`);
    } catch {}
  };

  if (!visible) return null;

  const fullName = user?.user_metadata?.full_name || 'User';
  const initial = fullName[0].toUpperCase();

  const navItems = [
    { icon: SquarePen, label: 'New chat', onPress: createNewChat },
    { icon: BarChart3, label: 'Markets', onPress: () => go('/(tabs)?tab=markets') },
    { icon: Star, label: 'Watchlist', onPress: () => go('/(tabs)?tab=watchlist') },
    { icon: Wallet, label: 'Portfolio', onPress: () => go('/(tabs)?tab=portfolio') },
  ];

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      <Animated.View style={[styles.backdrop, { opacity: backdropOpacity }]}>
        <TouchableOpacity style={StyleSheet.absoluteFill} onPress={closeDrawer} activeOpacity={1} />
      </Animated.View>

      <Animated.View style={[styles.panel, { transform: [{ translateX }], paddingTop: insets.top + 14, paddingBottom: insets.bottom + 12 }]}>
        {/* Header */}
        <View style={styles.header}>
          <FinchLogo size={24} showText />
          <TouchableOpacity onPress={closeDrawer} style={styles.closeBtn} activeOpacity={0.7}>
            <X size={20} color={COLORS.gray400} />
          </TouchableOpacity>
        </View>

        {/* Search */}
        <TouchableOpacity style={styles.search} onPress={() => go('/(tabs)')} activeOpacity={0.7}>
          <Search size={16} color={COLORS.gray400} />
          <Text style={styles.searchText}>Search stocks…</Text>
        </TouchableOpacity>

        {/* Primary nav */}
        <View style={styles.nav}>
          {navItems.map(({ icon: Icon, label, onPress }) => (
            <TouchableOpacity key={label} style={styles.navRow} onPress={onPress} activeOpacity={0.6}>
              <Icon size={18} color={COLORS.gray700} strokeWidth={2} />
              <Text style={styles.navText}>{label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Recents (collapsible) */}
        <TouchableOpacity
          style={styles.sectionHeader}
          onPress={() => setRecentsOpen(o => !o)}
          activeOpacity={0.6}
        >
          <Text style={styles.sectionTitle}>Recents</Text>
          <ChevronDown
            size={15}
            color={COLORS.gray400}
            style={{ transform: [{ rotate: recentsOpen ? '0deg' : '-90deg' }] }}
          />
        </TouchableOpacity>

        {recentsOpen && (
          <ScrollView style={styles.chatList} showsVerticalScrollIndicator={false}>
            {chats.slice(0, 40).map((chat) => (
              <TouchableOpacity
                key={chat.chat_id}
                style={styles.chatRow}
                onPress={() => go(`/(tabs)/chat/${chat.chat_id}`)}
                activeOpacity={0.6}
              >
                <MessageSquare size={14} color={COLORS.gray400} />
                <Text style={styles.chatTitle} numberOfLines={1}>
                  {chat.icon ? `${chat.icon} ` : ''}{chat.title || 'New chat'}
                </Text>
              </TouchableOpacity>
            ))}
            {chats.length === 0 && <Text style={styles.emptyText}>No chats yet</Text>}
          </ScrollView>
        )}
        {!recentsOpen && <View style={{ flex: 1 }} />}

        {/* Account footer */}
        <View style={styles.footer}>
          <TouchableOpacity style={styles.profileRow} onPress={() => go('/(tabs)/profile')} activeOpacity={0.7}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{initial}</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.profileName} numberOfLines={1}>{fullName}</Text>
              {!!user?.email && <Text style={styles.profileEmail} numberOfLines={1}>{user.email}</Text>}
            </View>
            <TouchableOpacity onPress={() => go('/settings')} style={styles.gearBtn} activeOpacity={0.7}>
              <Settings size={18} color={COLORS.gray400} />
            </TouchableOpacity>
          </TouchableOpacity>
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(15,23,42,0.28)',
  },
  panel: {
    position: 'absolute',
    top: 0,
    left: 0,
    bottom: 0,
    width: SIDEBAR_WIDTH,
    backgroundColor: '#fafaf9',
    borderRightWidth: 1,
    borderRightColor: 'rgba(0,0,0,0.06)',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 18,
    marginBottom: 16,
  },
  closeBtn: { padding: 4 },
  search: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    marginHorizontal: 14,
    height: 40,
    paddingHorizontal: 12,
    borderRadius: 12,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    marginBottom: 14,
  },
  searchText: { fontSize: 14, fontFamily: 'DMSans', color: COLORS.gray400 },
  nav: {
    paddingHorizontal: 10,
    marginBottom: 18,
    gap: 1,
  },
  navRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 13,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 10,
  },
  navText: {
    fontSize: 15,
    fontFamily: 'DMSans-Medium',
    color: '#0f172a',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 22,
    paddingRight: 18,
    marginBottom: 4,
  },
  sectionTitle: {
    fontSize: 11,
    fontFamily: 'DMSans-Bold',
    color: COLORS.gray400,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  chatList: {
    flex: 1,
    paddingHorizontal: 10,
    marginTop: 2,
  },
  chatRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 9,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  chatTitle: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'DMSans',
    color: COLORS.gray700,
  },
  emptyText: {
    fontSize: 13,
    fontFamily: 'DMSans',
    color: COLORS.gray400,
    paddingHorizontal: 12,
    paddingVertical: 14,
  },
  footer: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.06)',
    paddingTop: 10,
    paddingHorizontal: 10,
    marginTop: 4,
  },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
    paddingVertical: 6,
    paddingHorizontal: 8,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: COLORS.emerald,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { fontSize: 15, fontFamily: 'DMSans-Bold', color: '#fff' },
  profileName: { fontSize: 14, fontFamily: 'DMSans-Medium', color: '#0f172a' },
  profileEmail: { fontSize: 12, fontFamily: 'DMSans', color: COLORS.gray400, marginTop: 1 },
  gearBtn: { padding: 6 },
});
