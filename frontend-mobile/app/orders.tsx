import { View, Text, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator, Alert, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useState, useEffect, useCallback } from 'react';
import { alpacaBrokerApi } from '@/lib/api';
import type { AlpacaOrder } from '@/lib/types';
import { X, ClipboardList } from 'lucide-react-native';
import { COLORS, formatRelativeTime } from '@/lib/constants';
import * as Haptics from 'expo-haptics';
import SegmentedControl from '@/components/ui/SegmentedControl';
import EmptyState from '@/components/ui/EmptyState';

type TabFilter = 'open' | 'closed' | 'all';

export default function OrdersScreen() {
  const { user } = useAuth();
  const [orders, setOrders] = useState<AlpacaOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tab, setTab] = useState<TabFilter>('open');

  const fetchOrders = useCallback(async () => {
    if (!user) return;
    try {
      const data = await alpacaBrokerApi.getOrders(user.id, tab, 50);
      setOrders(data || []);
    } catch { setOrders([]); }
    finally { setLoading(false); }
  }, [user, tab]);

  useEffect(() => {
    setLoading(true);
    fetchOrders();
  }, [fetchOrders]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchOrders();
    setRefreshing(false);
  }, [fetchOrders]);

  const cancelOrder = (orderId: string) => {
    if (!user) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    Alert.alert('Cancel Order', 'Are you sure?', [
      { text: 'No', style: 'cancel' },
      {
        text: 'Cancel Order', style: 'destructive',
        onPress: async () => { try { await alpacaBrokerApi.cancelOrder(user.id, orderId); fetchOrders(); } catch {} },
      },
    ]);
  };

  const statusColor = (status: string) => {
    if (['filled', 'partially_filled'].includes(status)) return { text: 'text-emerald-600', bg: '#ecfdf5' };
    if (['canceled', 'expired', 'rejected'].includes(status)) return { text: 'text-red-500', bg: '#fef2f2' };
    return { text: 'text-amber-600', bg: '#fffbeb' };
  };

  return (
    <SafeAreaView className="flex-1 bg-white" edges={[]}>
      <View className="px-4 py-2.5">
        <SegmentedControl options={['open', 'closed', 'all']} selected={tab} onChange={setTab} />
      </View>

      {loading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color={COLORS.gray400} />
        </View>
      ) : orders.length === 0 ? (
        <EmptyState icon={<ClipboardList size={40} color="#d1d5db" />} title={`No ${tab} orders`} />
      ) : (
        <FlatList
          data={orders}
          keyExtractor={(item) => item.id}
          contentContainerClassName="px-4 pb-4"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
          renderItem={({ item }) => {
            const sc = statusColor(item.status);
            return (
              <View style={styles.orderCard}>
                <View className="flex-row items-start justify-between">
                  <View className="flex-1">
                    <View className="flex-row items-center gap-1.5 mb-1">
                      <Text className="text-[14px] font-body-bold text-gray-900">{item.symbol}</Text>
                      <View className="px-1.5 py-px rounded-md" style={{ backgroundColor: item.side === 'buy' ? '#ecfdf5' : '#fef2f2' }}>
                        <Text className={`text-[10px] font-body-bold uppercase ${item.side === 'buy' ? 'text-emerald-600' : 'text-red-500'}`}>
                          {item.side}
                        </Text>
                      </View>
                      <View className="px-1.5 py-px rounded-md" style={{ backgroundColor: sc.bg }}>
                        <Text className={`text-[10px] font-body-medium capitalize ${sc.text}`}>
                          {item.status.replace(/_/g, ' ')}
                        </Text>
                      </View>
                    </View>
                    <Text className="text-[12px] font-body text-gray-500">
                      {item.qty || item.notional} · {item.type} · {item.time_in_force}
                    </Text>
                    {item.filled_avg_price && (
                      <Text className="text-[12px] font-body text-gray-500 mt-px">
                        Filled @ ${parseFloat(item.filled_avg_price).toFixed(2)}
                      </Text>
                    )}
                  </View>
                  {['new', 'accepted', 'pending_new'].includes(item.status) && (
                    <TouchableOpacity onPress={() => cancelOrder(item.id)} className="p-1.5" activeOpacity={0.7}>
                      <X size={16} color="#ef4444" />
                    </TouchableOpacity>
                  )}
                </View>
                <Text className="text-[11px] font-body text-gray-400 mt-2">{formatRelativeTime(item.created_at)}</Text>
              </View>
            );
          }}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  orderCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
});
