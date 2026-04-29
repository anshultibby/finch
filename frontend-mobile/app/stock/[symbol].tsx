import { View, Text, ScrollView, ActivityIndicator, TouchableOpacity, RefreshControl } from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { useState, useEffect, useCallback } from 'react';
import { marketApi, chatApi } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { MessageSquare, TrendingUp, TrendingDown, Star } from 'lucide-react-native';
import { watchlistApi } from '@/lib/api';

interface StockQuote {
  symbol: string;
  name: string;
  price: number;
  changesPercentage: number;
  change: number;
  dayHigh: number;
  dayLow: number;
  volume: number;
  marketCap: number;
  pe: number;
  exchange: string;
}

interface NewsItem {
  title: string;
  text: string;
  publishedDate: string;
  site: string;
  url: string;
}

export default function StockDetailScreen() {
  const { symbol } = useLocalSearchParams<{ symbol: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [quote, setQuote] = useState<StockQuote | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [inWatchlist, setInWatchlist] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [quoteData, newsData] = await Promise.all([
        marketApi.getQuote(symbol),
        marketApi.getNews(symbol, 5).catch(() => ({ news: [] })),
      ]);
      setQuote(quoteData);
      setNews(newsData.news || newsData || []);

      if (user) {
        try {
          const wl = await watchlistApi.getWatchlist(user.id);
          const symbols = wl.symbols || wl.watchlist || [];
          setInWatchlist(symbols.includes(symbol));
        } catch {}
      }
    } catch (err) {
      console.error('Failed to fetch stock data:', err);
    } finally {
      setLoading(false);
    }
  }, [symbol, user]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  }, [fetchData]);

  const toggleWatchlist = async () => {
    if (!user) return;
    try {
      if (inWatchlist) {
        await watchlistApi.removeSymbol(user.id, symbol);
      } else {
        await watchlistApi.addSymbol(user.id, symbol);
      }
      setInWatchlist(!inWatchlist);
    } catch {}
  };

  const chatAboutStock = async () => {
    if (!user) return;
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}`);
    } catch {}
  };

  const isPositive = (quote?.changesPercentage || 0) >= 0;

  const formatVolume = (vol: number) => {
    if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`;
    if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `${(vol / 1e3).toFixed(1)}K`;
    return vol.toString();
  };

  return (
    <>
      <Stack.Screen options={{ headerTitle: symbol }} />
      <ScrollView
        className="flex-1 bg-finch-bg"
        contentContainerClassName="px-5 pb-8"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {loading ? (
          <View className="py-20 items-center">
            <ActivityIndicator size="large" color="#0f172a" />
          </View>
        ) : quote ? (
          <>
            {/* Price Header */}
            <View className="mt-4 mb-6">
              <Text className="text-sm font-body text-slate-500">{quote.name}</Text>
              <View className="flex-row items-baseline gap-3 mt-1">
                <Text className="text-4xl font-body-bold text-slate-900">
                  ${quote.price.toFixed(2)}
                </Text>
                <View className="flex-row items-center gap-1">
                  {isPositive ? (
                    <TrendingUp size={16} color="#059669" />
                  ) : (
                    <TrendingDown size={16} color="#dc2626" />
                  )}
                  <Text className={`text-lg font-body-medium ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                    {isPositive ? '+' : ''}{quote.changesPercentage.toFixed(2)}%
                  </Text>
                </View>
              </View>
              <Text className="text-sm font-body text-slate-400 mt-1">{quote.exchange}</Text>
            </View>

            {/* Action Buttons */}
            <View className="flex-row gap-3 mb-6">
              <TouchableOpacity
                onPress={chatAboutStock}
                className="flex-1 bg-slate-900 rounded-2xl py-3 flex-row items-center justify-center gap-2"
                activeOpacity={0.8}
              >
                <MessageSquare size={16} color="#ffffff" />
                <Text className="text-white font-body-medium text-sm">Chat about {symbol}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={toggleWatchlist}
                className={`rounded-2xl py-3 px-4 items-center justify-center border ${inWatchlist ? 'bg-amber-50 border-amber-200' : 'bg-white border-black/5'}`}
                activeOpacity={0.8}
              >
                <Star size={18} color={inWatchlist ? '#f59e0b' : '#94a3b8'} fill={inWatchlist ? '#f59e0b' : 'none'} />
              </TouchableOpacity>
            </View>

            {/* Key Stats */}
            <View className="bg-white rounded-2xl p-5 mb-4 border border-black/5">
              <Text className="text-base font-body-bold text-slate-900 mb-3">Key Stats</Text>
              <View className="flex-row flex-wrap gap-y-3">
                {[
                  { label: 'Day High', value: `$${quote.dayHigh?.toFixed(2) || '—'}` },
                  { label: 'Day Low', value: `$${quote.dayLow?.toFixed(2) || '—'}` },
                  { label: 'Volume', value: formatVolume(quote.volume || 0) },
                  { label: 'Market Cap', value: formatVolume(quote.marketCap || 0) },
                  { label: 'P/E Ratio', value: quote.pe ? quote.pe.toFixed(1) : '—' },
                ].map(stat => (
                  <View key={stat.label} className="w-1/2">
                    <Text className="text-xs font-body text-slate-400">{stat.label}</Text>
                    <Text className="text-sm font-body-medium text-slate-900">{stat.value}</Text>
                  </View>
                ))}
              </View>
            </View>

            {/* News */}
            {news.length > 0 && (
              <View>
                <Text className="text-lg font-body-bold text-slate-900 mb-3">News</Text>
                {news.map((item, i) => (
                  <View key={i} className="bg-white rounded-2xl p-4 mb-3 border border-black/5">
                    <Text className="text-sm font-body-medium text-slate-900" numberOfLines={2}>
                      {item.title}
                    </Text>
                    <Text className="text-xs font-body text-slate-400 mt-1">
                      {item.site} · {new Date(item.publishedDate).toLocaleDateString()}
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </>
        ) : (
          <View className="py-20 items-center">
            <Text className="text-slate-400 font-body">Failed to load stock data</Text>
          </View>
        )}
      </ScrollView>
    </>
  );
}
