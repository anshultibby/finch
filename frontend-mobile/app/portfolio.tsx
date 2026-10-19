import React, { useCallback, useState } from 'react';
import { StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { snaptradeApi } from '@/lib/api';
import type { SnapTradeStatusResponse } from '@/lib/types';
import ScreenHeader from '@/components/ui/ScreenHeader';
import SignInPrompt from '@/components/SignInPrompt';
import { PortfolioTab } from '@/components/home/sections';

// Your book: connected brokerage holdings (SnapTrade, read-only) + the agent card.
export default function PortfolioScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [isConnected, setIsConnected] = useState(false);
  const [reverify, setReverify] = useState<SnapTradeStatusResponse | null>(null);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [performance, setPerformance] = useState<any>(null);
  const [brokerages, setBrokerages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

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
        setAccounts(accts.accounts || []);
      }
    } catch {} finally {
      setLoading(false);
    }
  }, [user]);

  useFocusEffect(useCallback(() => { fetchPortfolio(); }, [fetchPortfolio]));

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchPortfolio();
    setRefreshing(false);
  }, [fetchPortfolio]);

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScreenHeader title="Your book" subtitle={isConnected ? 'Read-only brokerage sync' : undefined} />
      {user ? (
        <PortfolioTab
          isConnected={isConnected}
          reverify={reverify}
          portfolioData={portfolioData}
          accounts={accounts}
          performance={performance}
          brokerages={brokerages}
          loading={loading}
          refreshing={refreshing}
          onRefresh={onRefresh}
          onStockPress={(s) => router.push(`/stock/${s}`)}
          userId={user.id}
          onConnectionChange={fetchPortfolio}
          onStartWatchlist={() => router.push('/watchlist')}
        />
      ) : (
        <SignInPrompt
          title="See your portfolio in one place"
          description="Sign in to securely connect your brokerage and track holdings, performance, and trades."
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({ safe: { flex: 1, backgroundColor: '#fafaf9' } });
