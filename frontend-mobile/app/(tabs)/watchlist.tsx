import { View, Text, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useFocusEffect } from 'expo-router';
import { useState, useCallback } from 'react';
import { watchlistApi, marketApi } from '@/lib/api';
import { Star, Trash2 } from 'lucide-react-native';
import { COLORS, formatCurrency, formatPct } from '@/lib/constants';
import * as Haptics from 'expo-haptics';
import EmptyState from '@/components/ui/EmptyState';

interface WatchlistItem {
  symbol: string;
  price?: number;
  change_pct?: number;
  name?: string;
}

export default function WatchlistScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchWatchlist = useCallback(async () => {
    if (!user) return;
    try {
      const data = await watchlistApi.getWatchlist(user.id);
      const symbols: string[] = data.symbols || data.watchlist || [];

      if (symbols.length > 0) {
        try {
          const quotes = await marketApi.getBatchQuotes(symbols);
          const quoteMap = new Map(
            (quotes.quotes || quotes || []).map((q: any) => [q.symbol, q])
          );
          setItems(symbols.map(s => {
            const q = quoteMap.get(s) as any;
            return {
              symbol: s,
              price: q?.price,
              change_pct: q?.changesPercentage ?? q?.change_pct,
              name: q?.name,
            };
          }));
        } catch {
          setItems(symbols.map(s => ({ symbol: s })));
        }
      } else {
        setItems([]);
      }
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useFocusEffect(useCallback(() => {
    fetchWatchlist();
  }, [fetchWatchlist]));

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchWatchlist();
    setRefreshing(false);
  }, [fetchWatchlist]);

  const removeSymbol = (symbol: string) => {
    if (!user) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    Alert.alert('Remove', `Remove ${symbol} from watchlist?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove',
        style: 'destructive',
        onPress: async () => {
          try {
            await watchlistApi.removeSymbol(user.id, symbol);
            setItems(prev => prev.filter(i => i.symbol !== symbol));
          } catch {}
        },
      },
    ]);
  };

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <View className="px-5 pt-2 pb-3">
        <Text className="text-2xl font-body-bold text-gray-900">Watchlist</Text>
      </View>

      {loading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator size="large" color={COLORS.gray900} />
        </View>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Star size={48} color="#cbd5e1" />}
          title="No stocks watched"
          description="Search for stocks and add them to your watchlist"
          actionLabel="Search Stocks"
          onAction={() => router.push('/(tabs)/markets' as any)}
        />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.symbol}
          contentContainerClassName="px-5 pb-4"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() => router.push(`/stock/${item.symbol}`)}
              className="bg-white rounded-2xl p-4 mb-2.5 border border-gray-200 flex-row items-center justify-between"
              activeOpacity={0.7}
            >
              <View className="flex-1 mr-3">
                <Text className="text-[15px] font-body-bold text-gray-900">{item.symbol}</Text>
                {item.name && (
                  <Text className="text-sm font-body text-gray-500 mt-0.5" numberOfLines={1}>{item.name}</Text>
                )}
              </View>
              <View className="flex-row items-center gap-3">
                {item.price !== undefined && (
                  <View className="items-end">
                    <Text className="text-[15px] font-body-medium text-gray-900 tabular-nums">
                      {formatCurrency(item.price)}
                    </Text>
                    {item.change_pct !== undefined && (
                      <Text className={`text-sm font-body tabular-nums ${item.change_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {formatPct(item.change_pct)}
                      </Text>
                    )}
                  </View>
                )}
                <TouchableOpacity onPress={() => removeSymbol(item.symbol)} className="p-1.5" activeOpacity={0.7}>
                  <Trash2 size={16} color={COLORS.gray400} />
                </TouchableOpacity>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}
