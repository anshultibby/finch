import { View, Text, ScrollView, RefreshControl, ActivityIndicator, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useFocusEffect } from 'expo-router';
import { useState, useCallback } from 'react';
import { alpacaBrokerApi } from '@/lib/api';
import type { AlpacaBrokerPosition, AlpacaBrokerAccountDetail } from '@/lib/types';
import { DollarSign, ClipboardList } from 'lucide-react-native';
import { COLORS } from '@/lib/constants';
import AccountSummary from '@/components/portfolio/AccountSummary';
import PositionRow from '@/components/portfolio/PositionRow';
import SectionHeader from '@/components/ui/SectionHeader';
import EmptyState from '@/components/ui/EmptyState';

export default function PortfolioScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [account, setAccount] = useState<AlpacaBrokerAccountDetail | null>(null);
  const [positions, setPositions] = useState<AlpacaBrokerPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchPortfolio = useCallback(async () => {
    if (!user) return;
    try {
      const data = await alpacaBrokerApi.getPortfolio(user.id);
      if (data.success) {
        setAccount(data.account);
        setPositions(data.positions || []);
      }
    } catch {
    } finally {
      setLoading(false);
    }
  }, [user]);

  useFocusEffect(useCallback(() => {
    fetchPortfolio();
  }, [fetchPortfolio]));

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchPortfolio();
    setRefreshing(false);
  }, [fetchPortfolio]);

  const equity = parseFloat(account?.equity || '0');
  const cash = parseFloat(account?.cash || '0');
  const buyingPower = parseFloat(account?.buying_power || '0');
  const totalUnrealizedPl = positions.reduce((sum, p) => sum + parseFloat(p.unrealized_pl || '0'), 0);

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <View className="flex-row items-center justify-between px-5 pt-2 pb-3">
        <Text className="text-2xl font-body-bold text-gray-900">Portfolio</Text>
        <TouchableOpacity
          onPress={() => router.push('/orders')}
          className="flex-row items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-gray-200"
          activeOpacity={0.7}
        >
          <ClipboardList size={14} color={COLORS.gray500} />
          <Text className="text-sm font-body-medium text-gray-600">Orders</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator size="large" color={COLORS.gray900} />
        </View>
      ) : !account ? (
        <EmptyState
          icon={<DollarSign size={48} color="#cbd5e1" />}
          title="No account connected"
          description="Set up your trading account to see your portfolio"
        />
      ) : (
        <ScrollView
          className="flex-1"
          contentContainerClassName="px-5 pb-8"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          showsVerticalScrollIndicator={false}
        >
          <AccountSummary
            equity={equity}
            cash={cash}
            buyingPower={buyingPower}
            unrealizedPl={totalUnrealizedPl}
          />

          <View className="mt-5">
            <SectionHeader title="Positions" count={positions.length} />

            {positions.length === 0 ? (
              <View className="bg-white rounded-2xl p-8 items-center border border-gray-200">
                <Text className="text-gray-400 font-body">No open positions</Text>
              </View>
            ) : (
              <View className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                {positions.map((pos, i) => (
                  <PositionRow
                    key={pos.symbol}
                    symbol={pos.symbol}
                    qty={pos.qty}
                    avgEntry={pos.avg_entry_price}
                    marketValue={pos.market_value}
                    unrealizedPl={pos.unrealized_pl}
                    unrealizedPlPc={pos.unrealized_plpc}
                    currentPrice={pos.current_price}
                    onPress={() => router.push(`/stock/${pos.symbol}`)}
                    isLast={i === positions.length - 1}
                  />
                ))}
              </View>
            )}
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}
