import { View, Text, TextInput, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useState, useCallback, useRef } from 'react';
import { marketApi } from '@/lib/api';
import { Search as SearchIcon, TrendingUp } from 'lucide-react-native';

interface SearchResult {
  symbol: string;
  name: string;
  exchange?: string;
  price?: number;
  change_pct?: number;
}

export default function SearchScreen() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearch = useCallback((text: string) => {
    setQuery(text);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!text.trim()) {
      setResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await marketApi.searchStocks(text.trim());
        setResults(data.results || data || []);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }, []);

  return (
    <SafeAreaView className="flex-1 bg-finch-bg" edges={['top']}>
      <View className="px-5 pt-2 pb-3">
        <Text className="text-2xl font-body-bold text-slate-900 mb-4">Search</Text>
        <View className="flex-row items-center bg-white rounded-2xl px-4 border border-black/5">
          <SearchIcon size={18} color="#94a3b8" />
          <TextInput
            value={query}
            onChangeText={handleSearch}
            placeholder="Search stocks..."
            placeholderTextColor="#94a3b8"
            className="flex-1 py-3 ml-3 text-[15px] font-body text-slate-900"
            autoCapitalize="characters"
            autoCorrect={false}
          />
        </View>
      </View>

      {loading ? (
        <View className="py-8 items-center">
          <ActivityIndicator color="#0f172a" />
        </View>
      ) : (
        <FlatList
          data={results}
          keyExtractor={(item) => item.symbol}
          contentContainerClassName="px-5 pb-4"
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() => router.push(`/stock/${item.symbol}`)}
              className="bg-white rounded-2xl p-4 mb-3 border border-black/5 flex-row items-center justify-between"
              activeOpacity={0.7}
            >
              <View className="flex-1 mr-3">
                <Text className="text-base font-body-bold text-slate-900">{item.symbol}</Text>
                <Text className="text-sm font-body text-slate-500" numberOfLines={1}>{item.name}</Text>
              </View>
              {item.price && (
                <View className="items-end">
                  <Text className="text-base font-body-medium text-slate-900">${item.price.toFixed(2)}</Text>
                  {item.change_pct !== undefined && (
                    <Text className={`text-sm font-body ${item.change_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {item.change_pct >= 0 ? '+' : ''}{item.change_pct.toFixed(2)}%
                    </Text>
                  )}
                </View>
              )}
            </TouchableOpacity>
          )}
          ListEmptyComponent={
            !query.trim() ? (
              <View className="items-center py-20">
                <TrendingUp size={48} color="#cbd5e1" />
                <Text className="text-slate-400 font-body mt-4">Search for a stock symbol or company name</Text>
              </View>
            ) : null
          }
        />
      )}
    </SafeAreaView>
  );
}
