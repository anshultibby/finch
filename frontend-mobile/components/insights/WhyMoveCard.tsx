import React, { useState } from 'react';
import { View, Text, TouchableOpacity, Linking } from 'react-native';
import { Sparkles, ChevronDown, ChevronUp } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { insightsApi, MoveExplanation, VERDICT_META, DRIVER_LABEL, type MoveContext } from '@/lib/api';
import { Skeleton } from '@/components/ui/Skeleton';

interface WhyMoveCardProps {
  symbol: string;
  /** Sign of today's move, used to tint the pill. */
  changePct?: number | null;
}

/**
 * Tap-to-explain pill for a stock's move today. Expands inline into Finch's
 * read: is this routine, news with the story intact, or a narrative change —
 * and is it macro, sector or the company? The measured numbers behind the call
 * (vs its typical move, market, sector, volume) sit under the explanation.
 */
export default function WhyMoveCard({ symbol, changePct }: WhyMoveCardProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<MoveExplanation | null>(null);
  const [error, setError] = useState(false);

  const positive = (changePct ?? 0) >= 0;
  const tint = positive ? '#059669' : '#dc2626';
  const tintBg = positive ? '#ecfdf5' : '#fef2f2';

  const toggle = async () => {
    Haptics.selectionAsync();
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (data || loading) return;
    setLoading(true);
    setError(false);
    try {
      setData(await insightsApi.whyIsItMoving(symbol));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      <TouchableOpacity
        onPress={toggle}
        activeOpacity={0.7}
        className="flex-row items-center self-start rounded-full px-2.5 py-1 mt-2"
        style={{ backgroundColor: open ? '#111827' : tintBg }}
      >
        <Sparkles size={11} color={open ? '#ffffff' : tint} />
        <Text
          className="text-[12px] font-body-medium ml-1"
          style={{ color: open ? '#ffffff' : tint }}
        >
          Why is it moving?
        </Text>
        {open
          ? <ChevronUp size={12} color="#ffffff" style={{ marginLeft: 3 }} />
          : <ChevronDown size={12} color={tint} style={{ marginLeft: 3 }} />}
      </TouchableOpacity>

      {open && (
        <View className="mt-2 rounded-xl bg-white border border-gray-100 p-3">
          {loading && (
            <View style={{ gap: 8 }}>
              <Skeleton width="100%" height={12} radius={4} />
              <Skeleton width="70%" height={12} radius={4} />
            </View>
          )}
          {error && !loading && (
            <Text className="text-[13px] font-body text-gray-500">
              Couldn&apos;t generate an explanation right now.
            </Text>
          )}
          {data && !loading && (
            <>
              {data.verdict && (
                <View className="flex-row items-center mb-1.5" style={{ gap: 6 }}>
                  <View className="rounded-md px-1.5 py-0.5" style={{ backgroundColor: VERDICT_META[data.verdict].bg }}>
                    <Text className="text-[11px] font-body-bold" style={{ color: VERDICT_META[data.verdict].fg }}>
                      {VERDICT_META[data.verdict].label}
                    </Text>
                  </View>
                  {data.driver && (
                    <Text className="text-[11px] font-body-medium text-gray-400">{DRIVER_LABEL[data.driver]}</Text>
                  )}
                </View>
              )}
              {!!data.headline && (
                <Text className="text-[14px] font-body-bold text-gray-900 leading-5 mb-1">{data.headline}</Text>
              )}
              <Text className="text-[13px] font-body text-gray-800 leading-5">
                {data.explanation}
              </Text>
              {data.context && <MeasuredStrip ctx={data.context} />}
              {!!data.watch && (
                <Text className="text-[12.5px] font-body text-gray-600 leading-5 mt-2">
                  <Text className="font-body-bold text-gray-900">Watch: </Text>{data.watch}
                </Text>
              )}
              {data.sources[0] && (
                <TouchableOpacity
                  onPress={() => data.sources[0].url && Linking.openURL(data.sources[0].url)}
                  activeOpacity={0.7}
                  className="mt-2 pt-2 border-t border-gray-100"
                >
                  <Text className="text-[11px] font-body text-gray-400" numberOfLines={1}>
                    {data.sources[0].site ? `${data.sources[0].site} · ` : ''}
                    {data.sources[0].title}
                  </Text>
                </TouchableOpacity>
              )}
            </>
          )}
        </View>
      )}
    </View>
  );
}

/** The numbers behind the verdict: how unusual, and how much is market/sector. */
function MeasuredStrip({ ctx }: { ctx: MoveContext }) {
  const pct = (n: number | null) => (n == null ? null : `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`);
  const items = [
    ctx.move_multiple != null ? `${ctx.move_multiple}× its typical move` : null,
    pct(ctx.spy_change_pct) ? `Market ${pct(ctx.spy_change_pct)}` : null,
    pct(ctx.sector_change_pct) ? `${ctx.sector_etf || 'Sector'} ${pct(ctx.sector_change_pct)}` : null,
    ctx.volume_ratio != null ? `Volume ${ctx.volume_ratio}×` : null,
    ctx.earnings,
  ].filter(Boolean) as string[];
  if (!items.length) return null;
  return (
    <View className="flex-row flex-wrap mt-2" style={{ gap: 6 }}>
      {items.map(t => (
        <View key={t} className="rounded-md bg-stone-100 px-1.5 py-0.5">
          <Text className="text-[11px] font-body-medium text-stone-600">{t}</Text>
        </View>
      ))}
    </View>
  );
}
