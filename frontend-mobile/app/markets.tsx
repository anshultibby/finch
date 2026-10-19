import React, { useCallback, useEffect, useState } from 'react';
import { StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { marketApi } from '@/lib/api';
import ScreenHeader from '@/components/ui/ScreenHeader';
import { MarketsTab, MARKET_INDICES, type MarketRegion } from '@/components/home/sections';

// The full market view behind the home pulse strip: indices, movers, news.
export default function MarketsScreen() {
  const router = useRouter();
  const [region, setRegion] = useState<MarketRegion>('us');
  const [quotes, setQuotes] = useState<Record<string, any>>({});
  const [movers, setMovers] = useState<any>(null);
  const [news, setNews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(() => new Date().toISOString());

  const load = useCallback(async () => {
    const [moversData, newsData, batch] = await Promise.all([
      marketApi.getMovers().catch(() => null),
      marketApi.getGeneralNews(8, region).catch(() => []),
      marketApi.getBatchQuotes(MARKET_INDICES[region].map(i => i.symbol)).catch(() => null),
    ]);
    if (moversData) setMovers(moversData);
    setNews(newsData?.news || newsData || []);
    setError(batch === null && !moversData);
    if (Array.isArray(batch)) {
      const m: Record<string, any> = {};
      batch.forEach((q: any) => { if (q?.symbol) m[q.symbol] = q; });
      setQuotes(m);
    }
    setUpdatedAt(new Date().toISOString());
    setLoading(false);
  }, [region]);

  useEffect(() => { load(); }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScreenHeader title="Markets" />
      <MarketsTab
        gainers={movers?.gainers?.slice(0, 8) || []}
        losers={movers?.losers?.slice(0, 8) || []}
        actives={movers?.most_active?.slice(0, 8) || []}
        news={news}
        loading={loading}
        error={error}
        refreshing={refreshing}
        onRefresh={onRefresh}
        onStockPress={(s) => router.push(`/stock/${s}`)}
        marketRegion={region}
        onRegionChange={(r) => { setRegion(r); setLoading(true); }}
        indexQuotes={quotes}
        updatedAt={updatedAt}
        showBriefing={false}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({ safe: { flex: 1, backgroundColor: '#fafaf9' } });
