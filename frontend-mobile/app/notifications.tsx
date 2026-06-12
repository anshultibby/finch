import { View, Text, FlatList, TouchableOpacity, ActivityIndicator, RefreshControl, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Stack, useRouter } from 'expo-router';
import { useState, useEffect, useCallback } from 'react';
import { notificationsApi } from '@/lib/api';
import { syncBadgeCount } from '@/lib/pushNotifications';
import { MessageSquare, TrendingUp, Bell, CheckCheck } from 'lucide-react-native';
import { COLORS, formatRelativeTime } from '@/lib/constants';

interface NotificationItem {
  id: string;
  title: string;
  body: string;
  type: string;
  data?: Record<string, any>;
  read: boolean;
  created_at: string;
}

const TYPE_ICONS: Record<string, (color: string) => React.ReactNode> = {
  chat: (c) => <MessageSquare size={18} color={c} />,
  trade: (c) => <TrendingUp size={18} color={c} />,
  general: (c) => <Bell size={18} color={c} />,
  system: (c) => <Bell size={18} color={c} />,
};

export default function NotificationsScreen() {
  const router = useRouter();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await notificationsApi.getNotifications(50);
      const items: NotificationItem[] = data.notifications || [];
      setNotifications(items);
      syncBadgeCount(items.filter(n => !n.read).length);
    } catch {} finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchNotifications(); }, [fetchNotifications]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchNotifications();
    setRefreshing(false);
  }, [fetchNotifications]);

  const markAllRead = async () => {
    try {
      await notificationsApi.markRead();
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      syncBadgeCount(0);
    } catch {}
  };

  const handlePress = async (notif: NotificationItem) => {
    if (!notif.read) {
      try {
        await notificationsApi.markRead([notif.id]);
        setNotifications(prev => {
          const next = prev.map(n => n.id === notif.id ? { ...n, read: true } : n);
          syncBadgeCount(next.filter(n => !n.read).length);
          return next;
        });
      } catch {}
    }

    if (notif.data?.chatId) {
      router.push(`/(tabs)/chat/${notif.data.chatId}`);
    } else if (notif.data?.symbol) {
      router.push(`/stock/${notif.data.symbol}`);
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <>
      <Stack.Screen options={{ headerTitle: 'Notifications', headerStyle: { backgroundColor: '#fff' } }} />
      <SafeAreaView style={{ flex: 1, backgroundColor: '#fff' }} edges={['bottom']}>
        {unreadCount > 0 && (
          <TouchableOpacity onPress={markAllRead} style={ns.markAllBtn} activeOpacity={0.7}>
            <CheckCheck size={14} color="#059669" />
            <Text style={ns.markAllText}>Mark all as read</Text>
          </TouchableOpacity>
        )}

        {loading ? (
          <View className="flex-1 items-center justify-center">
            <ActivityIndicator color={COLORS.gray400} />
          </View>
        ) : (
          <FlatList
            data={notifications}
            keyExtractor={item => item.id}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
            contentContainerStyle={{ paddingBottom: 20 }}
            renderItem={({ item }) => {
              const iconFn = TYPE_ICONS[item.type] || TYPE_ICONS.general;
              return (
                <TouchableOpacity
                  onPress={() => handlePress(item)}
                  style={[ns.row, !item.read && ns.unreadRow]}
                  activeOpacity={0.6}
                >
                  <View style={[ns.iconCircle, { backgroundColor: !item.read ? '#ecfdf5' : '#f9fafb' }]}>
                    {iconFn(!item.read ? '#059669' : '#9ca3af')}
                  </View>
                  <View style={{ flex: 1, marginLeft: 12 }}>
                    <Text style={[ns.title, !item.read && { color: '#111827' }]} numberOfLines={1}>{item.title}</Text>
                    <Text style={ns.body} numberOfLines={2}>{item.body}</Text>
                    <Text style={ns.time}>{formatRelativeTime(item.created_at)}</Text>
                  </View>
                  {!item.read && <View style={ns.dot} />}
                </TouchableOpacity>
              );
            }}
            ListEmptyComponent={
              <View className="py-20 items-center">
                <Bell size={48} color="#e5e7eb" />
                <Text style={ns.emptyTitle}>No notifications</Text>
                <Text style={ns.emptyDesc}>You'll see updates here when your analyses and research complete.</Text>
              </View>
            }
          />
        )}
      </SafeAreaView>
    </>
  );
}

const ns = StyleSheet.create({
  markAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  markAllText: {
    fontSize: 13,
    fontFamily: 'DMSans-Medium',
    color: '#059669',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#f9fafb',
  },
  unreadRow: {
    backgroundColor: '#fafffe',
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 14,
    fontFamily: 'DMSans-Medium',
    color: '#6b7280',
  },
  body: {
    fontSize: 13,
    fontFamily: 'DMSans',
    color: '#9ca3af',
    lineHeight: 18,
    marginTop: 2,
  },
  time: {
    fontSize: 11,
    fontFamily: 'DMSans',
    color: '#d1d5db',
    marginTop: 4,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#059669',
    marginTop: 6,
    marginLeft: 8,
  },
  emptyTitle: {
    fontSize: 16,
    fontFamily: 'DMSans-Bold',
    color: '#9ca3af',
    marginTop: 16,
  },
  emptyDesc: {
    fontSize: 13,
    fontFamily: 'DMSans',
    color: '#d1d5db',
    textAlign: 'center',
    marginTop: 6,
    paddingHorizontal: 40,
    lineHeight: 18,
  },
});
