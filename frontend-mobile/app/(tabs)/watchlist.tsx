import { View, Text, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { useState, useEffect, useCallback } from 'react';
import { watchlistApi, marketApi } from '@/lib/api';
import { Star, Trash2 } from 'lucide-react-native';

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

  useEffect(() => { fetchWatchlist(); }, [fetchWatchlist]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchWatchlist();
    setRefreshing(false);
  }, [fetchWatchlist]);

  const removeSymbol = async (symbol: string) => {
    if (!user) return;
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
    <SafeAreaView className="flex-1 bg-finch-bg" edges={['top']}>
      <View className="px-5 pt-2 pb-3">
        <Text className="text-2xl font-body-bold text-slate-900">Watchlist</Text>
      </View>

      {loading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator size="large" color="#0f172a" />
        </View>
      ) : items.length === 0 ? (
        <View className="flex-1 items-center justify-center px-8">
          <Star size={48} color="#cbd5e1" />
          <Text className="text-lg font-body-medium text-slate-400 mt-4">No stocks watched</Text>
          <Text className="text-sm font-body text-slate-400 mt-1 text-center">
            Search for stocks and add them to your watchlist
          </Text>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.symbol}
          contentContainerClassName="px-5 pb-4"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() => router.push(`/stock/${item.symbol}`)}
              className="bg-white rounded-2xl p-4 mb-3 border border-black/5 flex-row items-center justify-between"
              activeOpacity={0.7}
            >
              <View className="flex-1 mr-3">
                <Text className="text-base font-body-bold text-slate-900">{item.symbol}</Text>
                {item.name && (
                  <Text className="text-sm font-body text-slate-500" numberOfLines={1}>{item.name}</Text>
                )}
              </View>
              <View className="flex-row items-center gap-3">
                {item.price !== undefined && (
                  <View className="items-end">
                    <Text className="text-base font-body-medium text-slate-900">${item.price.toFixed(2)}</Text>
                    {item.change_pct !== undefined && (
                      <Text className={`text-sm font-body ${item.change_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {item.change_pct >= 0 ? '+' : ''}{item.change_pct.toFixed(2)}%
                      </Text>
                    )}
                  </View>
                )}
                <TouchableOpacity onPress={() => removeSymbol(item.symbol)} className="p-1" activeOpacity={0.7}>
                  <Trash2 size={16} color="#94a3b8" />
                </TouchableOpacity>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}
