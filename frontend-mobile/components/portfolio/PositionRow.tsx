import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import PriceChange from '@/components/ui/PriceChange';
import { formatCurrency } from '@/lib/constants';

interface PositionRowProps {
  symbol: string;
  qty: string;
  avgEntry: string;
  marketValue: string;
  unrealizedPl: string;
  unrealizedPlPc: string;
  currentPrice: string;
  onPress: () => void;
  isLast?: boolean;
}

export default function PositionRow({ symbol, qty, avgEntry, marketValue, unrealizedPl, unrealizedPlPc, currentPrice, onPress, isLast }: PositionRowProps) {
  const pl = parseFloat(unrealizedPl || '0');
  const plPct = parseFloat(unrealizedPlPc || '0') * 100;
  const mv = parseFloat(marketValue || '0');

  return (
    <TouchableOpacity
      onPress={onPress}
      className={`px-3.5 py-3 ${!isLast ? 'border-b border-gray-100' : ''}`}
      activeOpacity={0.6}
    >
      <View className="flex-row items-center justify-between">
        <View className="flex-1">
          <Text className="text-[14px] font-body-bold text-gray-900">{symbol}</Text>
          <Text className="text-[12px] font-body text-gray-500 mt-px">
            {parseFloat(qty).toFixed(qty.includes('.') ? 4 : 0)} shares @ {formatCurrency(parseFloat(avgEntry), false, symbol)}
          </Text>
        </View>
        <View className="items-end">
          <Text className="text-[14px] font-body-medium text-gray-900 tabular-nums">
            {formatCurrency(mv, false, symbol)}
          </Text>
          <PriceChange value={pl} percent={plPct} showDollar size="sm" />
        </View>
      </View>
    </TouchableOpacity>
  );
}
