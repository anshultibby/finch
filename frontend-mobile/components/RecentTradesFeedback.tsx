import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { ChevronRight } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { useAuth } from '@/contexts/AuthContext';
import { tradesApi, chatApi, type RecentTrade } from '@/lib/api';
import { formatCurrency } from '@/lib/constants';

function fmtDate(iso: string | null): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

// Seeded into a fresh chat when a trade is tapped. The agent already gets the
// user's goal injected, so "against my goal" reinforces the framing.
function reviewPrompt(t: RecentTrade): string {
  const action = t.side === 'BUY' ? 'bought' : 'sold';
  const price = formatCurrency(t.price, false, t.symbol);
  const amount = formatCurrency(t.amount, false, t.symbol);
  return `I ${action} ${t.quantity} shares of ${t.symbol} at ${price} on ${fmtDate(t.date)} (~${amount}). `
    + `Review this trade against my goal — was the entry, timing, and sizing sound? `
    + `Then suggest 2-3 concrete alternatives I could act on now, with the reasoning.`;
}

export default function RecentTradesFeedback({ onConnect }: { onConnect?: () => void }) {
  const router = useRouter();
  const { user } = useAuth();
  const [trades, setTrades] = useState<RecentTrade[] | null>(null);
  const [connected, setConnected] = useState(true);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) { setLoading(false); return; }
    let alive = true;
    tradesApi.getRecent(5)
      .then((r) => { if (!alive) return; setConnected(r.connected); setTrades(r.trades || []); })
      .catch(() => { if (alive) setTrades([]); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [user]);

  const openReview = async (t: RecentTrade) => {
    if (!user || busy) return;
    setBusy(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(`/(tabs)/chat/${chatId}?seed=${encodeURIComponent(reviewPrompt(t))}`);
    } catch {
      // swallow — the AskBar flow does the same; a failed nav shouldn't crash home
    } finally {
      setBusy(false);
    }
  };

  if (loading || !user) return null;

  if (!connected) {
    return (
      <View className="mx-4 mb-3">
        <Text className="text-[13px] font-body-bold text-gray-900 mb-1.5">Trade feedback</Text>
        <View className="rounded-xl border border-gray-100 bg-white px-3.5 py-3">
          <Text className="text-[13px] font-body text-gray-600">
            Connect your brokerage and Finch will review your recent trades and suggest better alternatives.
          </Text>
          {onConnect && (
            <TouchableOpacity
              onPress={onConnect}
              activeOpacity={0.85}
              className="mt-3 rounded-lg bg-emerald-600 py-2.5 items-center"
            >
              <Text className="text-[13px] font-body-bold text-white">Connect brokerage</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    );
  }

  if (!trades || trades.length === 0) return null;

  return (
    <View className="mx-4 mb-3">
      <Text className="text-[13px] font-body-bold text-gray-900 mb-0.5">Review a recent trade</Text>
      <Text className="text-[11px] font-body text-gray-400 mb-2">
        Tap a trade — Finch critiques it and suggests alternatives.
      </Text>
      <View style={{ gap: 8 }}>
        {trades.map((t) => (
          <TouchableOpacity
            key={t.id}
            onPress={() => openReview(t)}
            disabled={busy}
            activeOpacity={0.7}
            className="flex-row items-center justify-between rounded-xl border border-gray-100 bg-white px-3.5 py-2.5"
          >
            <View className="flex-row items-center flex-1 mr-3" style={{ gap: 8 }}>
              <View className={`px-1.5 py-0.5 rounded ${t.side === 'BUY' ? 'bg-emerald-50' : 'bg-rose-50'}`}>
                <Text className={`text-[11px] font-body-bold ${t.side === 'BUY' ? 'text-emerald-700' : 'text-rose-700'}`}>
                  {t.side}
                </Text>
              </View>
              <Text className="text-[14px] font-body-bold text-gray-900">{t.symbol}</Text>
              <Text className="text-[12px] font-body text-gray-400" numberOfLines={1}>
                {t.quantity} sh · {fmtDate(t.date)}
              </Text>
            </View>
            <View className="flex-row items-center" style={{ gap: 4 }}>
              <Text className="text-[13px] font-body-medium text-gray-600 tabular-nums">
                {formatCurrency(t.amount, true, t.symbol)}
              </Text>
              <ChevronRight size={14} color="#9ca3af" />
            </View>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}
