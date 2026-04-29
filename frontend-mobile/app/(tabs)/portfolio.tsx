import { View, Text, ScrollView, RefreshControl, ActivityIndicator, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { useState, useEffect, useCallback } from 'react';
import { alpacaBrokerApi } from '@/lib/api';
import type { AlpacaPortfolioResponse, AlpacaBrokerPosition, AlpacaBrokerAccountDetail } from '@/lib/types';
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react-native';

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
      const data: AlpacaPortfolioResponse = await alpacaBrokerApi.getPortfolio(user.id);
      if (data.success) {
        setAccount(data.account);
        setPositions(data.positions || []);
      }
    } catch {
      // Account may not exist
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchPortfolio(); }, [fetchPortfolio]);

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
    <SafeAreaView className="flex-1 bg-finch-bg" edges={['top']}>
      <ScrollView
        className="flex-1"
        contentContainerClassName="px-5 pb-8"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <Text className="text-2xl font-body-bold text-slate-900 mt-2 mb-4">Portfolio</Text>

        {loading ? (
          <View className="py-20 items-center">
            <ActivityIndicator size="large" color="#0f172a" />
          </View>
        ) : !account ? (
          <View className="items-center py-20">
            <DollarSign size={48} color="#cbd5e1" />
            <Text className="text-lg font-body-medium text-slate-400 mt-4">No account connected</Text>
            <Text className="text-sm font-body text-slate-400 mt-1 text-center">
              Set up your trading account to see your portfolio here
            </Text>
          </View>
        ) : (
          <>
            {/* Account Summary */}
            <View className="bg-white rounded-2xl p-5 mb-4 border border-black/5">
              <View className="flex-row justify-between mb-3">
                <View>
                  <Text className="text-sm font-body text-slate-500">Equity</Text>
                  <Text className="text-2xl font-body-bold text-slate-900">
                    ${equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </Text>
                </View>
                <View className="items-end">
                  <Text className="text-sm font-body text-slate-500">Unrealized P&L</Text>
                  <Text className={`text-lg font-body-bold ${totalUnrealizedPl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {totalUnrealizedPl >= 0 ? '+' : ''}${totalUnrealizedPl.toFixed(2)}
                  </Text>
                </View>
              </View>
              <View className="flex-row gap-4">
                <View>
                  <Text className="text-xs font-body text-slate-400">Cash</Text>
                  <Text className="text-sm font-body-medium text-slate-700">${cash.toFixed(2)}</Text>
                </View>
                <View>
                  <Text className="text-xs font-body text-slate-400">Buying Power</Text>
                  <Text className="text-sm font-body-medium text-slate-700">${buyingPower.toFixed(2)}</Text>
                </View>
              </View>
            </View>

            {/* Positions */}
            <Text className="text-lg font-body-bold text-slate-900 mb-3">
              Positions ({positions.length})
            </Text>

            {positions.length === 0 ? (
              <View className="bg-white rounded-2xl p-8 items-center border border-black/5">
                <Text className="text-slate-400 font-body">No open positions</Text>
              </View>
            ) : (
              <View className="bg-white rounded-2xl border border-black/5 overflow-hidden">
                {positions.map((pos, i) => {
                  const pl = parseFloat(pos.unrealized_pl || '0');
                  const plPct = parseFloat(pos.unrealized_plpc || '0') * 100;
                  const isPositive = pl >= 0;
                  const marketValue = parseFloat(pos.market_value || '0');

                  return (
                    <TouchableOpacity
                      key={pos.symbol}
                      onPress={() => router.push(`/stock/${pos.symbol}`)}
                      className={`p-4 ${i > 0 ? 'border-t border-black/5' : ''}`}
                      activeOpacity={0.7}
                    >
                      <View className="flex-row items-center justify-between">
                        <View>
                          <Text className="text-base font-body-bold text-slate-900">{pos.symbol}</Text>
                          <Text className="text-sm font-body text-slate-500">
                            {pos.qty} shares @ ${parseFloat(pos.avg_entry_price).toFixed(2)}
                          </Text>
                        </View>
                        <View className="items-end">
                          <Text className="text-base font-body-medium text-slate-900">
                            ${marketValue.toFixed(2)}
                          </Text>
                          <View className="flex-row items-center gap-1">
                            {isPositive ? (
                              <TrendingUp size={12} color="#059669" />
                            ) : (
                              <TrendingDown size={12} color="#dc2626" />
                            )}
                            <Text className={`text-sm font-body ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                              {isPositive ? '+' : ''}${pl.toFixed(2)} ({plPct.toFixed(1)}%)
                            </Text>
                          </View>
                        </View>
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </View>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
