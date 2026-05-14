import { View, Text, TextInput, FlatList, TouchableOpacity, ActivityIndicator, ScrollView, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useState, useCallback, useRef, useEffect } from 'react';
import { marketApi } from '@/lib/api';
import { Search as SearchIcon, TrendingUp, Calendar } from 'lucide-react-native';
import { COLORS, formatCurrency, formatPct } from '@/lib/constants';
import SectionHeader from '@/components/ui/SectionHeader';
import MoverCard from '@/components/market/MoverCard';
import StockRow from '@/components/market/StockRow';
import SegmentedControl from '@/components/ui/SegmentedControl';

type TabType = 'discover' | 'search';

interface SearchResult {
  symbol: string;
  name: string;
  price?: number;
  changesPercentage?: number;
  change_pct?: number;
}

export default function MarketsScreen() {
  const router = useRouter();
  const [tab, setTab] = useState<TabType>('discover');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [movers, setMovers] = useState<any>(null);
  const [earnings, setEarnings] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(true);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchDiscover = useCallback(async () => {
    try {
      const [moversData, earningsData] = await Promise.all([
        marketApi.getMovers().catch(() => null),
        marketApi.getEarnings().catch(() => []),
      ]);
      if (moversData) setMovers(moversData);
      setEarnings(earningsData?.earnings || earningsData || []);
    } catch {} finally {
      setDiscoverLoading(false);
    }
  }, []);

  useEffect(() => { fetchDiscover(); }, [fetchDiscover]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchDiscover();
    setRefreshing(false);
  }, [fetchDiscover]);

  const handleSearch = useCallback((text: string) => {
    setQuery(text);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!text.trim()) { setResults([]); return; }
    setTab('search');
    debounceRef.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const data = await marketApi.searchStocks(text.trim());
        setResults(data.results || data || []);
      } catch {
        setResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }, []);

  const gainers = movers?.gainers?.slice(0, 8) || [];
  const losers = movers?.losers?.slice(0, 8) || [];
  const actives = movers?.most_active?.slice(0, 8) || [];

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <View className="px-5 pt-2 pb-3">
        <Text className="text-2xl font-body-bold text-gray-900 mb-3">Markets</Text>
        <View className="flex-row items-center bg-white rounded-2xl px-4 border border-gray-200">
          <SearchIcon size={18} color={COLORS.gray400} />
          <TextInput
            value={query}
            onChangeText={handleSearch}
            placeholder="Search stocks..."
            placeholderTextColor={COLORS.gray400}
            className="flex-1 py-3 ml-3 text-[15px] font-body text-gray-900"
            autoCapitalize="characters"
            autoCorrect={false}
            onFocus={() => setTab('search')}
          />
          {query.length > 0 && (
            <TouchableOpacity onPress={() => { setQuery(''); setResults([]); setTab('discover'); }}>
              <Text className="text-sm font-body-medium text-gray-400">Clear</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {tab === 'search' && query.trim() ? (
        searchLoading ? (
          <View className="py-8 items-center">
            <ActivityIndicator color={COLORS.gray900} />
          </View>
        ) : (
          <FlatList
            data={results}
            keyExtractor={(item) => item.symbol}
            contentContainerClassName="px-5 pb-4"
            renderItem={({ item }) => (
              <StockRow
                symbol={item.symbol}
                name={item.name}
                price={item.price}
                changePct={item.changesPercentage ?? item.change_pct}
                onPress={() => router.push(`/stock/${item.symbol}`)}
              />
            )}
            ListEmptyComponent={
              <View className="py-20 items-center">
                <Text className="text-gray-400 font-body">No results for "{query}"</Text>
              </View>
            }
            ItemSeparatorComponent={() => <View className="h-px bg-black/5" />}
          />
        )
      ) : (
        <ScrollView
          className="flex-1"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          showsVerticalScrollIndicator={false}
        >
          {discoverLoading ? (
            <View className="py-20 items-center">
              <ActivityIndicator size="large" color={COLORS.gray900} />
            </View>
          ) : (
            <>
              {/* Gainers */}
              {gainers.length > 0 && (
                <View className="mb-5">
                  <View className="px-5"><SectionHeader title="Top Gainers" /></View>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerClassName="px-5">
                    {gainers.map((m: any) => (
                      <MoverCard
                        key={m.symbol}
                        symbol={m.symbol}
                        name={m.name || m.companyName || ''}
                        price={m.price}
                        changePct={m.changesPercentage}
                        onPress={() => router.push(`/stock/${m.symbol}`)}
                      />
                    ))}
                  </ScrollView>
                </View>
              )}

              {/* Losers */}
              {losers.length > 0 && (
                <View className="mb-5">
                  <View className="px-5"><SectionHeader title="Top Losers" /></View>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerClassName="px-5">
                    {losers.map((m: any) => (
                      <MoverCard
                        key={m.symbol}
                        symbol={m.symbol}
                        name={m.name || m.companyName || ''}
                        price={m.price}
                        changePct={m.changesPercentage}
                        onPress={() => router.push(`/stock/${m.symbol}`)}
                      />
                    ))}
                  </ScrollView>
                </View>
              )}

              {/* Most Active */}
              {actives.length > 0 && (
                <View className="px-5 mb-5">
                  <SectionHeader title="Most Active" />
                  <View className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                    {actives.map((m: any, i: number) => (
                      <TouchableOpacity
                        key={m.symbol}
                        onPress={() => router.push(`/stock/${m.symbol}`)}
                        className={`flex-row items-center justify-between px-4 py-3 ${i > 0 ? 'border-t border-gray-200' : ''}`}
                        activeOpacity={0.6}
                      >
                        <View className="flex-1">
                          <Text className="text-[15px] font-body-bold text-gray-900">{m.symbol}</Text>
                          <Text className="text-sm font-body text-gray-500" numberOfLines={1}>{m.name || m.companyName}</Text>
                        </View>
                        <View className="items-end">
                          <Text className="text-[15px] font-body-medium text-gray-900 tabular-nums">{formatCurrency(m.price)}</Text>
                          <Text className={`text-sm font-body tabular-nums ${m.changesPercentage >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            {formatPct(m.changesPercentage)}
                          </Text>
                        </View>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}

              {/* Earnings Calendar */}
              {earnings.length > 0 && (
                <View className="px-5 mb-8">
                  <SectionHeader title="Upcoming Earnings" />
                  <View className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                    {earnings.slice(0, 10).map((e: any, i: number) => (
                      <TouchableOpacity
                        key={`${e.symbol}-${i}`}
                        onPress={() => router.push(`/stock/${e.symbol}`)}
                        className={`flex-row items-center justify-between px-4 py-3 ${i > 0 ? 'border-t border-gray-200' : ''}`}
                        activeOpacity={0.6}
                      >
                        <View className="flex-1">
                          <Text className="text-[15px] font-body-bold text-gray-900">{e.symbol}</Text>
                          <Text className="text-sm font-body text-gray-500" numberOfLines={1}>
                            {e.date || e.reportDate}
                          </Text>
                        </View>
                        <View className="flex-row items-center gap-1.5">
                          <Calendar size={14} color={COLORS.gray400} />
                          <Text className="text-xs font-body-medium text-gray-500 capitalize">
                            {e.time || e.when || 'TBD'}
                          </Text>
                        </View>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}
            </>
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}
