import { View, Text, Pressable, ActivityIndicator, ScrollView, Linking } from 'react-native';
import { useRouter } from 'expo-router';
import { Sparkles } from 'lucide-react-native';
import { robinhoodApi, type RobinhoodPortfolioResponse } from '@/lib/api';
import { useCachedResource } from '@/hooks/useCachedResource';

function usd(v?: string | number | null): string {
  if (v == null) return '—';
  const n = Number(v);
  return Number.isNaN(n) ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(n);
}
function signed(n: number): string {
  const s = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Math.abs(n));
  return `${n >= 0 ? '+' : '−'}${s}`;
}
function timeAgo(iso?: string): string {
  if (!iso) return '';
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

export default function AgentTabView({ userId }: { userId: string }) {
  const router = useRouter();

  // Cached so returning to the Agent tab shows the last portfolio instantly and
  // only revalidates in the background, instead of re-fetching from a spinner.
  const { data, error, isLoading, refresh } = useCachedResource<RobinhoodPortfolioResponse>(
    userId ? `rh-portfolio:${userId}` : null,
    () => robinhoodApi.getPortfolio(userId),
    { ttl: 30_000 },
  );

  if (isLoading) {
    return <View className="py-16 items-center"><ActivityIndicator color="#10b981" /></View>;
  }
  if (error && !data) {
    return (
      <View className="py-12 items-center">
        <Text className="text-sm text-red-500">Couldn’t load the agent portfolio.</Text>
        <Pressable onPress={() => refresh()} className="mt-2"><Text className="text-sm text-emerald-600 underline">Retry</Text></Pressable>
      </View>
    );
  }

  if (!data?.is_connected || !data.agentic_account) {
    return (
      <View className="mt-8 mx-2 rounded-2xl border border-gray-200 p-7 items-center">
        <View className="h-12 w-12 rounded-xl items-center justify-center mb-3" style={{ backgroundColor: '#10b981' }}>
          <Sparkles size={22} color="#fff" />
        </View>
        <Text className="text-base font-semibold text-gray-900">Your AI Trading Agent</Text>
        <Text className="mt-1.5 text-sm text-gray-500 text-center">Connect a Robinhood Agentic account to let Finch trade for you — in its own account, with your limits.</Text>
        <Text className="mt-4 text-[11px] text-gray-400 text-center">🔒 Robinhood only allows trading approval from an app on your desktop. Open Finch Connect on your computer to link it.</Text>
      </View>
    );
  }

  const { holdings, orders, total_value, buying_power, agentic_account } = data;
  const totalUnrealized = holdings.reduce((s, h) => s + h.unrealized_pl, 0);
  const col = (n: number) => (n >= 0 ? '#059669' : '#ef4444');

  return (
    <ScrollView className="px-1" showsVerticalScrollIndicator={false}>
      {/* Headline */}
      <View className="rounded-2xl border border-emerald-100 p-5 mb-4" style={{ backgroundColor: '#ecfdf5' }}>
        <View className="flex-row items-center gap-1.5">
          <View className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: '#10b981' }} />
          <Text className="text-[11px] font-medium text-emerald-600">AI Trading Agent · Agentic ••{agentic_account.account_number.slice(-4)}</Text>
        </View>
        <View className="flex-row items-end justify-between mt-1">
          <View>
            <Text className="text-3xl font-bold text-gray-900">{usd(total_value)}</Text>
            <Text className="mt-0.5 text-sm font-semibold" style={{ color: col(totalUnrealized) }}>{signed(totalUnrealized)} unrealized</Text>
          </View>
          <View className="items-end">
            <Text className="text-xs text-gray-400">Buying power</Text>
            <Text className="text-sm font-semibold text-gray-700">{usd(buying_power)}</Text>
          </View>
        </View>
      </View>

      {/* Holdings */}
      <View className="rounded-2xl border border-gray-200 mb-4">
        <Text className="px-4 py-3 text-sm font-semibold text-gray-900 border-b border-gray-100">Holdings ({holdings.length})</Text>
        {holdings.length === 0 ? (
          <Text className="px-4 py-8 text-center text-sm text-gray-400">No open positions yet.</Text>
        ) : holdings.map((h) => (
          <Pressable key={h.symbol} onPress={() => router.push(`/stock/${h.symbol}`)}
            className="flex-row items-center justify-between px-4 py-3 border-b border-gray-50 active:bg-gray-50">
            <View>
              <Text className="text-sm font-semibold text-gray-900">{h.symbol}</Text>
              <Text className="text-[11px] text-gray-400">{h.quantity} sh · avg {usd(h.average_buy_price)}</Text>
            </View>
            <View className="items-end">
              <Text className="text-sm font-semibold text-gray-900">{usd(h.market_value)}</Text>
              <Text className="text-[11px] font-medium" style={{ color: col(h.unrealized_pl) }}>
                {signed(h.unrealized_pl)} ({h.unrealized_pct >= 0 ? '+' : ''}{h.unrealized_pct}%)
              </Text>
            </View>
          </Pressable>
        ))}
      </View>

      {/* Recent trades */}
      <View className="rounded-2xl border border-gray-200 mb-3">
        <Text className="px-4 py-3 text-sm font-semibold text-gray-900 border-b border-gray-100">Recent trades</Text>
        {orders.length === 0 ? (
          <Text className="px-4 py-8 text-center text-sm text-gray-400">No trades yet.</Text>
        ) : orders.map((o, i) => (
          <View key={i} className="flex-row items-center px-4 py-2.5 border-b border-gray-50">
            <Text className="text-xs font-bold mr-2" style={{ color: o.side === 'sell' ? '#ef4444' : '#059669' }}>{o.side === 'sell' ? '▼' : '▲'}</Text>
            <Text className="text-sm text-gray-700">{o.side === 'sell' ? 'Sold' : 'Bought'} {Number(o.quantity).toLocaleString()} {o.symbol}</Text>
            <Text className="ml-auto text-sm text-gray-500">{usd(o.price)}</Text>
            <Text className="w-10 text-right text-[11px] text-gray-400">{timeAgo(o.at)}</Text>
          </View>
        ))}
      </View>

      <Text className="px-2 pb-4 text-center text-[11px] text-gray-400">The agent trades only in this Agentic account — never your main accounts.</Text>
    </ScrollView>
  );
}
