import { View, Text, ScrollView, ActivityIndicator, TouchableOpacity, RefreshControl, StyleSheet, Platform, Alert, KeyboardAvoidingView } from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { useState, useEffect, useCallback } from 'react';
import { marketApi, chatApi, watchlistApi, analysisApi } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { MessageSquare, Star, BarChart3, FileText, TrendingUp, ChevronRight } from 'lucide-react-native';
import { COLORS, formatCurrency, formatPct, formatVolume, currencySymbol } from '@/lib/constants';
import * as Haptics from 'expo-haptics';
import SectionHeader from '@/components/ui/SectionHeader';
import NewsCard from '@/components/market/NewsCard';
import PriceChart from '@/components/shared/PriceChart';
import AskBar from '@/components/chat/AskBar';
import PriceChange from '@/components/ui/PriceChange';
import { CountUp } from '@/components/ui/CountUp';
import { Skeleton, SkeletonRows } from '@/components/ui/Skeleton';

type StockTab = 'overview' | 'earnings' | 'financials' | 'news' | 'analysis';

const TABS: { key: StockTab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'earnings', label: 'Earnings' },
  { key: 'financials', label: 'Financials' },
  { key: 'news', label: 'News' },
  { key: 'analysis', label: 'Analysis' },
];

export default function StockDetailScreen() {
  const { symbol } = useLocalSearchParams<{ symbol: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [quote, setQuote] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [news, setNews] = useState<any[]>([]);
  const [peers, setPeers] = useState<any[]>([]);
  const [analyst, setAnalyst] = useState<any>(null);
  const [earningsHistory, setEarningsHistory] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [inWatchlist, setInWatchlist] = useState(false);
  const [activeTab, setActiveTab] = useState<StockTab>('overview');

  const fetchData = useCallback(async () => {
    try {
      const [quoteData, profileData, newsData, peersData, analystData, earningsData, analysisData] = await Promise.all([
        marketApi.getQuote(symbol),
        marketApi.getProfile(symbol).catch(() => null),
        marketApi.getNews(symbol, 8).catch(() => ({ news: [] })),
        marketApi.getPeers(symbol, 6).catch(() => ({ peers: [] })),
        marketApi.getAnalyst(symbol).catch(() => null),
        marketApi.getEarningsHistory(symbol, 8).catch(() => []),
        analysisApi.getBySymbol(symbol).catch(() => []),
      ]);
      setQuote(quoteData);
      setProfile(profileData);
      setNews(newsData.news || newsData || []);
      setPeers(peersData.peers || peersData || []);
      setAnalyst(analystData);
      setEarningsHistory(earningsData.earnings || earningsData || []);
      setAnalysis(Array.isArray(analysisData) ? analysisData : analysisData?.notes || []);

      if (user) {
        try {
          const wl = await watchlistApi.getWatchlist(user.id);
          const symbols = (wl.symbols || wl.watchlist || []).map((s: any) => typeof s === 'string' ? s : s.symbol);
          setInWatchlist(symbols.includes(symbol));
        } catch {}
      }
    } catch {} finally {
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
    if (!user) {
      router.push('/(auth)/login');
      return;
    }
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      if (inWatchlist) await watchlistApi.removeSymbol(user.id, symbol);
      else await watchlistApi.addSymbol(user.id, symbol);
      setInWatchlist(!inWatchlist);
    } catch {}
  };

  const chatAboutStock = async () => {
    if (!user) {
      router.push('/(auth)/login');
      return;
    }
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}`);
    } catch {}
  };

  return (
    <View style={{ flex: 1, backgroundColor: '#fafaf9' }}>
      <Stack.Screen
        options={{
          headerTitle: symbol,
          headerStyle: { backgroundColor: '#ffffff' },
          headerRight: () => (
            <TouchableOpacity testID="watchlist-toggle" onPress={toggleWatchlist} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }} activeOpacity={0.7}>
              <Star size={20} color={inWatchlist ? '#f59e0b' : '#9ca3af'} fill={inWatchlist ? '#f59e0b' : 'none'} />
            </TouchableOpacity>
          ),
        }}
      />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 96 : 0}
      >
      <ScrollView
        className="flex-1 bg-[#fafaf9]"
        contentContainerClassName="pb-6"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.gray400} />}
        showsVerticalScrollIndicator={false}
      >
        {loading ? (
          <View className="pt-3">
            <View className="px-4 mb-5">
              <Skeleton width={120} height={12} radius={4} />
              <Skeleton width={170} height={34} radius={6} style={{ marginTop: 10 }} />
              <Skeleton width={90} height={14} radius={4} style={{ marginTop: 10 }} />
            </View>
            <View className="flex-row gap-2 px-4 mb-5">
              <Skeleton width={180} height={40} radius={12} />
              <Skeleton width={48} height={40} radius={12} />
            </View>
            <View className="px-4 mb-5"><Skeleton width="100%" height={150} radius={14} /></View>
            <SkeletonRows count={4} />
          </View>
        ) : quote ? (
          <>
            {/* Price Header */}
            <View className="px-4 mt-2 mb-4">
              <Text style={s.companyName}>
                {profile?.companyName || quote.name || symbol}
              </Text>
              <View className="flex-row items-baseline gap-2.5 mt-0.5">
                <CountUp value={quote.price} format={(n) => formatCurrency(n, false, symbol)} style={s.price} />
                <PriceChange value={quote.change || 0} percent={quote.changesPercentage} size="lg" />
              </View>
              {profile?.exchangeShortName && (
                <Text style={s.exchangeLabel}>
                  {profile.exchangeShortName} · {profile.sector || quote.exchange}
                </Text>
              )}
            </View>

            {/* Price Chart */}
            <View className="mb-4">
              <PriceChart symbol={symbol} />
            </View>


            {/* Tab Bar */}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} className="border-b border-gray-100 mb-4" contentContainerStyle={{ paddingHorizontal: 16, gap: 20 }}>
              {TABS.map(tab => (
                <TouchableOpacity
                  key={tab.key}
                  onPress={() => { Haptics.selectionAsync(); setActiveTab(tab.key); }}
                  style={s.tab}
                  activeOpacity={0.7}
                >
                  <Text style={[s.tabText, activeTab === tab.key && s.tabTextActive]}>{tab.label}</Text>
                  {activeTab === tab.key && <View style={s.tabIndicator} />}
                </TouchableOpacity>
              ))}
            </ScrollView>

            {/* Tab Content */}
            {activeTab === 'overview' && (
              <OverviewTab
                symbol={symbol}
                quote={quote}
                profile={profile}
                analyst={analyst}
                peers={peers}
                router={router}
              />
            )}
            {activeTab === 'earnings' && (
              <EarningsTab earnings={earningsHistory} />
            )}
            {activeTab === 'financials' && (
              <FinancialsTab symbol={symbol} />
            )}
            {activeTab === 'news' && (
              <NewsTab news={news} />
            )}
            {activeTab === 'analysis' && (
              <AnalysisTab
                analyst={analyst}
                analysis={analysis}
                quote={quote}
                onChat={chatAboutStock}
              />
            )}
          </>
        ) : (
          <View className="py-20 items-center">
            <Text className="text-gray-400 font-body text-[13px]">Failed to load stock data</Text>
          </View>
        )}
      </ScrollView>

      {/* Persistent contextual ask bar */}
      {!loading && quote && (
        <AskBar placeholder={`Ask anything about ${symbol}…`} prefix={`Regarding ${symbol}: `} />
      )}
      </KeyboardAvoidingView>
    </View>
  );
}

// ── Overview Tab ────────────────────────────────────────────────────────────────

function OverviewTab({ symbol, quote, profile, analyst, peers, router }: {
  symbol: string; quote: any; profile: any; analyst: any; peers: any[]; router: any;
}) {
  return (
    <>
      {/* Key Stats */}
      <View className="px-4 mb-3.5">
        <View style={s.card}>
          <Text style={s.cardTitle}>Key Stats</Text>
          <View className="flex-row flex-wrap gap-y-3.5">
            {[
              { label: 'Day High', value: quote.dayHigh ? formatCurrency(quote.dayHigh, false, symbol) : '—' },
              { label: 'Day Low', value: quote.dayLow ? formatCurrency(quote.dayLow, false, symbol) : '—' },
              { label: 'Open', value: quote.open ? formatCurrency(quote.open, false, symbol) : '—' },
              { label: 'Prev Close', value: quote.previousClose ? formatCurrency(quote.previousClose, false, symbol) : '—' },
              { label: 'Volume', value: formatVolume(quote.volume || 0) },
              { label: 'Avg Volume', value: formatVolume(quote.avgVolume || 0) },
              { label: 'Mkt Cap', value: formatVolume(quote.marketCap || profile?.mktCap || 0) },
              { label: 'P/E', value: (quote.pe || profile?.peRatio) ? (quote.pe || profile.peRatio).toFixed(1) : '—' },
              { label: 'EPS', value: (quote.eps || profile?.eps) ? `${currencySymbol(symbol)}${(quote.eps || profile.eps).toFixed(2)}` : '—' },
              { label: 'Div Yield', value: profile?.lastDiv ? `${((profile.lastDiv / quote.price) * 100).toFixed(2)}%` : '—' },
              { label: '52w High', value: quote.yearHigh ? formatCurrency(quote.yearHigh, false, symbol) : '—' },
              { label: '52w Low', value: quote.yearLow ? formatCurrency(quote.yearLow, false, symbol) : '—' },
            ].map(stat => (
              <View key={stat.label} className="w-1/3">
                <Text style={s.statLabel}>{stat.label}</Text>
                <Text style={s.statValue}>{stat.value}</Text>
              </View>
            ))}
          </View>
        </View>
      </View>

      {/* 52-Week Range */}
      {quote.yearLow && quote.yearHigh && (
        <View className="px-4 mb-3.5">
          <View style={s.card}>
            <Text style={s.cardTitle}>52-Week Range</Text>
            <View className="flex-row items-center gap-2 mt-1">
              <Text style={s.rangeLabel}>{formatCurrency(quote.yearLow, false, symbol)}</Text>
              <View style={s.rangeTrack}>
                <View
                  style={[s.rangeFill, {
                    width: `${Math.min(100, Math.max(0, ((quote.price - quote.yearLow) / (quote.yearHigh - quote.yearLow)) * 100))}%`,
                  }]}
                />
                <View
                  style={[s.rangeDot, {
                    left: `${Math.min(100, Math.max(0, ((quote.price - quote.yearLow) / (quote.yearHigh - quote.yearLow)) * 100))}%`,
                  }]}
                />
              </View>
              <Text style={s.rangeLabel}>{formatCurrency(quote.yearHigh, false, symbol)}</Text>
            </View>
          </View>
        </View>
      )}

      {/* Analyst Ratings */}
      {analyst && (analyst.consensus || analyst.targetConsensus) && (
        <View className="px-4 mb-3.5">
          <View style={s.card}>
            <Text style={s.cardTitle}>Analyst Ratings</Text>

            {/* Price Target Range */}
            {analyst.targetConsensus && (
              <View className="mb-4">
                <View className="flex-row justify-between mb-2">
                  <View>
                    <Text style={s.statLabel}>Low</Text>
                    <Text style={s.targetPrice}>{formatCurrency(analyst.targetConsensus.targetLow || 0, false, symbol)}</Text>
                  </View>
                  <View className="items-center">
                    <Text style={s.statLabel}>Average</Text>
                    <Text style={[s.targetPrice, { color: '#059669' }]}>{formatCurrency(analyst.targetConsensus.targetMedian || analyst.targetConsensus.targetConsensus || 0, false, symbol)}</Text>
                  </View>
                  <View className="items-end">
                    <Text style={s.statLabel}>High</Text>
                    <Text style={s.targetPrice}>{formatCurrency(analyst.targetConsensus.targetHigh || 0, false, symbol)}</Text>
                  </View>
                </View>
                {/* Price target bar */}
                {analyst.targetConsensus.targetLow && analyst.targetConsensus.targetHigh && (
                  <View style={s.targetTrack}>
                    <View style={s.targetBar} />
                    {quote.price && (
                      <View style={[s.targetCurrentDot, {
                        left: `${Math.min(95, Math.max(5, ((quote.price - analyst.targetConsensus.targetLow) / (analyst.targetConsensus.targetHigh - analyst.targetConsensus.targetLow)) * 100))}%`,
                      }]}>
                        <Text style={s.targetCurrentLabel}>Current</Text>
                      </View>
                    )}
                  </View>
                )}
                {quote.price && analyst.targetConsensus.targetMedian && (
                  <Text style={s.upsideText}>
                    {analyst.targetConsensus.targetMedian > quote.price ? '↑' : '↓'}{' '}
                    {formatPct(((analyst.targetConsensus.targetMedian - quote.price) / quote.price) * 100)} to avg target
                  </Text>
                )}
              </View>
            )}

            {/* Consensus Breakdown */}
            {analyst.consensus && (
              <View className="flex-row gap-2">
                {[
                  { label: 'Buy', count: (analyst.consensus.buy || 0) + (analyst.consensus.strongBuy || 0), bg: '#ecfdf5', color: '#059669' },
                  { label: 'Hold', count: analyst.consensus.hold || 0, bg: '#fffbeb', color: '#d97706' },
                  { label: 'Sell', count: (analyst.consensus.sell || 0) + (analyst.consensus.strongSell || 0), bg: '#fef2f2', color: '#dc2626' },
                ].map(r => (
                  <View key={r.label} className="flex-1 rounded-xl py-2.5 items-center" style={{ backgroundColor: r.bg }}>
                    <Text className="text-base font-body-bold" style={{ color: r.color }}>{r.count}</Text>
                    <Text style={s.ratingLabel}>{r.label}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        </View>
      )}

      {/* Peer Companies */}
      {peers.length > 0 && (
        <View className="px-4 mb-3.5">
          <SectionHeader title="Related Stocks" />
          <View style={s.listCard}>
            {peers.slice(0, 6).map((peer: any, i: number) => (
              <TouchableOpacity
                key={peer.symbol || i}
                onPress={() => router.push(`/stock/${peer.symbol}`)}
                style={[s.peerRow, i > 0 && { borderTopWidth: 1, borderTopColor: '#f3f4f6' }]}
                activeOpacity={0.6}
              >
                <View className="flex-1">
                  <Text style={s.peerSymbol}>{peer.symbol}</Text>
                  <Text style={s.peerName} numberOfLines={1}>{peer.name || peer.companyName}</Text>
                </View>
                {peer.price && (
                  <View className="items-end">
                    <Text style={s.peerPrice}>{formatCurrency(peer.price, false, symbol)}</Text>
                    {peer.changesPercentage != null && (
                      <Text style={[s.peerChange, { color: peer.changesPercentage >= 0 ? '#059669' : '#ef4444' }]}>
                        {formatPct(peer.changesPercentage)}
                      </Text>
                    )}
                  </View>
                )}
                <ChevronRight size={14} color="#d1d5db" style={{ marginLeft: 8 }} />
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* About */}
      {profile && (
        <View className="px-4 mb-3.5">
          <View style={s.card}>
            <Text style={s.cardTitle}>About</Text>
            {profile.description && (
              <Text style={s.aboutText} numberOfLines={6}>{profile.description}</Text>
            )}
            <View className="flex-row flex-wrap gap-y-2.5 mt-3">
              {[
                { label: 'CEO', value: profile.ceo },
                { label: 'Employees', value: profile.fullTimeEmployees?.toLocaleString() },
                { label: 'Sector', value: profile.sector },
                { label: 'Industry', value: profile.industry },
                { label: 'Country', value: profile.country },
                { label: 'IPO Date', value: profile.ipoDate },
              ].filter(item => item.value).map(item => (
                <View key={item.label} className="w-1/2">
                  <Text style={s.statLabel}>{item.label}</Text>
                  <Text style={s.infoValue} numberOfLines={1}>{item.value}</Text>
                </View>
              ))}
            </View>
          </View>
        </View>
      )}
    </>
  );
}

// ── Earnings Tab ────────────────────────────────────────────────────────────────

function EarningsTab({ earnings }: { earnings: any[] }) {
  if (earnings.length === 0) {
    return (
      <View className="py-16 items-center">
        <BarChart3 size={40} color="#d1d5db" />
        <Text style={s.emptyText}>No earnings data available</Text>
      </View>
    );
  }

  return (
    <View className="px-4">
      {/* Summary stats */}
      <View className="flex-row gap-2 mb-4">
        {(() => {
          const beats = earnings.filter(e => e.actualEarningResult != null && e.estimatedEarning != null && e.actualEarningResult > e.estimatedEarning).length;
          const total = earnings.filter(e => e.actualEarningResult != null && e.estimatedEarning != null).length;
          return (
            <>
              <View style={s.miniStat}>
                <Text style={s.miniStatValue}>{total > 0 ? `${((beats / total) * 100).toFixed(0)}%` : '—'}</Text>
                <Text style={s.miniStatLabel}>Beat Rate</Text>
              </View>
              <View style={s.miniStat}>
                <Text style={s.miniStatValue}>{beats}/{total}</Text>
                <Text style={s.miniStatLabel}>Beats</Text>
              </View>
            </>
          );
        })()}
      </View>

      <View style={s.listCard}>
        <View style={s.tableHeader}>
          <Text style={[s.tableHeaderText, { flex: 1 }]}>Date</Text>
          <Text style={[s.tableHeaderText, { width: 70, textAlign: 'right' }]}>Est.</Text>
          <Text style={[s.tableHeaderText, { width: 70, textAlign: 'right' }]}>Actual</Text>
          <Text style={[s.tableHeaderText, { width: 56, textAlign: 'right' }]}>Surprise</Text>
        </View>
        {earnings.map((e: any, i: number) => {
          const surprise = e.actualEarningResult != null && e.estimatedEarning
            ? ((e.actualEarningResult - e.estimatedEarning) / Math.abs(e.estimatedEarning)) * 100
            : null;
          const beat = surprise !== null && surprise > 0;
          return (
            <View key={i} style={[s.tableRow, i > 0 && { borderTopWidth: 1, borderTopColor: '#f3f4f6' }]}>
              <Text style={[s.tableCell, { flex: 1, color: '#374151' }]}>{e.date || e.fiscalDateEnding}</Text>
              <Text style={[s.tableCell, { width: 70, textAlign: 'right', color: '#9ca3af' }]}>
                {e.estimatedEarning != null ? `$${e.estimatedEarning.toFixed(2)}` : '—'}
              </Text>
              <Text style={[s.tableCell, { width: 70, textAlign: 'right', fontFamily: 'DMSans-Medium', color: '#111827' }]}>
                {e.actualEarningResult != null ? `$${e.actualEarningResult.toFixed(2)}` : '—'}
              </Text>
              <Text style={[s.tableCell, { width: 56, textAlign: 'right', fontFamily: 'DMSans-Medium', color: beat ? '#059669' : surprise !== null ? '#ef4444' : '#9ca3af' }]}>
                {surprise !== null ? formatPct(surprise) : '—'}
              </Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

// ── Financials Tab ──────────────────────────────────────────────────────────────

type FinancialStatement = 'key-stats' | 'income-statement' | 'balance-sheet-statement' | 'cash-flow-statement' | 'ratios';

const STATEMENT_TYPES: { key: FinancialStatement; label: string }[] = [
  { key: 'key-stats', label: 'Key Stats' },
  { key: 'income-statement', label: 'Income' },
  { key: 'balance-sheet-statement', label: 'Balance Sheet' },
  { key: 'cash-flow-statement', label: 'Cash Flow' },
  { key: 'ratios', label: 'Ratios' },
];

type FRow =
  | { t: 's'; label: string }
  | { t: 'd'; key: string; label: string; fmt?: 'c' | 'p' | 'r' | 'n'; indent?: boolean }
  | { t: 'g'; of: string; label: string }
  | { t: 'm'; num: string; den: string; label: string };

const STATEMENT_ROWS: Record<FinancialStatement, FRow[]> = {
  'key-stats': [
    { t: 'd', key: 'revenue', label: 'Revenue', fmt: 'c' },
    { t: 'g', of: 'revenue', label: '% Growth' },
    { t: 'd', key: 'grossProfit', label: 'Gross Profit', fmt: 'c' },
    { t: 'm', num: 'grossProfit', den: 'revenue', label: '% Margin' },
    { t: 'd', key: 'ebitda', label: 'EBITDA', fmt: 'c' },
    { t: 'd', key: 'netIncome', label: 'Net Income', fmt: 'c' },
    { t: 'm', num: 'netIncome', den: 'revenue', label: '% Margin' },
    { t: 'd', key: 'epsdiluted', label: 'Diluted EPS', fmt: 'r' },
    { t: 'g', of: 'epsdiluted', label: '% Growth' },
    { t: 'd', key: 'operatingCashFlow', label: 'Operating Cash Flow', fmt: 'c' },
    { t: 'd', key: 'freeCashFlow', label: 'Free Cash Flow', fmt: 'c' },
  ],
  'income-statement': [
    { t: 'd', key: 'revenue', label: 'Revenue', fmt: 'c' },
    { t: 'd', key: 'costOfRevenue', label: 'Cost of Revenue', fmt: 'c', indent: true },
    { t: 'd', key: 'grossProfit', label: 'Gross Profit', fmt: 'c' },
    { t: 'd', key: 'sellingGeneralAndAdministrativeExpenses', label: 'SG&A', fmt: 'c', indent: true },
    { t: 'd', key: 'researchAndDevelopmentExpenses', label: 'R&D', fmt: 'c', indent: true },
    { t: 'd', key: 'operatingIncome', label: 'Operating Income', fmt: 'c' },
    { t: 'd', key: 'incomeBeforeTax', label: 'Income Before Tax', fmt: 'c' },
    { t: 'd', key: 'incomeTaxExpense', label: 'Tax Expense', fmt: 'c', indent: true },
    { t: 'd', key: 'netIncome', label: 'Net Income', fmt: 'c' },
    { t: 'd', key: 'epsdiluted', label: 'Diluted EPS', fmt: 'r' },
    { t: 's', label: 'Margins' },
    { t: 'd', key: 'grossProfitRatio', label: 'Gross Margin', fmt: 'p' },
    { t: 'd', key: 'operatingIncomeRatio', label: 'Operating Margin', fmt: 'p' },
    { t: 'd', key: 'netIncomeRatio', label: 'Net Margin', fmt: 'p' },
  ],
  'balance-sheet-statement': [
    { t: 's', label: 'Assets' },
    { t: 'd', key: 'cashAndCashEquivalents', label: 'Cash', fmt: 'c', indent: true },
    { t: 'd', key: 'shortTermInvestments', label: 'Short-Term Investments', fmt: 'c', indent: true },
    { t: 'd', key: 'netReceivables', label: 'Receivables', fmt: 'c', indent: true },
    { t: 'd', key: 'inventory', label: 'Inventories', fmt: 'c', indent: true },
    { t: 'd', key: 'totalCurrentAssets', label: 'Total Current Assets', fmt: 'c' },
    { t: 'd', key: 'propertyPlantEquipmentNet', label: 'PP&E', fmt: 'c', indent: true },
    { t: 'd', key: 'goodwill', label: 'Goodwill', fmt: 'c', indent: true },
    { t: 'd', key: 'totalAssets', label: 'Total Assets', fmt: 'c' },
    { t: 's', label: 'Liabilities' },
    { t: 'd', key: 'totalCurrentLiabilities', label: 'Current Liabilities', fmt: 'c' },
    { t: 'd', key: 'longTermDebt', label: 'Long-Term Debt', fmt: 'c', indent: true },
    { t: 'd', key: 'totalLiabilities', label: 'Total Liabilities', fmt: 'c' },
    { t: 's', label: 'Equity' },
    { t: 'd', key: 'retainedEarnings', label: 'Retained Earnings', fmt: 'c', indent: true },
    { t: 'd', key: 'totalStockholdersEquity', label: 'Total Equity', fmt: 'c' },
  ],
  'cash-flow-statement': [
    { t: 's', label: 'Operating' },
    { t: 'd', key: 'netIncome', label: 'Net Income', fmt: 'c', indent: true },
    { t: 'd', key: 'depreciationAndAmortization', label: 'D&A', fmt: 'c', indent: true },
    { t: 'd', key: 'stockBasedCompensation', label: 'Stock-Based Comp', fmt: 'c', indent: true },
    { t: 'd', key: 'netCashProvidedByOperatingActivities', label: 'Operating Cash Flow', fmt: 'c' },
    { t: 's', label: 'Investing' },
    { t: 'd', key: 'investmentsInPropertyPlantAndEquipment', label: 'CapEx', fmt: 'c', indent: true },
    { t: 'd', key: 'acquisitionsNet', label: 'Acquisitions', fmt: 'c', indent: true },
    { t: 'd', key: 'netCashUsedForInvestingActivites', label: 'Investing Cash Flow', fmt: 'c' },
    { t: 's', label: 'Financing' },
    { t: 'd', key: 'commonStockRepurchased', label: 'Share Repurchases', fmt: 'c', indent: true },
    { t: 'd', key: 'dividendsPaid', label: 'Dividends Paid', fmt: 'c', indent: true },
    { t: 'd', key: 'netCashUsedProvidedByFinancingActivities', label: 'Financing Cash Flow', fmt: 'c' },
    { t: 'd', key: 'netChangeInCash', label: 'Net Change in Cash', fmt: 'c' },
    { t: 'd', key: 'freeCashFlow', label: 'Free Cash Flow', fmt: 'c' },
  ],
  'ratios': [
    { t: 's', label: 'Valuation' },
    { t: 'd', key: 'priceEarningsRatio', label: 'P/E', fmt: 'r' },
    { t: 'd', key: 'priceToSalesRatio', label: 'P/S', fmt: 'r' },
    { t: 'd', key: 'priceToBookRatio', label: 'P/B', fmt: 'r' },
    { t: 'd', key: 'enterpriseValueMultiple', label: 'EV/EBITDA', fmt: 'r' },
    { t: 'd', key: 'priceToFreeCashFlowsRatio', label: 'P/FCF', fmt: 'r' },
    { t: 's', label: 'Profitability' },
    { t: 'd', key: 'grossProfitMargin', label: 'Gross Margin', fmt: 'p' },
    { t: 'd', key: 'operatingProfitMargin', label: 'Operating Margin', fmt: 'p' },
    { t: 'd', key: 'netProfitMargin', label: 'Net Margin', fmt: 'p' },
    { t: 's', label: 'Returns' },
    { t: 'd', key: 'returnOnEquity', label: 'ROE', fmt: 'p' },
    { t: 'd', key: 'returnOnAssets', label: 'ROA', fmt: 'p' },
    { t: 's', label: 'Leverage' },
    { t: 'd', key: 'currentRatio', label: 'Current Ratio', fmt: 'r' },
    { t: 'd', key: 'debtEquityRatio', label: 'Debt/Equity', fmt: 'r' },
  ],
};

const COL_W = 80;

function fmtCell(val: any, fmt?: string): string {
  if (val == null) return '—';
  const n = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(n)) return '—';
  if (fmt === 'p') return `${(n * 100).toFixed(1)}%`;
  if (fmt === 'r') return n.toFixed(2);
  if (fmt === 'n') return n.toLocaleString();
  if (fmt === 'c') return formatVolume(n);
  return String(n);
}

function FinancialsTab({ symbol }: { symbol: string }) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<'annual' | 'quarter'>('annual');
  const [statement, setStatement] = useState<FinancialStatement>('key-stats');

  const apiStatement = statement === 'key-stats' ? 'income-statement'
    : statement === 'ratios' ? 'ratios' as any
    : statement;

  useEffect(() => {
    setLoading(true);
    const fetches = [marketApi.getFinancials(symbol, apiStatement, period, 4).catch(() => null)];
    if (statement === 'key-stats') {
      fetches.push(marketApi.getFinancials(symbol, 'cash-flow-statement', period, 4).catch(() => null));
      fetches.push(marketApi.getFinancials(symbol, 'balance-sheet-statement', period, 4).catch(() => null));
    }
    Promise.all(fetches).then(results => {
      const base = results[0]?.financials || results[0] || [];
      if (statement === 'key-stats' && base.length > 0) {
        const cf = results[1]?.financials || results[1] || [];
        const bs = results[2]?.financials || results[2] || [];
        base.forEach((item: any, i: number) => {
          if (cf[i]) Object.assign(item, { operatingCashFlow: cf[i].operatingCashFlow, freeCashFlow: cf[i].freeCashFlow, capitalExpenditure: cf[i].capitalExpenditure });
          if (bs[i]) Object.assign(item, { cashAndCashEquivalents: bs[i].cashAndCashEquivalents, totalDebt: bs[i].totalDebt });
        });
      }
      setData(base);
    }).finally(() => setLoading(false));
  }, [symbol, period, statement, apiStatement]);

  if (loading) {
    return <View className="py-16 items-center"><ActivityIndicator color={COLORS.gray400} /></View>;
  }

  if (data.length === 0) {
    return (
      <View className="py-16 items-center">
        <FileText size={40} color="#d1d5db" />
        <Text style={s.emptyText}>No financial data available</Text>
      </View>
    );
  }

  const columns = data.slice(0, 4);
  const rows = STATEMENT_ROWS[statement];
  const colLabels = columns.map((c: any) => {
    const d = c.date || c.calendarYear || c.period || '';
    if (period === 'quarter' && d.length >= 7) return d.substring(0, 7);
    if (d.length >= 4) return d.substring(0, 4);
    return d;
  });

  return (
    <View className="px-4">
      {/* Statement Type Selector */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mb-3" contentContainerStyle={{ gap: 6 }}>
        {STATEMENT_TYPES.map(st => (
          <TouchableOpacity
            key={st.key}
            onPress={() => setStatement(st.key)}
            style={[s.pillBtn, statement === st.key && s.pillBtnActive]}
            activeOpacity={0.7}
          >
            <Text style={[s.pillText, statement === st.key && s.pillTextActive]}>{st.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Period Selector */}
      <View className="flex-row gap-2 mb-4">
        {(['annual', 'quarter'] as const).map(p => (
          <TouchableOpacity
            key={p}
            onPress={() => setPeriod(p)}
            style={[s.periodBtn, period === p && s.periodBtnActive]}
            activeOpacity={0.7}
          >
            <Text style={[s.periodText, period === p && s.periodTextActive]}>
              {p === 'annual' ? 'Annual' : 'Quarterly'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Table */}
      <ScrollView horizontal showsHorizontalScrollIndicator>
        <View>
          {/* Column Headers */}
          <View style={ft.headerRow}>
            <View style={ft.labelCol} />
            {colLabels.map((label: string, i: number) => (
              <View key={i} style={ft.dataCol}>
                <Text style={ft.headerText}>{label}</Text>
              </View>
            ))}
          </View>

          {/* Data Rows */}
          {rows.map((row, ri) => {
            if (row.t === 's') {
              return (
                <View key={ri} style={ft.sectionRow}>
                  <Text style={ft.sectionText}>{row.label}</Text>
                </View>
              );
            }

            if (row.t === 'g') {
              const vals = columns.map((c: any) => c[row.of]);
              const hasData = vals.some((v: any) => v != null);
              if (!hasData) return null;
              return (
                <View key={ri} style={[ft.dataRow, ri % 2 === 0 && ft.stripedRow]}>
                  <View style={ft.labelCol}>
                    <Text style={[ft.labelText, { color: '#9ca3af', fontStyle: 'italic' }]}>{row.label}</Text>
                  </View>
                  {vals.map((val: any, ci: number) => {
                    const prev = columns[ci + 1]?.[row.of];
                    const growth = val != null && prev != null && prev !== 0 ? ((val - prev) / Math.abs(prev)) * 100 : null;
                    return (
                      <View key={ci} style={ft.dataCol}>
                        <Text style={[ft.cellText, growth != null && { color: growth >= 0 ? '#059669' : '#ef4444' }]}>
                          {growth != null ? `${growth >= 0 ? '+' : ''}${growth.toFixed(1)}%` : '—'}
                        </Text>
                      </View>
                    );
                  })}
                </View>
              );
            }

            if (row.t === 'm') {
              const hasData = columns.some((c: any) => c[row.num] != null && c[row.den] != null);
              if (!hasData) return null;
              return (
                <View key={ri} style={[ft.dataRow, ri % 2 === 0 && ft.stripedRow]}>
                  <View style={ft.labelCol}>
                    <Text style={[ft.labelText, { color: '#9ca3af', fontStyle: 'italic' }]}>{row.label}</Text>
                  </View>
                  {columns.map((c: any, ci: number) => {
                    const margin = c[row.num] != null && c[row.den] ? (c[row.num] / c[row.den]) * 100 : null;
                    return (
                      <View key={ci} style={ft.dataCol}>
                        <Text style={ft.cellText}>{margin != null ? `${margin.toFixed(1)}%` : '—'}</Text>
                      </View>
                    );
                  })}
                </View>
              );
            }

            // row.t === 'd'
            const vals = columns.map((c: any) => c[row.key]);
            const hasData = vals.some((v: any) => v != null);
            if (!hasData) return null;

            return (
              <View key={ri} style={[ft.dataRow, ri % 2 === 0 && ft.stripedRow]}>
                <View style={ft.labelCol}>
                  <Text style={[ft.labelText, row.indent && { paddingLeft: 10, color: '#6b7280' }]} numberOfLines={1}>
                    {row.label}
                  </Text>
                </View>
                {vals.map((val: any, ci: number) => (
                  <View key={ci} style={ft.dataCol}>
                    <Text style={ft.cellText}>{fmtCell(val, row.fmt)}</Text>
                  </View>
                ))}
              </View>
            );
          })}
        </View>
      </ScrollView>
    </View>
  );
}

const ft = StyleSheet.create({
  headerRow: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#e5e7eb', paddingBottom: 8, marginBottom: 2 },
  labelCol: { width: 140 },
  dataCol: { width: COL_W, alignItems: 'flex-end', paddingRight: 4 },
  headerText: { fontSize: 11, fontFamily: 'DMSans-Bold', color: '#6b7280', textAlign: 'right' },
  sectionRow: { paddingTop: 14, paddingBottom: 4 },
  sectionText: { fontSize: 12, fontFamily: 'DMSans-Bold', color: '#111827', textTransform: 'uppercase', letterSpacing: 0.3 },
  dataRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 7 },
  stripedRow: { backgroundColor: '#fafafa' },
  labelText: { fontSize: 12, fontFamily: 'DMSans', color: '#374151' },
  cellText: { fontSize: 12, fontFamily: 'DMSans-Medium', color: '#111827', textAlign: 'right' },
});

// ── News Tab ────────────────────────────────────────────────────────────────────

function NewsTab({ news }: { news: any[] }) {
  if (news.length === 0) {
    return (
      <View className="py-16 items-center">
        <FileText size={40} color="#d1d5db" />
        <Text style={s.emptyText}>No news available</Text>
      </View>
    );
  }

  return (
    <View className="px-4 gap-2.5">
      {news.map((item: any, i: number) => (
        <NewsCard
          key={i}
          title={item.title}
          source={item.site || item.source || ''}
          date={item.publishedDate || item.date || ''}
          url={item.url}
          image={item.image}
        />
      ))}
    </View>
  );
}

// ── Analysis Tab ────────────────────────────────────────────────────────────────

function AnalysisTab({ analyst, analysis, quote, onChat }: {
  analyst: any; analysis: any[]; quote: any; onChat: () => void;
}) {
  const [expandedNote, setExpandedNote] = useState<number | null>(null);

  return (
    <View className="px-4">
      {/* Individual Analyst Grades */}
      {analyst?.grades && analyst.grades.length > 0 && (
        <View className="mb-4">
          <SectionHeader title="Analyst Grades" />
          <View style={s.listCard}>
            {analyst.grades.slice(0, 10).map((grade: any, i: number) => {
              const isUpgrade = grade.newGrade?.toLowerCase().includes('buy') || grade.newGrade?.toLowerCase().includes('outperform');
              const isDowngrade = grade.newGrade?.toLowerCase().includes('sell') || grade.newGrade?.toLowerCase().includes('underperform');
              return (
                <View key={i} style={[s.gradeRow, i > 0 && { borderTopWidth: 1, borderTopColor: '#f3f4f6' }]}>
                  <View className="flex-1">
                    <Text style={s.gradeFirm} numberOfLines={1}>{grade.gradingCompany || grade.company || 'Unknown'}</Text>
                    <Text style={s.gradeDate}>{grade.date}</Text>
                  </View>
                  <View style={[s.gradeBadge, { backgroundColor: isUpgrade ? '#ecfdf5' : isDowngrade ? '#fef2f2' : '#f9fafb' }]}>
                    <Text style={[s.gradeText, { color: isUpgrade ? '#059669' : isDowngrade ? '#dc2626' : '#6b7280' }]}>
                      {grade.newGrade || grade.grade || '—'}
                    </Text>
                  </View>
                </View>
              );
            })}
          </View>
        </View>
      )}

      {/* AI Research Notes */}
      {analysis.length > 0 && (
        <View className="mb-4">
          <SectionHeader title="AI Research Notes" />
          {analysis.map((note: any, i: number) => (
            <TouchableOpacity
              key={i}
              onPress={() => setExpandedNote(expandedNote === i ? null : i)}
              style={[s.noteCard, { marginBottom: 8 }]}
              activeOpacity={0.7}
            >
              <Text style={s.noteTitle} numberOfLines={expandedNote === i ? undefined : 2}>
                {note.title || note.summary || 'Research Note'}
              </Text>
              {expandedNote === i && note.content && (
                <Text style={s.noteContent}>{note.content}</Text>
              )}
              <Text style={s.noteDate}>{note.created_at ? new Date(note.created_at).toLocaleDateString() : ''}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Empty state — when there are no grades and no notes, point to the
          docked "Ask anything about {symbol}" bar instead of a redundant CTA. */}
      {!(analyst?.grades?.length > 0) && analysis.length === 0 && (
        <View className="items-center pt-12 pb-6">
          <View style={s.analysisEmptyIcon}>
            <TrendingUp size={22} color="#9ca3af" />
          </View>
          <Text style={s.analysisEmptyTitle}>No analyst grades or AI notes yet</Text>
          <Text style={s.analysisEmptyDesc}>
            Ask Finch AI below for a deep-dive on this stock's fundamentals, risks, and outlook.
          </Text>
        </View>
      )}
    </View>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  companyName: { fontSize: 13, fontFamily: 'DMSans', color: '#6b7280' },
  price: { fontSize: 32, fontFamily: 'DMSans-Bold', color: '#111827' },
  exchangeLabel: { fontSize: 12, fontFamily: 'DMSans', color: '#9ca3af', marginTop: 2 },
  actionBtn: {
    flex: 1, borderRadius: 12, paddingVertical: 10,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
  },
  actionBtnText: { color: '#fff', fontSize: 13, fontFamily: 'DMSans-Medium' },
  watchlistBtn: {
    borderRadius: 12, paddingVertical: 10, paddingHorizontal: 14,
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: '#f3f4f6', backgroundColor: '#fff',
  },
  tab: { paddingBottom: 10, paddingTop: 4, position: 'relative' },
  tabText: { fontSize: 14, fontFamily: 'DMSans-Medium', color: '#9ca3af' },
  tabTextActive: { color: '#111827' },
  tabIndicator: { position: 'absolute', bottom: 0, left: 0, right: 0, height: 2, backgroundColor: '#111827', borderRadius: 1 },
  card: {
    backgroundColor: '#fff', borderRadius: 14, padding: 16,
    borderWidth: 1, borderColor: '#f3f4f6',
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.03, shadowRadius: 4, elevation: 1,
  },
  cardTitle: { fontSize: 11, fontFamily: 'DMSans-Bold', color: '#9ca3af', letterSpacing: 0.5, marginBottom: 12, textTransform: 'uppercase' },
  listCard: { backgroundColor: '#fff', borderRadius: 12, borderWidth: 1, borderColor: '#f3f4f6', overflow: 'hidden' },
  statLabel: { fontSize: 11, fontFamily: 'DMSans', color: '#9ca3af' },
  statValue: { fontSize: 13, fontFamily: 'DMSans-Medium', color: '#111827', marginTop: 1 },
  infoValue: { fontSize: 13, fontFamily: 'DMSans', color: '#374151', marginTop: 1 },
  rangeLabel: { fontSize: 11, fontFamily: 'DMSans', color: '#9ca3af', width: 52 },
  rangeTrack: { flex: 1, height: 4, backgroundColor: '#f3f4f6', borderRadius: 2, position: 'relative' },
  rangeFill: { position: 'absolute', top: 0, left: 0, height: 4, backgroundColor: '#059669', borderRadius: 2 },
  rangeDot: { position: 'absolute', top: -4, width: 12, height: 12, borderRadius: 6, backgroundColor: '#059669', marginLeft: -6, borderWidth: 2, borderColor: '#fff' },
  targetPrice: { fontSize: 14, fontFamily: 'DMSans-Bold', color: '#111827', marginTop: 2 },
  targetTrack: { height: 6, backgroundColor: '#f3f4f6', borderRadius: 3, marginVertical: 8, position: 'relative' },
  targetBar: { position: 'absolute', top: 0, left: '10%', right: '10%', height: 6, backgroundColor: '#d1d5db', borderRadius: 3 },
  targetCurrentDot: { position: 'absolute', top: -6, width: 18, height: 18, borderRadius: 9, backgroundColor: '#111827', borderWidth: 2, borderColor: '#fff', alignItems: 'center', justifyContent: 'center', marginLeft: -9 },
  targetCurrentLabel: { fontSize: 6, fontFamily: 'DMSans-Bold', color: '#fff' },
  upsideText: { fontSize: 12, fontFamily: 'DMSans-Medium', color: '#059669', textAlign: 'center', marginTop: 4 },
  ratingLabel: { fontSize: 11, fontFamily: 'DMSans', color: '#6b7280' },
  peerRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 10 },
  peerSymbol: { fontSize: 14, fontFamily: 'DMSans-Bold', color: '#111827' },
  peerName: { fontSize: 12, fontFamily: 'DMSans', color: '#9ca3af', marginTop: 1 },
  peerPrice: { fontSize: 14, fontFamily: 'DMSans-Medium', color: '#111827' },
  peerChange: { fontSize: 11, fontFamily: 'DMSans', marginTop: 1 },
  aboutText: { fontSize: 13, fontFamily: 'DMSans', color: '#6b7280', lineHeight: 19 },
  emptyText: { fontSize: 13, fontFamily: 'DMSans', color: '#9ca3af', marginTop: 12 },
  miniStat: { flex: 1, backgroundColor: '#f9fafb', borderRadius: 12, padding: 14, alignItems: 'center' },
  miniStatValue: { fontSize: 18, fontFamily: 'DMSans-Bold', color: '#111827' },
  miniStatLabel: { fontSize: 11, fontFamily: 'DMSans', color: '#9ca3af', marginTop: 2 },
  tableHeader: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, backgroundColor: '#f9fafb', borderBottomWidth: 1, borderBottomColor: '#f3f4f6' },
  tableHeaderText: { fontSize: 11, fontFamily: 'DMSans-Bold', color: '#6b7280' },
  tableRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 10 },
  tableCell: { fontSize: 13, fontFamily: 'DMSans', color: '#374151' },
  financialPeriod: { fontSize: 13, fontFamily: 'DMSans-Bold', color: '#111827', marginBottom: 8 },
  pillBtn: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20, backgroundColor: '#f3f4f6' },
  pillBtnActive: { backgroundColor: '#111827' },
  pillText: { fontSize: 13, fontFamily: 'DMSans-Medium', color: '#6b7280' },
  pillTextActive: { color: '#fff' },
  periodBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8, backgroundColor: '#f9fafb' },
  periodBtnActive: { backgroundColor: '#111827' },
  periodText: { fontSize: 12, fontFamily: 'DMSans-Medium', color: '#9ca3af' },
  periodTextActive: { color: '#fff' },
  gradeRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 10 },
  gradeFirm: { fontSize: 13, fontFamily: 'DMSans-Medium', color: '#111827' },
  gradeDate: { fontSize: 11, fontFamily: 'DMSans', color: '#9ca3af', marginTop: 1 },
  gradeBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6 },
  gradeText: { fontSize: 11, fontFamily: 'DMSans-Medium' },
  noteCard: { backgroundColor: '#f9fafb', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#f3f4f6' },
  noteTitle: { fontSize: 14, fontFamily: 'DMSans-Medium', color: '#111827', lineHeight: 20 },
  noteContent: { fontSize: 13, fontFamily: 'DMSans', color: '#6b7280', lineHeight: 19, marginTop: 8 },
  noteDate: { fontSize: 11, fontFamily: 'DMSans', color: '#d1d5db', marginTop: 6 },
  aiCta: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#ecfdf5',
    borderRadius: 14, padding: 16, borderWidth: 1, borderColor: '#d1fae5',
  },
  aiCtaTitle: { fontSize: 14, fontFamily: 'DMSans-Bold', color: '#111827' },
  aiCtaDesc: { fontSize: 12, fontFamily: 'DMSans', color: '#6b7280', lineHeight: 17, marginTop: 2 },
  aiCtaBtn: { backgroundColor: '#059669', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8 },
  aiCtaBtnText: { fontSize: 12, fontFamily: 'DMSans-Medium', color: '#fff' },
  analysisEmptyIcon: {
    width: 48, height: 48, borderRadius: 24, backgroundColor: '#f3f4f6',
    alignItems: 'center', justifyContent: 'center', marginBottom: 12,
  },
  analysisEmptyTitle: { fontSize: 15, fontFamily: 'DMSans-Bold', color: '#111827' },
  analysisEmptyDesc: {
    fontSize: 13, fontFamily: 'DMSans', color: '#9ca3af', textAlign: 'center',
    lineHeight: 18, marginTop: 4, paddingHorizontal: 24,
  },
});
