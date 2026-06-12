import React, { useEffect, useRef, useState } from 'react';
import { View, Text, TouchableOpacity, Animated, StyleSheet, ScrollView, Platform, Modal, Pressable, Alert, Share, TextInput } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useDrawer } from '@/contexts/DrawerContext';
import { chatApi } from '@/lib/api';
import {
  X, SquarePen, Search, Star, BarChart3, Wallet, Settings,
  ChevronDown, MessageSquare, MoreHorizontal, Share2, Pencil, Trash2, LogIn,
} from 'lucide-react-native';
import FinchLogo from '@/components/FinchLogo';
import { COLORS } from '@/lib/constants';

const SIDEBAR_WIDTH = 308;

// Public share links open the web app (mobile has no in-app shared route).
const WEB_BASE_URL = process.env.EXPO_PUBLIC_WEB_URL || 'https://finchapp.ai';

interface ChatItem {
  chat_id: string;
  title: string | null;
  icon: string | null;
  updated_at: string;
  is_public?: boolean;
  share_token?: string | null;
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
  const [menuChat, setMenuChat] = useState<ChatItem | null>(null);
  const [renameTarget, setRenameTarget] = useState<ChatItem | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [busy, setBusy] = useState(false);

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
    closeDrawer();
    if (!user) {
      router.push('/(auth)/login');
      return;
    }
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}`);
    } catch {}
  };

  const handleShare = async (chat: ChatItem) => {
    setMenuChat(null);
    setBusy(true);
    try {
      let token = chat.is_public ? chat.share_token : null;
      if (!token) {
        const res = await chatApi.shareChat(chat.chat_id);
        token = res.share_token;
        setChats(prev => prev.map(c => c.chat_id === chat.chat_id ? { ...c, is_public: res.is_public, share_token: res.share_token } : c));
      }
      if (token) {
        const url = `${WEB_BASE_URL}/share/chat/${token}`;
        await Share.share({ url, message: url });
      }
    } catch {} finally { setBusy(false); }
  };

  const openRename = (chat: ChatItem) => {
    setMenuChat(null);
    setRenameValue(chat.title || '');
    setRenameTarget(chat);
  };

  const submitRename = async () => {
    const target = renameTarget;
    const next = renameValue.trim();
    if (!target || !next || next === target.title) { setRenameTarget(null); return; }
    setBusy(true);
    try {
      await chatApi.renameChat(target.chat_id, next);
      setChats(prev => prev.map(c => c.chat_id === target.chat_id ? { ...c, title: next } : c));
      setRenameTarget(null);
    } catch {} finally { setBusy(false); }
  };

  const confirmDelete = (chat: ChatItem) => {
    setMenuChat(null);
    Alert.alert('Delete chat', 'Delete this chat? This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await chatApi.deleteChat(chat.chat_id);
            setChats(prev => prev.filter(c => c.chat_id !== chat.chat_id));
          } catch {}
        },
      },
    ]);
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
              <View key={chat.chat_id} style={styles.chatRow}>
                <TouchableOpacity
                  style={styles.chatRowMain}
                  onPress={() => go(`/(tabs)/chat/${chat.chat_id}`)}
                  activeOpacity={0.6}
                >
                  <MessageSquare size={14} color={COLORS.gray400} />
                  <Text style={styles.chatTitle} numberOfLines={1}>
                    {chat.icon ? `${chat.icon} ` : ''}{chat.title || 'New chat'}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.kebab}
                  onPress={() => setMenuChat(chat)}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                  activeOpacity={0.6}
                >
                  <MoreHorizontal size={16} color={COLORS.gray400} />
                </TouchableOpacity>
              </View>
            ))}
            {chats.length === 0 && <Text style={styles.emptyText}>No chats yet</Text>}
          </ScrollView>
        )}
        {!recentsOpen && <View style={{ flex: 1 }} />}

        {/* Account footer */}
        <View style={styles.footer}>
          {user ? (
            <TouchableOpacity style={styles.profileRow} onPress={() => go('/settings')} activeOpacity={0.7}>
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
          ) : (
            <TouchableOpacity style={styles.profileRow} onPress={() => go('/(auth)/login')} activeOpacity={0.7}>
              <View style={styles.avatar}>
                <LogIn size={17} color="#fff" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.profileName} numberOfLines={1}>Sign in</Text>
                <Text style={styles.profileEmail} numberOfLines={1}>Free to sign up</Text>
              </View>
            </TouchableOpacity>
          )}
        </View>
      </Animated.View>

      {/* Per-chat action menu */}
      <Modal visible={!!menuChat} transparent animationType="fade" onRequestClose={() => setMenuChat(null)}>
        <Pressable style={styles.menuOverlay} onPress={() => setMenuChat(null)}>
          <View style={styles.menuCard}>
            <Text style={styles.menuTitle} numberOfLines={1}>{menuChat?.title || 'New chat'}</Text>
            <TouchableOpacity style={styles.menuRow} onPress={() => menuChat && handleShare(menuChat)} activeOpacity={0.6}>
              <Share2 size={18} color={COLORS.gray700} />
              <Text style={styles.menuText}>Share</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.menuRow} onPress={() => menuChat && openRename(menuChat)} activeOpacity={0.6}>
              <Pencil size={18} color={COLORS.gray700} />
              <Text style={styles.menuText}>Rename</Text>
            </TouchableOpacity>
            <View style={styles.menuDivider} />
            <TouchableOpacity style={styles.menuRow} onPress={() => menuChat && confirmDelete(menuChat)} activeOpacity={0.6}>
              <Trash2 size={18} color={COLORS.red} />
              <Text style={[styles.menuText, { color: COLORS.red }]}>Delete</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Modal>

      {/* Rename modal */}
      <Modal visible={!!renameTarget} transparent animationType="fade" onRequestClose={() => setRenameTarget(null)}>
        <Pressable style={styles.menuOverlay} onPress={() => setRenameTarget(null)}>
          <Pressable style={styles.renameCard} onPress={() => {}}>
            <Text style={styles.renameTitle}>Rename chat</Text>
            <TextInput
              value={renameValue}
              onChangeText={setRenameValue}
              autoFocus
              placeholder="Chat title"
              placeholderTextColor={COLORS.gray400}
              style={styles.renameInput}
              onSubmitEditing={submitRename}
              returnKeyType="done"
            />
            <View style={styles.renameActions}>
              <TouchableOpacity onPress={() => setRenameTarget(null)} activeOpacity={0.6} style={styles.renameBtn}>
                <Text style={styles.renameCancel}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={submitRename} disabled={busy} activeOpacity={0.6} style={[styles.renameBtn, styles.renameSave]}>
                <Text style={styles.renameSaveText}>Save</Text>
              </TouchableOpacity>
            </View>
          </Pressable>
        </Pressable>
      </Modal>
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
    borderRadius: 8,
  },
  chatRowMain: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 9,
    paddingLeft: 12,
    paddingRight: 4,
    minWidth: 0,
  },
  kebab: {
    paddingHorizontal: 8,
    paddingVertical: 9,
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
  menuTitle: {
    fontSize: 12,
    fontFamily: 'DMSans-Medium',
    color: COLORS.gray400,
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
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
