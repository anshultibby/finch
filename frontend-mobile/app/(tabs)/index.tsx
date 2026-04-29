import { View, Text, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { useState, useEffect, useCallback } from 'react';
import { alpacaBrokerApi, marketApi } from '@/lib/api';
import { TrendingUp, TrendingDown, MessageSquare, BarChart3, LogOut } from 'lucide-react-native';

interface PortfolioSummary {
  equity: string;
  cash: string;
  buyingPower: string;
  positions: Array<{
    symbol: string;
    qty: string;
    unrealized_pl: string;
    unrealized_plpc: string;
    current_price: string;
  }>;
}

export default function HomeScreen() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    if (!user) return;
    try {
      const data = await alpacaBrokerApi.getPortfolio(user.id);
      if (data.success) {
        setPortfolio({
          equity: data.account?.equity || '0',
          cash: data.account?.cash || '0',
          buyingPower: data.account?.buying_power || '0',
          positions: data.positions || [],
        });
      }
    } catch {
      // Account may not exist yet
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  }, [fetchData]);

  const equity = parseFloat(portfolio?.equity || '0');
  const cash = parseFloat(portfolio?.cash || '0');

  return (
    <SafeAreaView className="flex-1 bg-finch-bg" edges={['top']}>
      <ScrollView
        className="flex-1"
        contentContainerClassName="px-5 pb-8"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Header */}
        <View className="flex-row items-center justify-between mt-2 mb-6">
          <View>
            <Text className="text-sm font-body text-slate-500">Welcome back</Text>
            <Text className="text-2xl font-body-bold text-slate-900">
              {user?.user_metadata?.full_name?.split(' ')[0] || 'Trader'}
            </Text>
          </View>
          <TouchableOpacity onPress={signOut} className="p-2" activeOpacity={0.7}>
            <LogOut size={20} color="#94a3b8" />
          </TouchableOpacity>
        </View>

        {/* Portfolio Value Card */}
        <View className="bg-white rounded-2xl p-5 mb-4 border border-black/5">
          <Text className="text-sm font-body text-slate-500 mb-1">Portfolio Value</Text>
          {loading ? (
            <ActivityIndicator className="py-4" />
          ) : (
            <>
              <Text className="text-3xl font-body-bold text-slate-900">
                ${equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </Text>
              <Text className="text-sm font-body text-slate-400 mt-1">
                Cash: ${cash.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </Text>
            </>
          )}
        </View>

        {/* Quick Actions */}
        <View className="flex-row gap-3 mb-6">
          <TouchableOpacity
            onPress={() => router.push('/(tabs)/chat')}
            className="flex-1 bg-slate-900 rounded-2xl p-4 flex-row items-center justify-center gap-2"
            activeOpacity={0.8}
          >
            <MessageSquare size={18} color="#ffffff" />
            <Text className="text-white font-body-medium text-sm">New Chat</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => router.push('/orders')}
            className="flex-1 bg-white rounded-2xl p-4 flex-row items-center justify-center gap-2 border border-black/5"
            activeOpacity={0.8}
          >
            <BarChart3 size={18} color="#0f172a" />
            <Text className="text-slate-900 font-body-medium text-sm">Orders</Text>
          </TouchableOpacity>
        </View>

        {/* Positions */}
        <Text className="text-lg font-body-bold text-slate-900 mb-3">Positions</Text>
        {loading ? (
          <ActivityIndicator className="py-8" />
        ) : portfolio?.positions && portfolio.positions.length > 0 ? (
          <View className="bg-white rounded-2xl border border-black/5 overflow-hidden">
            {portfolio.positions.map((pos, i) => {
              const pl = parseFloat(pos.unrealized_pl || '0');
              const plPct = parseFloat(pos.unrealized_plpc || '0') * 100;
              const isPositive = pl >= 0;

              return (
                <TouchableOpacity
                  key={pos.symbol}
                  onPress={() => router.push(`/stock/${pos.symbol}`)}
                  className={`flex-row items-center justify-between p-4 ${i > 0 ? 'border-t border-black/5' : ''}`}
                  activeOpacity={0.7}
                >
                  <View>
                    <Text className="text-base font-body-bold text-slate-900">{pos.symbol}</Text>
                    <Text className="text-sm font-body text-slate-500">{pos.qty} shares</Text>
                  </View>
                  <View className="items-end">
                    <Text className="text-base font-body-medium text-slate-900">
                      ${parseFloat(pos.current_price).toFixed(2)}
                    </Text>
                    <View className="flex-row items-center gap-1">
                      {isPositive ? (
                        <TrendingUp size={12} color="#059669" />
                      ) : (
                        <TrendingDown size={12} color="#dc2626" />
                      )}
                      <Text className={`text-sm font-body ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                        {isPositive ? '+' : ''}{plPct.toFixed(2)}%
                      </Text>
                    </View>
                  </View>
                </TouchableOpacity>
              );
            })}
          </View>
        ) : (
          <View className="bg-white rounded-2xl p-8 items-center border border-black/5">
            <Text className="text-slate-400 font-body text-center">
              No positions yet. Start a chat to explore trading ideas.
            </Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
