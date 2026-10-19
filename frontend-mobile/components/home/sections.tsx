// Section bodies lifted out of the old tabbed home screen. Each one is now
// hosted by its own screen (markets, calendar, portfolio) behind a home card.
import { View, Text, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator, TextInput, FlatList, Alert, Platform, StyleSheet, useWindowDimensions } from 'react-native';
import { useAuth } from '@/contexts/AuthContext';
import { useState } from 'react';
import { snaptradeApi } from '@/lib/api';
import type { SnapTradeStatusResponse } from '@/lib/types';
import { AlertTriangle } from 'lucide-react-native';
import { Search as SearchIcon, X, Calendar, Star, Trash2, Link, ExternalLink, Trash, ChevronRight, ChevronDown, Lock } from 'lucide-react-native';
import { formatCurrency, formatPct, formatRelativeTime, COLORS } from '@/lib/constants';
import SectionHeader from '@/components/ui/SectionHeader';
import MoverCard from '@/components/market/MoverCard';
import NewsCard from '@/components/market/NewsCard';
import EmptyState from '@/components/ui/EmptyState';
import DataError from '@/components/ui/DataError';
import MiniSparkline from '@/components/shared/MiniSparkline';
import RobinhoodAgentCard from '@/components/RobinhoodAgentCard';
import TodayDigestCard from '@/components/insights/TodayDigestCard';
import WhileYouWereGoneCard from '@/components/activity/WhileYouWereGoneCard';
import { Skeleton, SkeletonMoverRow, SkeletonRows } from '@/components/ui/Skeleton';
import Animated, { FadeInDown } from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';
import * as WebBrowser from 'expo-web-browser';

export type MarketRegion = 'us' | 'india';

// Index cards per row: 2 on phones, 4 on tablet-width windows. Account for
// 16px side padding + 10px inter-card gaps. Must be derived from the LIVE
// window width (useWindowDimensions) — a value captured at module load goes
// stale when iPadOS resizes the app window, leaving the grid overflowing or
// cramped.
const idxCardWidth = (windowWidth: number) => {
  const cols = windowWidth >= 700 ? 4 : 2;
  return (windowWidth - 16 * 2 - 10 * (cols - 1)) / cols;
};

export const MARKET_INDICES: Record<MarketRegion, { symbol: string; label: string }[]> = {
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

// ── Markets Tab ──────────────────────────────────────────────────────────────

export function MarketsTab({ gainers, losers, actives, news, loading, error, refreshing, onRefresh, onStockPress, marketRegion, onRegionChange, indexQuotes, updatedAt, isConnected, onConnectPress, showBriefing = true }: {
  gainers: any[]; losers: any[]; actives: any[]; news: any[];
  loading: boolean; error?: boolean; refreshing: boolean; onRefresh: () => void;
  onStockPress: (symbol: string) => void;
  marketRegion: MarketRegion;
  onRegionChange: (r: MarketRegion) => void;
  indexQuotes: Record<string, any>;
  updatedAt: string;
  isConnected?: boolean;
  onConnectPress?: () => void;
  showBriefing?: boolean;
}) {
  const { user } = useAuth();
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
      {/* The briefing block — the agent accounts for itself (ledger, approvals)
          and tells the story of the user's day (digest) before market data. */}
      {showBriefing && <WhileYouWereGoneCard hasBrokerage={isConnected} onConnect={onConnectPress} />}
      {showBriefing && user && (
        <View className="px-4 mt-2">
          <TodayDigestCard userId={user.id} />
        </View>
      )}

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
      {error ? (
        <View className="px-4 mb-4">
          <DataError message="Couldn't load market data" onRetry={onRefresh} />
        </View>
      ) : (
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
      )}

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

export function EarningsTab({ earnings, loading, error, refreshing, onRefresh, onStockPress }: {
  earnings: any[]; loading: boolean; error?: boolean; refreshing: boolean; onRefresh: () => void;
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
      {error && earnings.length === 0 ? (
        // A failed fetch must not masquerade as "no earnings this week".
        <DataError message="Couldn't load the earnings calendar" onRetry={onRefresh} />
      ) : earnings.length === 0 ? (
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

export function WatchlistTab({ items, loading, refreshing, onRefresh, onStockPress, onRemove }: {
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

export function PortfolioTab({ isConnected, reverify, portfolioData, accounts, performance, brokerages, loading, refreshing, onRefresh, onStockPress, userId, onConnectionChange, onStartWatchlist }: {
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
  onStartWatchlist: () => void;
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
            {/* Watchlist-mode digest — show the daily AI story even before a
                brokerage is connected, so this screen previews value instead
                of gating it. Renders nothing when there's no watchlist. */}
            <TodayDigestCard userId={userId} />

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

            {/* Escape hatch — not ready to connect shouldn't be a dead end */}
            <TouchableOpacity
              onPress={onStartWatchlist}
              activeOpacity={0.7}
              className="mt-4 flex-row items-center justify-center"
              style={{ gap: 4 }}
            >
              <Text className="text-[13px] font-body-medium text-emerald-700">
                Not ready? Start with a watchlist
              </Text>
              <ChevronRight size={14} color="#047857" />
            </TouchableOpacity>
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
      {/* Today digest (AI story of the day) */}
      <TodayDigestCard userId={userId} />

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

