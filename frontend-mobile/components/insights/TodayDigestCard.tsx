import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Sparkles } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { useRouter } from 'expo-router';
import { insightsApi, PortfolioDigest } from '@/lib/api';
import { Skeleton } from '@/components/ui/Skeleton';

interface TodayDigestCardProps {
  userId: string;
}

/**
 * The generated "Today" story for the user's portfolio (or watchlist when no
 * brokerage is connected): day P&L, an AI narrative of what drove it, and
 * mover chips that deep-link to each stock.
 */
export default function TodayDigestCard({ userId }: TodayDigestCardProps) {
  const router = useRouter();
  const [digest, setDigest] = useState<PortfolioDigest | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    insightsApi
      .getPortfolioDigest(userId)
      .then(d => { if (!cancelled) setDigest(d); })
      .catch(() => { if (!cancelled) setDigest(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [userId]);

  if (loading) {
    return (
      <View className="mb-4 rounded-2xl bg-white border border-gray-100 p-4">
        <View className="flex-row items-center mb-2.5" style={{ gap: 5 }}>
          <Sparkles size={12} color="#059669" />
          <Text className="text-[11px] font-body-bold text-gray-400 uppercase tracking-wide">Today</Text>
        </View>
        <View style={{ gap: 8 }}>
          <Skeleton width="100%" height={12} radius={4} />
          <Skeleton width="80%" height={12} radius={4} />
        </View>
      </View>
    );
  }

  if (!digest || !digest.success || digest.mode === 'empty' || !digest.narrative) {
    return null;
  }

  const isPortfolio = digest.mode === 'portfolio';
  const dayChange = digest.day_change ?? 0;
  const dayUp = dayChange >= 0;

  return (
    <View className="mb-4 rounded-2xl bg-white border border-gray-100 p-4">
      <View className="flex-row items-center justify-between mb-2">
        <View className="flex-row items-center" style={{ gap: 5 }}>
          <Sparkles size={12} color="#059669" />
          <Text className="text-[11px] font-body-bold text-gray-400 uppercase tracking-wide">
            {isPortfolio ? 'Today' : 'Your watchlist today'}
          </Text>
        </View>
        {isPortfolio && (
          <Text
            className="text-[13px] font-body-bold tabular-nums"
            style={{ color: dayUp ? '#059669' : '#dc2626' }}
          >
            {dayUp ? '+' : '-'}${Math.abs(dayChange).toLocaleString(undefined, { maximumFractionDigits: 0 })}
            {' '}({dayUp ? '+' : ''}{(digest.day_change_pct ?? 0).toFixed(2)}%)
          </Text>
        )}
      </View>

      <Text className="text-[13.5px] font-body text-gray-700 leading-5">{digest.narrative}</Text>

      {(digest.movers?.length ?? 0) > 0 && (
        <View className="flex-row flex-wrap mt-3" style={{ gap: 6 }}>
          {digest.movers!.map(m => {
            const up = m.change_pct >= 0;
            return (
              <TouchableOpacity
                key={m.symbol}
                onPress={() => {
                  Haptics.selectionAsync();
                  router.push(`/stock/${m.symbol}`);
                }}
                activeOpacity={0.7}
                className="flex-row items-center rounded-full border border-gray-200 bg-white px-2.5 py-1"
                style={{ gap: 5 }}
              >
                <Text className="text-[12px] font-body-bold text-gray-900">{m.symbol}</Text>
                <Text
                  className="text-[12px] font-body tabular-nums"
                  style={{ color: up ? '#059669' : '#dc2626' }}
                >
                  {up ? '+' : ''}{m.change_pct.toFixed(1)}%
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      )}
    </View>
  );
}
