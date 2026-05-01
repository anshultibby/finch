import { View, Text, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { useState, useEffect, useCallback } from 'react';
import { alpacaBrokerApi, chatApi } from '@/lib/api';
import { TrendingUp, TrendingDown, MessageSquare, Settings, DollarSign } from 'lucide-react-native';
import { TLH_PROMPT, PORTFOLIO_REVIEW_PROMPT } from '@/lib/aiPrompts';
import FinchLogo from '@/components/FinchLogo';

function formatPct(n: number) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

export default function HomeScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [portfolio, setPortfolio] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    if (!user) return;
    try {
      const portfolioData = await alpacaBrokerApi.getPortfolio(user.id).catch(() => null);
      if (portfolioData?.success) {
        setPortfolio({
          equity: portfolioData.account?.equity || '0',
          cash: portfolioData.account?.cash || '0',
          buyingPower: portfolioData.account?.buying_power || '0',
          positions: portfolioData.positions || [],
        });
      }
    } catch {} finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  }, [fetchData]);

  const startTlhChat = async () => {
    if (!user) return;
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}`);
      setTimeout(() => {
        // The chat view will handle sending via the welcome screen
      }, 100);
    } catch {}
  };

  const equity = parseFloat(portfolio?.equity || '0');

  return (
    <SafeAreaView className="flex-1 bg-finch-bg" edges={['top']}>
      <ScrollView
        className="flex-1"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#059669" />}
      >
        {/* Header */}
        <View className="flex-row items-center justify-between px-5 mt-2 mb-5">
          <View className="flex-row items-center gap-3">
            <FinchLogo size={32} />
            <View>
              <Text className="text-sm font-body text-slate-400">Welcome back</Text>
              <Text className="text-lg font-body-bold text-slate-900">
                {user?.user_metadata?.full_name?.split(' ')[0] || 'Trader'}
              </Text>
            </View>
          </View>
          <TouchableOpacity onPress={() => router.push('/settings')} className="p-2" activeOpacity={0.7}>
            <Settings size={22} color="#94a3b8" />
          </TouchableOpacity>
        </View>

        {/* Portfolio Card */}
        <View className="mx-5 bg-white rounded-2xl p-5 mb-4 border border-black/5">
          <Text className="text-sm font-body text-slate-400 mb-1">Portfolio Value</Text>
          {loading ? (
            <ActivityIndicator className="py-4" color="#059669" />
          ) : (
            <>
              <Text className="text-3xl font-body-bold text-slate-900 tracking-tight">
                ${equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </Text>
              {portfolio?.cash && (
                <Text className="text-sm font-body text-slate-400 mt-1">
                  ${parseFloat(portfolio.cash).toLocaleString('en-US', { minimumFractionDigits: 2 })} cash available
                </Text>
              )}
            </>
          )}
        </View>

        {/* Primary CTA — Tax-Loss Harvesting */}
        <TouchableOpacity
          onPress={() => router.push('/(tabs)/chat')}
          className="mx-5 mb-4 bg-emerald-600 rounded-2xl p-5 flex-row items-center gap-4"
          activeOpacity={0.8}
        >
          <View className="w-12 h-12 rounded-xl bg-white/20 items-center justify-center">
            <DollarSign size={24} color="#ffffff" />
          </View>
          <View className="flex-1">
            <Text className="text-base font-body-bold text-white">Find Tax Savings</Text>
            <Text className="text-sm font-body text-emerald-100 mt-0.5">
              Scan your portfolio for tax-loss harvesting opportunities
            </Text>
          </View>
        </TouchableOpacity>

        {/* Secondary Actions */}
        <View className="flex-row gap-3 mx-5 mb-6">
          <TouchableOpacity
            onPress={() => router.push('/(tabs)/chat')}
            className="flex-1 bg-white rounded-2xl p-4 flex-row items-center justify-center gap-2 border border-black/5"
            activeOpacity={0.8}
          >
            <MessageSquare size={18} color="#059669" />
            <Text className="text-slate-900 font-body-medium text-sm">New Chat</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => router.push('/orders')}
            className="flex-1 bg-white rounded-2xl p-4 flex-row items-center justify-center gap-2 border border-black/5"
            activeOpacity={0.8}
          >
            <TrendingUp size={18} color="#059669" />
            <Text className="text-slate-900 font-body-medium text-sm">Orders</Text>
          </TouchableOpacity>
        </View>

        {/* Positions */}
        {portfolio?.positions?.length > 0 && (
          <View className="px-5 mb-8">
            <Text className="text-xs font-body-bold text-slate-400 uppercase tracking-widest mb-3">
              Your Positions
            </Text>
            <View className="bg-white rounded-2xl border border-black/5 overflow-hidden">
              {portfolio.positions.map((pos: any, i: number) => {
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
                      <Text className="text-sm font-body text-slate-400">{pos.qty} shares</Text>
                    </View>
                    <View className="items-end">
                      <Text className="text-base font-body-medium text-slate-900 tabular-nums">
                        ${parseFloat(pos.current_price).toFixed(2)}
                      </Text>
                      <View className="flex-row items-center gap-1">
                        {isPositive ? (
                          <TrendingUp size={12} color="#059669" />
                        ) : (
                          <TrendingDown size={12} color="#dc2626" />
                        )}
                        <Text className={`text-sm font-body tabular-nums ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                          {formatPct(plPct)}
                        </Text>
                      </View>
                    </View>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
