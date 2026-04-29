import { View, Text, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useState, useEffect, useCallback } from 'react';
import { alpacaBrokerApi } from '@/lib/api';
import type { AlpacaOrder } from '@/lib/types';
import { X } from 'lucide-react-native';

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
    } catch {
      setOrders([]);
    } finally {
      setLoading(false);
    }
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

  const cancelOrder = async (orderId: string) => {
    if (!user) return;
    Alert.alert('Cancel Order', 'Are you sure you want to cancel this order?', [
      { text: 'No', style: 'cancel' },
      {
        text: 'Yes, Cancel',
        style: 'destructive',
        onPress: async () => {
          try {
            await alpacaBrokerApi.cancelOrder(user.id, orderId);
            fetchOrders();
          } catch {}
        },
      },
    ]);
  };

  const statusColor = (status: string) => {
    if (['filled', 'partially_filled'].includes(status)) return 'text-emerald-600';
    if (['canceled', 'expired', 'rejected'].includes(status)) return 'text-red-600';
    return 'text-amber-600';
  };

  return (
    <SafeAreaView className="flex-1 bg-finch-bg" edges={[]}>
      {/* Tabs */}
      <View className="flex-row px-5 py-3 gap-2">
        {(['open', 'closed', 'all'] as TabFilter[]).map(t => (
          <TouchableOpacity
            key={t}
            onPress={() => setTab(t)}
            className={`px-4 py-2 rounded-full ${tab === t ? 'bg-slate-900' : 'bg-white border border-black/5'}`}
            activeOpacity={0.8}
          >
            <Text className={`text-sm font-body-medium capitalize ${tab === t ? 'text-white' : 'text-slate-600'}`}>
              {t}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator size="large" color="#0f172a" />
        </View>
      ) : (
        <FlatList
          data={orders}
          keyExtractor={(item) => item.id}
          contentContainerClassName="px-5 pb-4"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          renderItem={({ item }) => (
            <View className="bg-white rounded-2xl p-4 mb-3 border border-black/5">
              <View className="flex-row items-start justify-between">
                <View className="flex-1">
                  <View className="flex-row items-center gap-2">
                    <Text className="text-base font-body-bold text-slate-900">{item.symbol}</Text>
                    <View className={`px-2 py-0.5 rounded-full ${item.side === 'buy' ? 'bg-emerald-50' : 'bg-red-50'}`}>
                      <Text className={`text-xs font-body-medium uppercase ${item.side === 'buy' ? 'text-emerald-600' : 'text-red-600'}`}>
                        {item.side}
                      </Text>
                    </View>
                  </View>
                  <Text className="text-sm font-body text-slate-500 mt-1">
                    {item.qty || item.notional} · {item.type} · {item.time_in_force}
                  </Text>
                  <Text className={`text-sm font-body mt-1 capitalize ${statusColor(item.status)}`}>
                    {item.status.replace(/_/g, ' ')}
                  </Text>
                </View>
                {['new', 'accepted', 'pending_new'].includes(item.status) && (
                  <TouchableOpacity
                    onPress={() => cancelOrder(item.id)}
                    className="p-2"
                    activeOpacity={0.7}
                  >
                    <X size={18} color="#ef4444" />
                  </TouchableOpacity>
                )}
              </View>
              <Text className="text-xs font-body text-slate-400 mt-2">
                {new Date(item.created_at).toLocaleString()}
              </Text>
            </View>
          )}
          ListEmptyComponent={
            <View className="py-20 items-center">
              <Text className="text-slate-400 font-body">No {tab} orders</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}
