import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, TouchableOpacity, Animated } from 'react-native';
import * as Haptics from 'expo-haptics';
import { pendingTradesApi, PendingTradeItem } from '@/lib/api';

const HOLD_MS = 1100;

/**
 * The approval moment. A proposed trade rendered as a deliberate decision:
 * exact order terms, a live expiry countdown, and hold-to-approve — approving
 * is a physical act, not a tap the user might not remember making.
 */
export default function ApprovalCard({
  trade,
  onDecided,
}: {
  trade: PendingTradeItem;
  onDecided: (id: string, status: 'approved' | 'rejected' | 'expired') => void;
}) {
  const [busy, setBusy] = useState<'approving' | 'rejecting' | null>(null);
  const [holding, setHolding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const fill = useRef(new Animated.Value(0)).current;
  const holdAnim = useRef<Animated.CompositeAnimation | null>(null);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const p = trade.order_params || {};
  const symbol = String(p.symbol || '').toUpperCase();
  const side = String(p.side || '').toLowerCase();

  const expiresMs = trade.expires_at ? new Date(trade.expires_at).getTime() - now : Infinity;
  const expired = expiresMs <= 0;
  const mins = Math.max(0, Math.floor(expiresMs / 60000));
  const countdown = expiresMs === Infinity ? '' :
    mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` :
    mins >= 1 ? `${mins}m ${Math.floor((expiresMs % 60000) / 1000)}s` :
    `${Math.max(0, Math.floor(expiresMs / 1000))}s`;

  const approve = useCallback(async () => {
    setBusy('approving');
    setError(null);
    try {
      await pendingTradesApi.approve(trade.id);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      onDecided(trade.id, 'approved');
    } catch (e: any) {
      if (e?.response?.status === 410) { onDecided(trade.id, 'expired'); return; }
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      // The backend marks the trade failed on a placement error — terminal.
      setFailed(e?.response?.data?.detail || 'Order could not be placed.');
      setBusy(null);
    }
  }, [trade.id, onDecided]);

  const startHold = useCallback(() => {
    if (busy || expired) return;
    setHolding(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    holdAnim.current = Animated.timing(fill, {
      toValue: 1, duration: HOLD_MS, useNativeDriver: false,
    });
    holdAnim.current.start(({ finished }) => {
      setHolding(false);
      fill.setValue(0);
      if (finished) void approve();
    });
  }, [busy, expired, approve, fill]);

  const cancelHold = useCallback(() => {
    holdAnim.current?.stop();
    setHolding(false);
    fill.setValue(0);
  }, [fill]);

  const reject = useCallback(async () => {
    setBusy('rejecting');
    setError(null);
    try {
      await pendingTradesApi.reject(trade.id);
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      onDecided(trade.id, 'rejected');
    } catch {
      setError('Could not reject — try again.');
      setBusy(null);
    }
  }, [trade.id, onDecided]);

  if (failed) {
    return (
      <View className="rounded-2xl border border-red-100 bg-red-50 p-4 mb-3">
        <Text className="text-sm font-body-bold text-red-700 mb-1">Order couldn&apos;t be placed — no trade happened.</Text>
        <Text className="text-xs font-body text-red-600 mb-1">{failed}</Text>
        <Text className="text-xs font-body text-gray-500">{trade.summary} · Ask Finch to re-propose once fixed.</Text>
      </View>
    );
  }

  if (expired) {
    return (
      <View className="rounded-2xl border border-gray-200 bg-gray-50 p-4 mb-3">
        <Text className="text-xs font-body text-gray-500">
          Proposal expired — no trade was placed. <Text className="font-body-bold text-gray-700">{trade.summary}</Text>
        </Text>
      </View>
    );
  }

  const rows: [string, string][] = [];
  if (side) rows.push(['Side', side.toUpperCase()]);
  if (p.quantity) rows.push(['Quantity', `${p.quantity} shares`]);
  if (p.dollar_amount) rows.push(['Amount', `$${Number(p.dollar_amount).toLocaleString()}`]);
  rows.push(['Order type', String(p.type || 'market')]);
  if (p.limit_price) rows.push(['Limit price', `$${Number(p.limit_price).toFixed(2)}`]);

  return (
    <View className="rounded-2xl border border-emerald-200 bg-white mb-3 overflow-hidden">
      <View className="flex-row items-center justify-between px-4 py-2 bg-emerald-50 border-b border-emerald-100">
        <Text className="text-[10px] font-body-bold text-emerald-700 uppercase tracking-widest">
          Trade proposal · needs approval
        </Text>
        <Text className={`text-[10px] font-body-bold ${mins < 5 ? 'text-red-600' : 'text-emerald-700/70'}`}>
          expires in {countdown}
        </Text>
      </View>

      <View className="p-4">
        <View className="flex-row items-center mb-1.5" style={{ gap: 8 }}>
          <Text className="text-lg font-body-bold text-gray-900">{symbol || 'Order'}</Text>
          {!!side && (
            <View className={`px-1.5 py-0.5 rounded ${side === 'buy' ? 'bg-emerald-100' : 'bg-amber-100'}`}>
              <Text className={`text-[10px] font-body-bold uppercase ${side === 'buy' ? 'text-emerald-700' : 'text-amber-700'}`}>
                {side}
              </Text>
            </View>
          )}
        </View>
        {!!trade.summary && (
          <Text className="text-sm font-body text-gray-700 mb-3">{trade.summary}</Text>
        )}

        <View className="mb-4">
          {rows.map(([k, v]) => (
            <View key={k} className="flex-row justify-between py-1 border-b border-dashed border-gray-100">
              <Text className="text-xs font-body text-gray-400">{k}</Text>
              <Text className="text-xs font-body-bold text-gray-800">{v}</Text>
            </View>
          ))}
        </View>

        {!!error && <Text className="text-xs font-body text-red-600 mb-3">{error}</Text>}

        <View className="flex-row items-center" style={{ gap: 8 }}>
          <Pressable
            onPressIn={startHold}
            onPressOut={cancelHold}
            disabled={!!busy}
            className={`flex-1 h-12 rounded-xl bg-emerald-600 overflow-hidden items-center justify-center ${busy ? 'opacity-60' : ''}`}
          >
            <Animated.View
              className="absolute left-0 top-0 bottom-0 bg-emerald-800"
              style={{
                width: fill.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] }),
              }}
            />
            <Text className="text-sm font-body-bold text-white">
              {busy === 'approving' ? 'Placing order…' : holding ? 'Keep holding…' : 'Hold to approve'}
            </Text>
          </Pressable>
          <TouchableOpacity
            onPress={reject}
            disabled={!!busy}
            className={`h-12 px-4 rounded-xl border border-gray-200 items-center justify-center ${busy ? 'opacity-60' : ''}`}
          >
            <Text className="text-sm font-body-bold text-gray-600">
              {busy === 'rejecting' ? 'Rejecting…' : 'Reject'}
            </Text>
          </TouchableOpacity>
        </View>
        <Text className="text-[10px] font-body text-gray-400 mt-2">
          Nothing is placed until you approve. If it expires, no trade happens.
        </Text>
      </View>
    </View>
  );
}
