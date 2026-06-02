import { View, Text, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator, TextInput, FlatList, Alert, Platform, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useDrawer } from '@/contexts/DrawerContext';
import { useRouter, useFocusEffect } from 'expo-router';
import { useState, useCallback, useRef } from 'react';
import { snaptradeApi, marketApi, watchlistApi, notificationsApi } from '@/lib/api';
import { Search as SearchIcon, X, Calendar, Star, Trash2, DollarSign, Menu, SquarePen, Link, ExternalLink, Trash, ChevronRight, ChevronDown, Bell } from 'lucide-react-native';
import { formatCurrency, formatPct, COLORS, isIndianStock, currencySymbol } from '@/lib/constants';
import FinchLogo from '@/components/FinchLogo';
import SectionHeader from '@/components/ui/SectionHeader';
import MoverCard from '@/components/market/MoverCard';
import NewsCard from '@/components/market/NewsCard';
import EmptyState from '@/components/ui/EmptyState';
import MiniSparkline from '@/components/shared/MiniSparkline';
import { Skeleton, SkeletonMoverRow, SkeletonRows } from '@/components/ui/Skeleton';
import Animated, { FadeInDown } from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';
import * as WebBrowser from 'expo-web-browser';

type MarketRegion = 'us' | 'india';

const MARKET_INDICES: Record<MarketRegion, { symbol: string; label: string }[]> = {
  us: [
    { symbol: 'SPY', label: 'S&P 500' },
    { symbol: 'QQQ', label: 'NASDAQ' },
    { symbol: 'DIA', label: 'Dow Jones' },
    { symbol: 'VIXY', label: 'VIX' },
  ],
  india: [
    { symbol: '^NSEI', label: 'Nifty 50' },
    { symbol: '^BSESN', label: 'Sensex' },
    { symbol: '^NSEBANK', label: 'Bank Nifty' },
  ],
};

type HomeTab = 'markets' | 'earnings' | 'watchlist' | 'portfolio';

const NAV_TABS: { key: HomeTab; label: string }[] = [
  { key: 'markets', label: 'Markets' },
  { key: 'earnings', label: 'Earnings' },
  { key: 'watchlist', label: 'Watchlist' },
  { key: 'portfolio', label: 'Portfolio' },
];

export default function HomeScreen() {
  const { user } = useAuth();
  const { openDrawer } = useDrawer();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<HomeTab>('markets');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchActive, setSearchActive] = useState(false);
  const searchInputRef = useRef<TextInput>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);

  // Markets state
  const [marketRegion, setMarketRegion] = useState<MarketRegion>('us');
  const [indexQuotes, setIndexQuotes] = useState<Record<string, any>>({});
  const [movers, setMovers] = useState<any>(null);
  const [news, setNews] = useState<any[]>([]);
  const [marketsLoading, setMarketsLoading] = useState(true);
  const [marketsRefreshing, setMarketsRefreshing] = useState(false);

  // Earnings state
  const [earnings, setEarnings] = useState<any[]>([]);
  const [earningsLoading, setEarningsLoading] = useState(true);

  // Watchlist state
  const [watchlistItems, setWatchlistItems] = useState<any[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(true);

  // Portfolio state (SnapTrade)
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [portfolioAccounts, setPortfolioAccounts] = useState<any[]>([]);
  const [performance, setPerformance] = useState<any>(null);
  const [brokerages, setBrokerages] = useState<any[]>([]);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);

  const [refreshing, setRefreshing] = useState(false);

  const fetchMarkets = useCallback(async () => {
    try {
      const indices = MARKET_INDICES[marketRegion].map(i => i.symbol);
      const [moversData, newsData, batchQuotes] = await Promise.all([
        marketApi.getMovers().catch(() => null),
        marketApi.getGeneralNews(8, marketRegion).catch(() => []),
        marketApi.getBatchQuotes(indices).catch(() => ({})),
      ]);
      if (moversData) setMovers(moversData);
      setNews(newsData?.news || newsData || []);
      // batch-quotes returns an array; key it by symbol for O(1) lookup.
      if (Array.isArray(batchQuotes)) {
        const quoteMap: Record<string, any> = {};
        batchQuotes.forEach((q: any) => { if (q?.symbol) quoteMap[q.symbol] = q; });
        setIndexQuotes(quoteMap);
      }
    } catch {} finally {
      setMarketsLoading(false);
    }
  }, [marketRegion]);

  const fetchEarnings = useCallback(async () => {
    try {
      const data = await marketApi.getEarnings().catch(() => []);
      setEarnings(data?.earnings || data || []);
    } catch {} finally {
      setEarningsLoading(false);
    }
  }, []);

  const fetchWatchlist = useCallback(async () => {
    if (!user) return;
    try {
      const data = await watchlistApi.getWatchlist(user.id);
      const raw = data.symbols || data.watchlist || [];
      const items = raw.map((item: any) => {
        if (typeof item === 'string') {
          return { symbol: item };
        }
        return {
          symbol: item.symbol,
          price: item.price,
          change_pct: item.changesPercentage ?? item.change_pct,
          name: item.name,
        };
      });
      setWatchlistItems(items);
    } catch {
      setWatchlistItems([]);
    } finally {
      setWatchlistLoading(false);
    }
  }, [user]);

  const fetchPortfolio = useCallback(async () => {
    if (!user) return;
    try {
      const [status, brokerList] = await Promise.all([
        snaptradeApi.getStatus(user.id).catch(() => ({ is_connected: false })),
        snaptradeApi.getBrokerages().catch(() => ({ brokerages: [] })),
      ]);
      setBrokerages(brokerList.brokerages || []);
      setIsConnected(status.is_connected);

      if (status.is_connected) {
        const [portfolio, perf, accts] = await Promise.all([
          snaptradeApi.getPortfolio(user.id).catch(() => null),
          snaptradeApi.getPerformance(user.id).catch(() => null),
          snaptradeApi.getAccounts(user.id).catch(() => ({ accounts: [] })),
        ]);
        if (portfolio) setPortfolioData(portfolio);
        if (perf) setPerformance(perf);
        setPortfolioAccounts(accts.accounts || []);
      }
    } catch {} finally {
      setPortfolioLoading(false);
    }
  }, [user]);

  useFocusEffect(useCallback(() => {
    fetchMarkets();
    fetchEarnings();
    fetchWatchlist();
    fetchPortfolio();
    notificationsApi.getUnreadCount().then(d => setUnreadCount(d.unread_count || 0)).catch(() => {});
  }, [fetchMarkets, fetchEarnings, fetchWatchlist, fetchPortfolio]));

  const onRefresh = useCallback(async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setRefreshing(true);
    await Promise.all([fetchMarkets(), fetchEarnings(), fetchWatchlist(), fetchPortfolio()]);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    setRefreshing(false);
  }, [fetchMarkets, fetchEarnings, fetchWatchlist, fetchPortfolio]);

  const handleSearch = useCallback((text: string) => {
    setSearchQuery(text);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!text.trim()) { setSearchResults([]); return; }
    setSearchActive(true);
    debounceRef.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const data = await marketApi.searchStocks(text.trim(), 8);
        setSearchResults(data.results || data || []);
      } catch { setSearchResults([]); }
      finally { setSearchLoading(false); }
    }, 250);
  }, []);

  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setSearchActive(false);
  };

  const handleTabChange = (tab: HomeTab) => {
    Haptics.selectionAsync();
    setActiveTab(tab);
  };

  const newChat = useCallback(async () => {
    if (!user) return;
    try {
      const { chatApi } = await import('@/lib/api');
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}`);
    } catch {}
  }, [user, router]);

  const removeFromWatchlist = (symbol: string) => {
    if (!user) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    if (Platform.OS === 'web') {
      if (!window.confirm(`Remove ${symbol} from watchlist?`)) return;
      watchlistApi.removeSymbol(user.id, symbol).then(() => {
        setWatchlistItems(prev => prev.filter(i => i.symbol !== symbol));
      }).catch(() => {});
      return;
    }
    Alert.alert('Remove', `Remove ${symbol} from watchlist?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove', style: 'destructive',
        onPress: async () => {
          try {
            await watchlistApi.removeSymbol(user.id, symbol);
            setWatchlistItems(prev => prev.filter(i => i.symbol !== symbol));
          } catch {}
        },
      },
    ]);
  };

  const gainers = movers?.gainers?.slice(0, 8) || [];
  const losers = movers?.losers?.slice(0, 8) || [];
  const actives = movers?.most_active?.slice(0, 8) || [];

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      {/* Header */}
      {searchActive ? (
        <View style={headerStyles.searchBar}>
          <SearchIcon size={16} color={COLORS.gray400} />
          <TextInput
            ref={searchInputRef}
            testID="search-input"
            value={searchQuery}
            onChangeText={handleSearch}
            placeholder="Search stocks..."
            placeholderTextColor={COLORS.gray400}
            style={headerStyles.searchInput}
            autoCapitalize="characters"
            autoCorrect={false}
            autoFocus
          />
          <TouchableOpacity onPress={clearSearch} style={{ padding: 4 }}>
            <X size={18} color={COLORS.gray500} />
          </TouchableOpacity>
        </View>
      ) : (
        <View style={headerStyles.header}>
          <View style={headerStyles.headerLeft}>
            <TouchableOpacity onPress={openDrawer} style={headerStyles.iconBtn} activeOpacity={0.7}>
              <Menu size={22} color="#111827" />
            </TouchableOpacity>
            <FinchLogo size={22} showText />
          </View>
          <View style={headerStyles.headerRight}>
            <TouchableOpacity testID="search-button" onPress={() => setSearchActive(true)} style={headerStyles.iconBtn} activeOpacity={0.7}>
              <SearchIcon size={20} color="#6b7280" />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => router.push('/notifications')} style={headerStyles.iconBtn} activeOpacity={0.7}>
              <Bell size={20} color="#6b7280" />
              {unreadCount > 0 && (
                <View style={headerStyles.badge}>
                  <Text style={headerStyles.badgeText}>{unreadCount > 9 ? '9+' : unreadCount}</Text>
                </View>
              )}
            </TouchableOpacity>
            <TouchableOpacity onPress={newChat} style={headerStyles.iconBtn} activeOpacity={0.7}>
              <SquarePen size={20} color="#6b7280" />
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Search Results */}
      {searchActive && searchQuery.trim() ? (
        <View className="flex-1">
          {searchLoading ? (
            <View className="py-8 items-center">
              <ActivityIndicator color={COLORS.gray900} />
            </View>
          ) : (
            <FlatList
              data={searchResults}
              keyExtractor={(item) => item.symbol}
              contentContainerClassName="px-4 pb-4"
              keyboardShouldPersistTaps="handled"
              renderItem={({ item }) => (
                <TouchableOpacity
                  onPress={() => { clearSearch(); router.push(`/stock/${item.symbol}`); }}
                  className="flex-row items-center justify-between py-3 border-b border-gray-100"
                  activeOpacity={0.6}
                >
                  <View className="flex-1 mr-3">
                    <Text className="text-[15px] font-body-bold text-gray-900">{item.symbol}</Text>
                    <Text className="text-sm font-body text-gray-500 mt-0.5" numberOfLines={1}>{item.name}</Text>
                  </View>
                  {item.price != null && (
                    <View className="items-end">
                      <Text className="text-[15px] font-body-medium text-gray-900 tabular-nums">{formatCurrency(item.price, false, item.symbol)}</Text>
                      <Text className={`text-sm font-body tabular-nums ${(item.changesPercentage ?? item.change_pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                        {formatPct(item.changesPercentage ?? item.change_pct ?? 0)}
                      </Text>
                    </View>
                  )}
                </TouchableOpacity>
              )}
              ListEmptyComponent={
                <View className="py-20 items-center">
                  <Text className="text-gray-400 font-body">No results for "{searchQuery}"</Text>
                </View>
              }
            />
          )}
        </View>
      ) : searchActive ? (
        <TouchableOpacity style={{ flex: 1 }} onPress={clearSearch} activeOpacity={1} />
      ) : (
        <>
          {/* Top Nav Tabs */}
          <View className="border-b border-gray-100 px-4">
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerClassName="gap-5">
              {NAV_TABS.map(tab => (
                <TouchableOpacity
                  key={tab.key}
                  onPress={() => handleTabChange(tab.key)}
                  className="pb-2.5 pt-1"
                  activeOpacity={0.7}
                >
                  <Text className={`text-sm font-body-medium ${
                    activeTab === tab.key ? 'text-gray-900' : 'text-gray-400'
                  }`}>
                    {tab.label}
                  </Text>
                  {activeTab === tab.key && (
                    <View className="absolute bottom-0 left-0 right-0 h-[2px] bg-gray-900 rounded-full" />
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>

          {/* Tab Content */}
          {activeTab === 'markets' && (
            <MarketsTab
              gainers={gainers} losers={losers} actives={actives} news={news}
              loading={marketsLoading} refreshing={refreshing} onRefresh={onRefresh}
              onStockPress={(s) => router.push(`/stock/${s}`)}
              marketRegion={marketRegion}
              onRegionChange={(r) => { setMarketRegion(r); setMarketsLoading(true); }}
              indexQuotes={indexQuotes}
            />
          )}
          {activeTab === 'earnings' && (
            <EarningsTab
              earnings={earnings} loading={earningsLoading}
              refreshing={refreshing} onRefresh={onRefresh}
              onStockPress={(s) => router.push(`/stock/${s}`)}
            />
          )}
          {activeTab === 'watchlist' && (
            <WatchlistTab
              items={watchlistItems} loading={watchlistLoading}
              refreshing={refreshing} onRefresh={onRefresh}
              onStockPress={(s) => router.push(`/stock/${s}`)}
              onRemove={removeFromWatchlist}
            />
          )}
          {activeTab === 'portfolio' && (
            <PortfolioTab
              isConnected={isConnected}
              portfolioData={portfolioData}
              accounts={portfolioAccounts}
              performance={performance}
              brokerages={brokerages}
              loading={portfolioLoading}
              refreshing={refreshing}
              onRefresh={onRefresh}
              onStockPress={(s) => router.push(`/stock/${s}`)}
              userId={user?.id || ''}
              onConnectionChange={fetchPortfolio}
            />
          )}
        </>
      )}
    </SafeAreaView>
  );
}

// ── Markets Tab ──────────────────────────────────────────────────────────────

function MarketsTab({ gainers, losers, actives, news, loading, refreshing, onRefresh, onStockPress, marketRegion, onRegionChange, indexQuotes }: {
  gainers: any[]; losers: any[]; actives: any[]; news: any[];
  loading: boolean; refreshing: boolean; onRefresh: () => void;
  onStockPress: (symbol: string) => void;
  marketRegion: MarketRegion;
  onRegionChange: (r: MarketRegion) => void;
  indexQuotes: Record<string, any>;
}) {
  const [showRegionPicker, setShowRegionPicker] = useState(false);

  if (loading) {
    return (
      <View className="flex-1 pt-5">
        <View className="flex-row gap-2.5 px-4 mb-6">
          {[0, 1, 2].map((i) => <Skeleton key={i} width={150} height={72} radius={14} />)}
        </View>
        <View className="px-4 mb-3"><Skeleton width={110} height={14} radius={4} /></View>
        <SkeletonMoverRow />
        <View className="px-4 mt-6 mb-3"><Skeleton width={90} height={14} radius={4} /></View>
        <SkeletonRows count={4} />
      </View>
    );
  }

  const indices = MARKET_INDICES[marketRegion];

  return (
    <ScrollView
      className="flex-1"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
      showsVerticalScrollIndicator={false}
    >
      {/* Market Region Toggle */}
      <View className="px-4 mt-3 mb-3 flex-row items-center justify-between">
        <TouchableOpacity
          onPress={() => setShowRegionPicker(!showRegionPicker)}
          style={idxStyles.regionBtn}
          activeOpacity={0.7}
        >
          <Text style={idxStyles.regionFlag}>{marketRegion === 'us' ? '🇺🇸' : '🇮🇳'}</Text>
          <Text style={idxStyles.regionLabel}>{marketRegion === 'us' ? 'US Markets' : 'India Markets'}</Text>
          <ChevronDown size={14} color="#9ca3af" />
        </TouchableOpacity>
      </View>

      {showRegionPicker && (
        <View className="px-4 mb-3">
          <View style={idxStyles.regionDropdown}>
            {(['us', 'india'] as const).map(r => (
              <TouchableOpacity
                key={r}
                onPress={() => { onRegionChange(r); setShowRegionPicker(false); }}
                style={[idxStyles.regionOption, marketRegion === r && idxStyles.regionOptionActive]}
                activeOpacity={0.7}
              >
                <Text style={idxStyles.regionFlag}>{r === 'us' ? '🇺🇸' : '🇮🇳'}</Text>
                <Text style={[idxStyles.regionOptionText, marketRegion === r && { color: '#059669' }]}>
                  {r === 'us' ? 'US Markets' : 'India Markets'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* Index Cards */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 16, gap: 10 }} className="mb-5">
        {indices.map(idx => {
          const q = indexQuotes[idx.symbol] || {};
          return (
            <TouchableOpacity key={idx.symbol} onPress={() => onStockPress(idx.symbol)} style={idxStyles.card} activeOpacity={0.7}>
              <Text style={idxStyles.cardLabel}>{idx.label}</Text>
              <View className="flex-row items-end justify-between mt-1">
                <View>
                  <Text style={idxStyles.cardPrice}>{q.price ? formatCurrency(q.price, false, idx.symbol) : '—'}</Text>
                  {q.changesPercentage != null && (
                    <Text style={[idxStyles.cardChange, { color: q.changesPercentage >= 0 ? '#059669' : '#ef4444' }]}>
                      {q.changesPercentage >= 0 ? '↗' : '↘'} {formatPct(q.changesPercentage)}
                    </Text>
                  )}
                </View>
                <MiniSparkline symbol={idx.symbol} width={50} height={22} days={7} />
              </View>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {gainers.length > 0 && (
        <View className="mt-4 mb-5">
          <View className="px-4"><SectionHeader title="Top Gainers" /></View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerClassName="px-4">
            {gainers.map((m: any, i: number) => (
              <Animated.View key={m.symbol} entering={FadeInDown.delay(i * 45).springify().damping(14)}>
                <MoverCard symbol={m.symbol} name={m.name || m.companyName || ''} price={m.price} changePct={m.changesPercentage} onPress={() => onStockPress(m.symbol)} />
              </Animated.View>
            ))}
          </ScrollView>
        </View>
      )}

      {losers.length > 0 && (
        <View className="mb-5">
          <View className="px-4"><SectionHeader title="Top Losers" /></View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerClassName="px-4">
            {losers.map((m: any, i: number) => (
              <Animated.View key={m.symbol} entering={FadeInDown.delay(i * 45).springify().damping(14)}>
                <MoverCard symbol={m.symbol} name={m.name || m.companyName || ''} price={m.price} changePct={m.changesPercentage} onPress={() => onStockPress(m.symbol)} />
              </Animated.View>
            ))}
          </ScrollView>
        </View>
      )}

      {actives.length > 0 && (
        <View className="px-4 mb-5">
          <SectionHeader title="Most Active" />
          <View className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {actives.map((m: any, i: number) => (
              <TouchableOpacity
                key={m.symbol}
                onPress={() => onStockPress(m.symbol)}
                className={`flex-row items-center justify-between px-4 py-3 ${i > 0 ? 'border-t border-gray-100' : ''}`}
                activeOpacity={0.6}
              >
                <View className="flex-1">
                  <Text className="text-[15px] font-body-bold text-gray-900">{m.symbol}</Text>
                  <Text className="text-sm font-body text-gray-500" numberOfLines={1}>{m.name || m.companyName}</Text>
                </View>
                <View className="items-end">
                  <Text className="text-[15px] font-body-medium text-gray-900 tabular-nums">{formatCurrency(m.price, false, m.symbol)}</Text>
                  <Text className={`text-sm font-body tabular-nums ${m.changesPercentage >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {formatPct(m.changesPercentage)}
                  </Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {news.length > 0 && (
        <View className="px-4 mb-8">
          <SectionHeader title="Market News" />
          <View className="gap-2.5">
            {news.slice(0, 6).map((item: any, i: number) => (
              <NewsCard key={i} title={item.title} source={item.site || item.source || ''} date={item.publishedDate || item.date || ''} url={item.url} />
            ))}
          </View>
        </View>
      )}
    </ScrollView>
  );
}

// ── Earnings Tab ─────────────────────────────────────────────────────────────

function EarningsTab({ earnings, loading, refreshing, onRefresh, onStockPress }: {
  earnings: any[]; loading: boolean; refreshing: boolean; onRefresh: () => void;
  onStockPress: (symbol: string) => void;
}) {
  if (loading) {
    return <View className="flex-1 pt-4"><SkeletonRows count={7} /></View>;
  }

  return (
    <ScrollView
      className="flex-1"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
      showsVerticalScrollIndicator={false}
      contentContainerClassName="px-4 pt-4 pb-8"
    >
      {earnings.length === 0 ? (
        <EmptyState
          icon={<Calendar size={48} color={COLORS.gray200} />}
          title="No upcoming earnings"
          description="Check back later for upcoming earnings reports"
        />
      ) : (
        <View className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {earnings.slice(0, 20).map((e: any, i: number) => (
            <TouchableOpacity
              key={`${e.symbol}-${i}`}
              onPress={() => onStockPress(e.symbol)}
              className={`flex-row items-center justify-between px-4 py-3.5 ${i > 0 ? 'border-t border-gray-100' : ''}`}
              activeOpacity={0.6}
            >
              <View className="flex-1">
                <Text className="text-[15px] font-body-bold text-gray-900">{e.symbol}</Text>
                <Text className="text-sm font-body text-gray-500 mt-0.5" numberOfLines={1}>
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
      )}
    </ScrollView>
  );
}

// ── Watchlist Tab ─────────────────────────────────────────────────────────────

function WatchlistTab({ items, loading, refreshing, onRefresh, onStockPress, onRemove }: {
  items: any[]; loading: boolean; refreshing: boolean; onRefresh: () => void;
  onStockPress: (symbol: string) => void; onRemove: (symbol: string) => void;
}) {
  if (loading) {
    return <View className="flex-1 pt-4"><SkeletonRows count={7} /></View>;
  }

  if (items.length === 0) {
    return (
      <ScrollView
        className="flex-1"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
      >
        <EmptyState
          icon={<Star size={48} color={COLORS.gray200} />}
          title="No stocks watched"
          description="Search for stocks and add them to your watchlist"
        />
      </ScrollView>
    );
  }

  return (
    <FlatList
      data={items}
      keyExtractor={(item) => item.symbol}
      contentContainerClassName="px-4 pt-4 pb-4"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
      renderItem={({ item, index }) => (
        <TouchableOpacity
          onPress={() => onStockPress(item.symbol)}
          className={`flex-row items-center justify-between py-3.5 ${index > 0 ? 'border-t border-gray-100' : ''}`}
          activeOpacity={0.6}
        >
          <View className="flex-1 mr-3">
            <Text className="text-[15px] font-body-bold text-gray-900">{item.symbol}</Text>
            {item.name && <Text className="text-sm font-body text-gray-500 mt-0.5" numberOfLines={1}>{item.name}</Text>}
          </View>
          <View className="flex-row items-center gap-2">
            <MiniSparkline symbol={item.symbol} width={48} height={20} days={30} />
            {item.price != null && (
              <View className="items-end">
                <Text className="text-[15px] font-body-medium text-gray-900 tabular-nums">{formatCurrency(item.price, false, item.symbol)}</Text>
                {item.change_pct != null && (
                  <Text className={`text-sm font-body tabular-nums ${item.change_pct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {formatPct(item.change_pct)}
                  </Text>
                )}
              </View>
            )}
            <TouchableOpacity onPress={() => onRemove(item.symbol)} className="p-1.5" activeOpacity={0.7}>
              <Trash2 size={16} color={COLORS.gray400} />
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      )}
    />
  );
}

// ── Portfolio Tab (SnapTrade) ─────────────────────────────────────────────────

function PortfolioTab({ isConnected, portfolioData, accounts, performance, brokerages, loading, refreshing, onRefresh, onStockPress, userId, onConnectionChange }: {
  isConnected: boolean;
  portfolioData: any;
  accounts: any[];
  performance: any;
  brokerages: any[];
  loading: boolean;
  refreshing: boolean;
  onRefresh: () => void;
  onStockPress: (symbol: string) => void;
  userId: string;
  onConnectionChange: () => void;
}) {
  const [connecting, setConnecting] = useState(false);
  const [showBrokers, setShowBrokers] = useState(false);
  const [brokerSearch, setBrokerSearch] = useState('');

  if (loading) {
    return <View className="flex-1 pt-4"><SkeletonRows count={7} /></View>;
  }

  const handleConnect = async (brokerId?: string) => {
    setConnecting(true);
    try {
      const redirectUri = Platform.OS === 'web'
        ? `${window.location.origin}/snaptrade/callback`
        : 'finch://snaptrade-callback';
      const response = brokerId
        ? await snaptradeApi.connectBroker(userId, redirectUri, brokerId)
        : await snaptradeApi.connect(userId, redirectUri);
      if (response.success && response.redirect_uri) {
        if (Platform.OS === 'web') {
          window.open(response.redirect_uri, '_blank', 'width=500,height=700');
        } else {
          await WebBrowser.openBrowserAsync(response.redirect_uri);
        }
        await snaptradeApi.callback(userId);
        onConnectionChange();
      }
    } catch {} finally {
      setConnecting(false);
      setShowBrokers(false);
    }
  };

  const handleDisconnectAccount = (accountId: string, name: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    if (Platform.OS === 'web') {
      if (!window.confirm(`Disconnect ${name}?`)) return;
      snaptradeApi.deleteAccount(userId, accountId).then(onConnectionChange).catch(() => {});
      return;
    }
    Alert.alert('Disconnect', `Disconnect ${name}?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Disconnect', style: 'destructive', onPress: () => snaptradeApi.deleteAccount(userId, accountId).then(onConnectionChange).catch(() => {}) },
    ]);
  };

  const filteredBrokers = brokerages.filter(b =>
    b.name.toLowerCase().includes(brokerSearch.toLowerCase())
  );

  // Not connected — show connect CTA
  if (!isConnected) {
    return (
      <ScrollView
        className="flex-1"
        contentContainerClassName="px-4 pt-8 pb-8"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
      >
        {showBrokers ? (
          <View>
            <View className="flex-row items-center justify-between mb-4">
              <Text style={pStyles.sectionTitle}>Select a brokerage</Text>
              <TouchableOpacity onPress={() => setShowBrokers(false)}>
                <X size={20} color={COLORS.gray500} />
              </TouchableOpacity>
            </View>
            <View style={pStyles.searchBox}>
              <SearchIcon size={15} color={COLORS.gray400} />
              <TextInput
                value={brokerSearch}
                onChangeText={setBrokerSearch}
                placeholder="Search brokerages..."
                placeholderTextColor={COLORS.gray400}
                style={pStyles.searchInput}
                autoFocus
              />
            </View>
            <View style={pStyles.brokerList}>
              {filteredBrokers.map((b: any) => (
                <TouchableOpacity
                  key={b.id}
                  style={pStyles.brokerRow}
                  onPress={() => handleConnect(b.id)}
                  disabled={connecting}
                  activeOpacity={0.6}
                >
                  <View style={pStyles.brokerIcon}>
                    <Text style={{ fontSize: 14, fontFamily: 'DMSans-Bold', color: '#6b7280' }}>{b.name[0]}</Text>
                  </View>
                  <Text style={pStyles.brokerName} numberOfLines={1}>{b.name}</Text>
                  <ChevronRight size={16} color="#d1d5db" />
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ) : (
          <View className="items-center pt-8">
            <View style={pStyles.emptyIcon}>
              <Link size={28} color="#059669" />
            </View>
            <Text style={pStyles.emptyTitle}>Connect your brokerage</Text>
            <Text style={pStyles.emptyDesc}>
              Link your accounts to track your portfolio, holdings, and performance — all in one place.
            </Text>
            <TouchableOpacity
              onPress={() => setShowBrokers(true)}
              style={pStyles.connectBtn}
              activeOpacity={0.85}
              disabled={connecting}
            >
              {connecting ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={pStyles.connectBtnText}>Connect Account</Text>
              )}
            </TouchableOpacity>
            <Text style={pStyles.supportedBrokers}>Robinhood, Schwab, Fidelity, E*TRADE, and more</Text>
          </View>
        )}
      </ScrollView>
    );
  }

  // Connected — show portfolio
  const totalValue = portfolioData?.total_value || 0;
  const totalPositions = portfolioData?.total_positions || 0;
  const totalGainLoss = performance?.total_gain_loss || 0;
  const totalGainLossPct = performance?.total_gain_loss_percent || 0;
  const allPositions: any[] = [];
  (portfolioData?.accounts || []).forEach((acct: any) => {
    (acct.positions || []).forEach((pos: any) => {
      allPositions.push({ ...pos, account: acct.institution });
    });
  });
  allPositions.sort((a, b) => (b.value || 0) - (a.value || 0));

  return (
    <ScrollView
      className="flex-1"
      contentContainerClassName="px-4 pt-4 pb-8"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
      showsVerticalScrollIndicator={false}
    >
      {/* Summary Stats */}
      <View style={pStyles.statsGrid}>
        <View style={pStyles.statCard}>
          <Text style={pStyles.statLabel}>TOTAL VALUE</Text>
          <Text style={pStyles.statValue}>{formatCurrency(totalValue)}</Text>
          <Text style={pStyles.statSub}>{totalPositions} positions</Text>
        </View>
        <View style={pStyles.statCard}>
          <Text style={pStyles.statLabel}>TOTAL RETURN</Text>
          <Text style={[pStyles.statValue, { color: totalGainLoss >= 0 ? '#059669' : '#ef4444' }]}>
            {totalGainLoss >= 0 ? '+' : ''}{formatCurrency(totalGainLoss)}
          </Text>
          <Text style={[pStyles.statSub, { color: totalGainLoss >= 0 ? '#059669' : '#ef4444' }]}>
            {totalGainLossPct >= 0 ? '+' : ''}{totalGainLossPct.toFixed(2)}%
          </Text>
        </View>
      </View>

      {/* Accounts */}
      <View className="flex-row items-center justify-between mt-5 mb-3">
        <Text style={pStyles.sectionTitle}>Accounts</Text>
        <TouchableOpacity onPress={() => setShowBrokers(true)} style={pStyles.addBtn} activeOpacity={0.7}>
          <ExternalLink size={13} color="#059669" />
          <Text style={pStyles.addBtnText}>Add</Text>
        </TouchableOpacity>
      </View>

      {accounts.map((acct: any) => (
        <View key={acct.id} style={pStyles.accountCard}>
          <View className="flex-row items-center justify-between mb-2">
            <View className="flex-1 mr-3">
              <Text style={pStyles.accountName} numberOfLines={1}>{acct.name || acct.institution}</Text>
              <Text style={pStyles.accountInst}>{acct.institution} · {acct.type || 'Account'}</Text>
            </View>
            <TouchableOpacity onPress={() => handleDisconnectAccount(acct.id, acct.name || acct.institution)} style={{ padding: 4 }}>
              <Trash size={14} color="#d1d5db" />
            </TouchableOpacity>
          </View>
          <Text style={pStyles.accountBalance}>{formatCurrency(acct.balance || 0)}</Text>
        </View>
      ))}

      {/* Holdings */}
      {allPositions.length > 0 && (
        <>
          <Text style={[pStyles.sectionTitle, { marginTop: 20, marginBottom: 10 }]}>Holdings</Text>
          <View style={pStyles.holdingsCard}>
            {allPositions.map((pos: any, i: number) => (
              <TouchableOpacity
                key={`${pos.symbol}-${i}`}
                onPress={() => onStockPress(pos.symbol)}
                style={[pStyles.holdingRow, i > 0 && { borderTopWidth: 1, borderTopColor: '#f3f4f6' }]}
                activeOpacity={0.6}
              >
                <View className="flex-1">
                  <Text style={pStyles.holdingSymbol}>{pos.symbol}</Text>
                  <Text style={pStyles.holdingQty}>{pos.quantity?.toFixed(2)} shares</Text>
                </View>
                <View className="items-end">
                  <Text style={pStyles.holdingValue}>{formatCurrency(pos.value || 0, false, pos.symbol)}</Text>
                  {pos.gain_loss != null && (
                    <Text style={[pStyles.holdingGain, { color: pos.gain_loss >= 0 ? '#059669' : '#ef4444' }]}>
                      {pos.gain_loss >= 0 ? '+' : ''}{formatCurrency(pos.gain_loss, false, pos.symbol)} ({pos.gain_loss_percent?.toFixed(1) || '0.0'}%)
                    </Text>
                  )}
                </View>
              </TouchableOpacity>
            ))}
          </View>
        </>
      )}

      {portfolioData?.syncing && (
        <View className="flex-row items-center justify-center gap-2 mt-4">
          <ActivityIndicator size="small" color={COLORS.gray400} />
          <Text style={pStyles.syncText}>Syncing portfolio data...</Text>
        </View>
      )}

      {showBrokers && (
        <View style={pStyles.brokerOverlay}>
          <View className="flex-row items-center justify-between mb-4">
            <Text style={pStyles.sectionTitle}>Add another account</Text>
            <TouchableOpacity onPress={() => setShowBrokers(false)}>
              <X size={20} color={COLORS.gray500} />
            </TouchableOpacity>
          </View>
          <View style={pStyles.searchBox}>
            <SearchIcon size={15} color={COLORS.gray400} />
            <TextInput
              value={brokerSearch}
              onChangeText={setBrokerSearch}
              placeholder="Search brokerages..."
              placeholderTextColor={COLORS.gray400}
              style={pStyles.searchInput}
              autoFocus
            />
          </View>
          <View style={pStyles.brokerList}>
            {filteredBrokers.map((b: any) => (
              <TouchableOpacity
                key={b.id}
                style={pStyles.brokerRow}
                onPress={() => handleConnect(b.id)}
                disabled={connecting}
                activeOpacity={0.6}
              >
                <View style={pStyles.brokerIcon}>
                  <Text style={{ fontSize: 14, fontFamily: 'DMSans-Bold', color: '#6b7280' }}>{b.name[0]}</Text>
                </View>
                <Text style={pStyles.brokerName} numberOfLines={1}>{b.name}</Text>
                <ChevronRight size={16} color="#d1d5db" />
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}
    </ScrollView>
  );
}

const pStyles = StyleSheet.create({
  statsGrid: {
    flexDirection: 'row',
    gap: 10,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  statLabel: {
    fontSize: 10,
    fontFamily: 'DMSans-Bold',
    color: '#9ca3af',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  statValue: {
    fontSize: 20,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
  },
  statSub: {
    fontSize: 12,
    fontFamily: 'DMSans',
    color: '#9ca3af',
    marginTop: 2,
  },
  sectionTitle: {
    fontSize: 14,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
  },
  addBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d1fae5',
    backgroundColor: '#ecfdf5',
  },
  addBtnText: {
    fontSize: 12,
    fontFamily: 'DMSans-Medium',
    color: '#059669',
  },
  accountCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    marginBottom: 8,
  },
  accountName: {
    fontSize: 14,
    fontFamily: 'DMSans-Medium',
    color: '#111827',
  },
  accountInst: {
    fontSize: 12,
    fontFamily: 'DMSans',
    color: '#9ca3af',
    marginTop: 2,
  },
  accountBalance: {
    fontSize: 18,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
    marginTop: 4,
  },
  holdingsCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    overflow: 'hidden',
  },
  holdingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  holdingSymbol: {
    fontSize: 14,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
  },
  holdingQty: {
    fontSize: 12,
    fontFamily: 'DMSans',
    color: '#9ca3af',
    marginTop: 2,
  },
  holdingValue: {
    fontSize: 14,
    fontFamily: 'DMSans-Medium',
    color: '#111827',
  },
  holdingGain: {
    fontSize: 11,
    fontFamily: 'DMSans',
    marginTop: 2,
  },
  syncText: {
    fontSize: 13,
    fontFamily: 'DMSans',
    color: '#9ca3af',
  },
  emptyIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#ecfdf5',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  emptyTitle: {
    fontSize: 20,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
    marginBottom: 8,
  },
  emptyDesc: {
    fontSize: 14,
    fontFamily: 'DMSans',
    color: '#9ca3af',
    textAlign: 'center',
    lineHeight: 20,
    paddingHorizontal: 16,
    marginBottom: 24,
  },
  connectBtn: {
    backgroundColor: '#059669',
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 12,
    marginBottom: 12,
  },
  connectBtnText: {
    fontSize: 15,
    fontFamily: 'DMSans-Medium',
    color: '#fff',
  },
  supportedBrokers: {
    fontSize: 12,
    fontFamily: 'DMSans',
    color: '#d1d5db',
  },
  brokerOverlay: {
    marginTop: 20,
    backgroundColor: '#f9fafb',
    borderRadius: 14,
    padding: 16,
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    paddingHorizontal: 12,
    height: 40,
    gap: 8,
    marginBottom: 12,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'DMSans',
    color: '#111827',
    paddingVertical: 0,
  },
  brokerList: {
    borderRadius: 12,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#f3f4f6',
    overflow: 'hidden',
  },
  brokerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f9fafb',
  },
  brokerIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: '#f3f4f6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  brokerName: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'DMSans-Medium',
    color: '#111827',
  },
});

const idxStyles = StyleSheet.create({
  regionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 10,
    backgroundColor: '#f9fafb',
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  regionFlag: { fontSize: 14 },
  regionLabel: { fontSize: 13, fontFamily: 'DMSans-Medium', color: '#374151' },
  regionDropdown: {
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  regionOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f9fafb',
  },
  regionOptionActive: { backgroundColor: '#ecfdf5' },
  regionOptionText: { fontSize: 14, fontFamily: 'DMSans-Medium', color: '#374151' },
  card: {
    width: 150,
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  cardLabel: { fontSize: 11, fontFamily: 'DMSans-Bold', color: '#9ca3af', letterSpacing: 0.3 },
  cardPrice: { fontSize: 16, fontFamily: 'DMSans-Bold', color: '#111827' },
  cardChange: { fontSize: 11, fontFamily: 'DMSans-Medium', marginTop: 2 },
});

const headerStyles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    height: 48,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  iconBtn: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 18,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    height: 42,
    backgroundColor: '#f3f4f6',
    borderRadius: 12,
    paddingHorizontal: 12,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    fontFamily: 'DMSans',
    color: '#111827',
    paddingVertical: 0,
  },
  badge: {
    position: 'absolute',
    top: 4,
    right: 4,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: '#dc2626',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  badgeText: {
    fontSize: 9,
    fontFamily: 'DMSans-Bold',
    color: '#fff',
  },
});
