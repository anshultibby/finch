import { View, Text, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator, TextInput, FlatList, Alert, Platform, StyleSheet, KeyboardAvoidingView, useWindowDimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useDrawer } from '@/contexts/DrawerContext';
import { useRouter, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useState, useCallback, useRef, useEffect } from 'react';
import { snaptradeApi, marketApi, watchlistApi, notificationsApi } from '@/lib/api';
import { isCacheFresh, touchCache } from '@/hooks/useCachedResource';
import { syncBadgeCount } from '@/lib/pushNotifications';
import type { SnapTradeStatusResponse } from '@/lib/types';
import { AlertTriangle } from 'lucide-react-native';
import { Search as SearchIcon, X, Calendar, Star, Trash2, DollarSign, Menu, SquarePen, Link, ExternalLink, Trash, ChevronRight, ChevronDown, Bell, Lock } from 'lucide-react-native';
import { formatCurrency, formatPct, formatRelativeTime, COLORS, isIndianStock, currencySymbol } from '@/lib/constants';
import FinchLogo from '@/components/FinchLogo';
import SectionHeader from '@/components/ui/SectionHeader';
import MoverCard from '@/components/market/MoverCard';
import NewsCard from '@/components/market/NewsCard';
import EmptyState from '@/components/ui/EmptyState';
import MiniSparkline from '@/components/shared/MiniSparkline';
import RobinhoodAgentCard from '@/components/RobinhoodAgentCard';
import AgentTabView from '@/components/AgentTabView';
import AskBar from '@/components/chat/AskBar';
import SignInPrompt from '@/components/SignInPrompt';
import { Skeleton, SkeletonMoverRow, SkeletonRows } from '@/components/ui/Skeleton';
import Animated, { FadeInDown } from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';
import * as WebBrowser from 'expo-web-browser';

type MarketRegion = 'us' | 'india';

// Index cards per row: 2 on phones, 4 on tablet-width windows. Account for
// 16px side padding + 10px inter-card gaps. Must be derived from the LIVE
// window width (useWindowDimensions) — a value captured at module load goes
// stale when iPadOS resizes the app window, leaving the grid overflowing or
// cramped.
const idxCardWidth = (windowWidth: number) => {
  const cols = windowWidth >= 700 ? 4 : 2;
  return (windowWidth - 16 * 2 - 10 * (cols - 1)) / cols;
};

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

type HomeTab = 'markets' | 'earnings' | 'watchlist' | 'portfolio' | 'agent';

const NAV_TABS: { key: HomeTab; label: string }[] = [
  { key: 'markets', label: 'Markets' },
  { key: 'earnings', label: 'Earnings' },
  { key: 'watchlist', label: 'Watchlist' },
  { key: 'portfolio', label: 'Portfolio' },
  { key: 'agent', label: 'Trading Agent' },
];

export default function HomeScreen() {
  const { user } = useAuth();
  const { openDrawer } = useDrawer();
  const router = useRouter();
  const { tab: tabParam } = useLocalSearchParams<{ tab?: string }>();
  const [activeTab, setActiveTab] = useState<HomeTab>('markets');

  // Let other surfaces (e.g. the sidebar nav) deep-link into a specific tab.
  useEffect(() => {
    if (tabParam && NAV_TABS.some(t => t.key === tabParam)) {
      setActiveTab(tabParam as HomeTab);
    }
  }, [tabParam]);
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
  const [marketsUpdatedAt, setMarketsUpdatedAt] = useState(() => new Date().toISOString());

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
  const [reverify, setReverify] = useState<SnapTradeStatusResponse | null>(null);

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
      setMarketsUpdatedAt(new Date().toISOString());
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
      setReverify((status as SnapTradeStatusResponse).needs_reverify ? (status as SnapTradeStatusResponse) : null);

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

  // Refetch on focus only when a source is stale — previously every focus
  // refetched all four endpoints, even when returning from a quick stock peek.
  // Markets is keyed by region so toggling US/India still refetches immediately.
  useFocusEffect(useCallback(() => {
    const TTL = 60_000;
    const marketsKey = `home-markets:${marketRegion}`;
    if (!isCacheFresh(marketsKey, TTL)) fetchMarkets().then(() => touchCache(marketsKey));
    if (!isCacheFresh('home-earnings', TTL)) fetchEarnings().then(() => touchCache('home-earnings'));
    // User-dependent: only mark fresh once we actually have a user to fetch for.
    if (user) {
      if (!isCacheFresh('home-watchlist', TTL)) fetchWatchlist().then(() => touchCache('home-watchlist'));
      if (!isCacheFresh('home-portfolio', TTL)) fetchPortfolio().then(() => touchCache('home-portfolio'));
    }
    notificationsApi.getUnreadCount().then(d => {
      const count = d.unread_count || 0;
      setUnreadCount(count);
      syncBadgeCount(count);
    }).catch(() => {});
  }, [user, marketRegion, fetchMarkets, fetchEarnings, fetchWatchlist, fetchPortfolio]));

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
    if (!user) {
      router.push('/(auth)/login');
      return;
    }
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
    <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={['top']}>
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
        <KeyboardAvoidingView
          style={{ flex: 1 }}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
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
          <View style={{ flex: 1 }}>
          {activeTab === 'markets' && (
            <MarketsTab
              gainers={gainers} losers={losers} actives={actives} news={news}
              loading={marketsLoading} refreshing={refreshing} onRefresh={onRefresh}
              onStockPress={(s) => router.push(`/stock/${s}`)}
              marketRegion={marketRegion}
              onRegionChange={(r) => { setMarketRegion(r); setMarketsLoading(true); }}
              indexQuotes={indexQuotes}
              updatedAt={marketsUpdatedAt}
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
            user ? (
              <WatchlistTab
                items={watchlistItems} loading={watchlistLoading}
                refreshing={refreshing} onRefresh={onRefresh}
                onStockPress={(s) => router.push(`/stock/${s}`)}
                onRemove={removeFromWatchlist}
              />
            ) : (
              <SignInPrompt
                title="Track your favorite stocks"
                description="Sign in to build a watchlist and follow the symbols you care about."
              />
            )
          )}
          {activeTab === 'portfolio' && !user && (
            <SignInPrompt
              title="See your portfolio in one place"
              description="Sign in to securely connect your brokerage and track holdings, performance, and trades."
            />
          )}
          {activeTab === 'portfolio' && user && (
            <PortfolioTab
              isConnected={isConnected}
              reverify={reverify}
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
          {activeTab === 'agent' && (
            user ? (
              <AgentTabView userId={user.id} />
            ) : (
              <SignInPrompt
                title="Meet your trading agent"
                description="Sign in to set up an AI agent that researches and manages trades with your approval."
              />
            )
          )}
          </View>

          {/* Persistent contextual ask bar — fuses the dashboard with the AI chat */}
          <AskBar
            placeholder={activeTab === 'portfolio' ? 'Ask anything about your portfolio…' : 'Ask anything about the markets…'}
          />
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}

// ── Markets Tab ──────────────────────────────────────────────────────────────

function MarketsTab({ gainers, losers, actives, news, loading, refreshing, onRefresh, onStockPress, marketRegion, onRegionChange, indexQuotes, updatedAt }: {
  gainers: any[]; losers: any[]; actives: any[]; news: any[];
  loading: boolean; refreshing: boolean; onRefresh: () => void;
  onStockPress: (symbol: string) => void;
  marketRegion: MarketRegion;
  onRegionChange: (r: MarketRegion) => void;
  indexQuotes: Record<string, any>;
  updatedAt: string;
}) {
  const [showRegionPicker, setShowRegionPicker] = useState(false);
  const { width: windowWidth } = useWindowDimensions();
  const cardW = idxCardWidth(windowWidth);

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
  const sentiment = marketSentiment(indices, indexQuotes);

  return (
    <ScrollView
      className="flex-1"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
      showsVerticalScrollIndicator={false}
    >
      {/* Market Region Toggle + Sentiment */}
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
        <SentimentChip s={sentiment} />
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

      {/* Index Cards — 2-column grid */}
      <View style={idxStyles.grid}>
        {indices.map(idx => {
          const q = indexQuotes[idx.symbol] || {};
          const up = (q.changesPercentage ?? 0) >= 0;
          return (
            <TouchableOpacity key={idx.symbol} onPress={() => onStockPress(idx.symbol)} style={[idxStyles.gridCard, { width: cardW }]} activeOpacity={0.7}>
              <View className="flex-row items-center justify-between">
                <Text style={idxStyles.cardLabel} numberOfLines={1}>{idx.label}</Text>
                {q.changesPercentage != null && (
                  <Text style={[idxStyles.cardChange, { color: up ? '#059669' : '#ef4444' }]}>
                    {up ? '↗' : '↘'} {formatPct(q.changesPercentage)}
                  </Text>
                )}
              </View>
              <Text style={idxStyles.cardPrice}>{q.price ? formatCurrency(q.price, false, idx.symbol) : '—'}</Text>
              <View style={idxStyles.cardSpark}>
                <MiniSparkline symbol={idx.symbol} width={cardW - 28} height={30} days={7} />
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

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
          <View className="flex-row items-center justify-between mb-2.5">
            <Text className="text-[13px] font-body-bold text-gray-900 uppercase tracking-wide">Market Summary</Text>
            <Text className="text-[11px] font-body text-gray-400">Updated {formatRelativeTime(updatedAt)}</Text>
          </View>
          <View className="gap-2.5">
            {news.slice(0, 6).map((item: any, i: number) => (
              <NewsCard
                key={i}
                title={item.title}
                source={item.site || item.source || ''}
                date={item.publishedDate || item.date || ''}
                url={item.url}
                image={item.image}
                symbol={item.symbol}
                onSymbolPress={onStockPress}
              />
            ))}
          </View>
        </View>
      )}
    </ScrollView>
  );
}

// Market sentiment derived from index moves we already fetched (no extra call).
// VIX is excluded — it inverts (up = fear) and would skew the read.
function marketSentiment(indices: { symbol: string }[], indexQuotes: Record<string, any>) {
  const vals = indices
    .filter(i => !/VIX/i.test(i.symbol))
    .map(i => indexQuotes[i.symbol]?.changesPercentage)
    .filter((v): v is number => typeof v === 'number');
  if (vals.length === 0) return null;
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
  if (avg >= 0.25) return { label: 'Upbeat', color: '#059669', score: 3 };
  if (avg <= -0.25) return { label: 'Cautious', color: '#ef4444', score: 1 };
  return { label: 'Mixed', color: '#9ca3af', score: 2 };
}

function SentimentChip({ s }: { s: { label: string; color: string; score: number } | null }) {
  if (!s) return null;
  return (
    <View style={idxStyles.sentiment}>
      <View style={idxStyles.bars}>
        {[6, 9, 12].map((h, i) => (
          <View key={i} style={{ width: 3, height: h, borderRadius: 1.5, backgroundColor: i < s.score ? s.color : '#e5e7eb' }} />
        ))}
      </View>
      <Text style={[idxStyles.sentimentText, { color: s.color }]}>{s.label} sentiment</Text>
    </View>
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

function PortfolioTab({ isConnected, reverify, portfolioData, accounts, performance, brokerages, loading, refreshing, onRefresh, onStockPress, userId, onConnectionChange }: {
  isConnected: boolean;
  reverify?: SnapTradeStatusResponse | null;
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
        contentContainerClassName="px-4 pt-5 pb-6"
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
          <View>
            {reverify?.needs_reverify && (
              <View className="mb-3 rounded-xl border border-amber-200 bg-amber-50 p-4 flex-row items-start gap-3">
                <View className="w-9 h-9 rounded-lg bg-amber-100 items-center justify-center">
                  <AlertTriangle size={18} color="#d97706" />
                </View>
                <View className="flex-1">
                  <Text className="text-[14px] font-body-bold text-amber-900">Brokerage connection paused</Text>
                  <Text className="text-[12px] font-body text-amber-700 mt-0.5">
                    We paused your connection after a period of inactivity. Reconnect to refresh your live portfolio.
                    {reverify.last_portfolio_value != null && (
                      <Text className="font-body-medium"> Last known value: {formatCurrency(reverify.last_portfolio_value)}
                        {reverify.last_synced_at ? ` as of ${new Date(reverify.last_synced_at).toLocaleDateString()}` : ''}.</Text>
                    )}
                  </Text>
                </View>
              </View>
            )}

            <Text style={pStyles.chooseHeader}>Set up your portfolio</Text>

            {/* Option 1 — Connect a real brokerage (primary) */}
            <View style={pStyles.optionCard}>
              <View style={pStyles.optionIcon}>
                <Link size={20} color="#059669" />
              </View>
              <Text style={pStyles.optionTitle}>{reverify?.needs_reverify ? 'Reconnect your brokerage' : 'Connect your brokerage'}</Text>
              <Text style={pStyles.optionDesc}>
                Securely sync your accounts to track holdings, performance, and trades — all in one place. Read-only.
              </Text>
              <View style={pStyles.brokerChips}>
                {['Robinhood', 'Schwab', 'Fidelity', 'E*TRADE'].map(b => (
                  <View key={b} style={pStyles.brokerChip}><Text style={pStyles.brokerChipText}>{b}</Text></View>
                ))}
                <View style={pStyles.brokerChip}><Text style={pStyles.brokerChipText}>+20 more</Text></View>
              </View>
              <TouchableOpacity
                onPress={() => setShowBrokers(true)}
                style={pStyles.connectBtn}
                activeOpacity={0.85}
                disabled={connecting}
              >
                {connecting ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={pStyles.connectBtnText}>{reverify?.needs_reverify ? 'Reconnect' : 'Connect account'}</Text>
                )}
              </TouchableOpacity>
            </View>

            <View style={pStyles.optionDivider}>
              <View style={pStyles.dividerLine} />
              <Text style={pStyles.dividerText}>or</Text>
              <View style={pStyles.dividerLine} />
            </View>

            {/* Option 2 — AI trading agent (distinct, secondary) */}
            <RobinhoodAgentCard userId={userId} />

            <View style={pStyles.trustRow}>
              <Lock size={12} color="#9ca3af" />
              <Text style={pStyles.trustText}>Bank-level encryption · Read-only access · Disconnect anytime</Text>
            </View>
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
      {/* AI Trading Agent (Robinhood) */}
      <RobinhoodAgentCard userId={userId} />

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
  chooseHeader: {
    fontSize: 13,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 10,
    marginLeft: 2,
  },
  optionCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  optionIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#ecfdf5',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  optionTitle: {
    fontSize: 17,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
  },
  optionDesc: {
    fontSize: 13,
    fontFamily: 'DMSans',
    color: '#6b7280',
    lineHeight: 19,
    marginTop: 5,
  },
  brokerChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 14,
    marginBottom: 16,
  },
  brokerChip: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    paddingHorizontal: 9,
    paddingVertical: 4,
    backgroundColor: '#fafafa',
  },
  brokerChipText: {
    fontSize: 11,
    fontFamily: 'DMSans-Medium',
    color: '#6b7280',
  },
  connectBtn: {
    backgroundColor: '#059669',
    paddingVertical: 13,
    borderRadius: 12,
    alignItems: 'center',
    alignSelf: 'stretch',
  },
  connectBtnText: {
    fontSize: 15,
    fontFamily: 'DMSans-Medium',
    color: '#fff',
  },
  optionDivider: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginVertical: 14,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#ececeb',
  },
  dividerText: {
    fontSize: 12,
    fontFamily: 'DMSans-Medium',
    color: '#9ca3af',
  },
  trustRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginTop: 18,
  },
  trustText: {
    fontSize: 11,
    fontFamily: 'DMSans',
    color: '#9ca3af',
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
  cardLabel: { fontSize: 11, fontFamily: 'DMSans-Bold', color: '#9ca3af', letterSpacing: 0.3, flexShrink: 1 },
  cardPrice: { fontSize: 18, fontFamily: 'DMSans-Bold', color: '#111827', marginTop: 4 },
  cardChange: { fontSize: 11, fontFamily: 'DMSans-Medium' },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
    gap: 10,
    marginBottom: 20,
  },
  gridCard: {
    backgroundColor: '#fff',
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingTop: 12,
    paddingBottom: 8,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  cardSpark: { marginTop: 6, alignItems: 'flex-start' },
  sentiment: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  bars: { flexDirection: 'row', alignItems: 'flex-end', gap: 2, height: 12 },
  sentimentText: { fontSize: 12, fontFamily: 'DMSans-Medium' },
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
