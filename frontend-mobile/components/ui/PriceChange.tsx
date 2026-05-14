import React from 'react';
import { View, Text } from 'react-native';
import { TrendingUp, TrendingDown } from 'lucide-react-native';
import { COLORS, formatPct, formatCurrency } from '@/lib/constants';

interface PriceChangeProps {
  value: number;
  percent?: number;
  showIcon?: boolean;
  showDollar?: boolean;
  size?: 'sm' | 'md' | 'lg';
  stockSymbol?: string;
}

const sizeMap = {
  sm: { text: 'text-[11px]', icon: 9 },
  md: { text: 'text-[13px]', icon: 11 },
  lg: { text: 'text-[14px]', icon: 13 },
};

export default function PriceChange({ value, percent, showIcon = true, showDollar = false, size = 'md', stockSymbol }: PriceChangeProps) {
  const isPositive = value >= 0;
  const color = isPositive ? COLORS.emerald : COLORS.red;
  const colorClass = isPositive ? 'text-emerald-600' : 'text-red-500';
  const s = sizeMap[size];

  return (
    <View className="flex-row items-center gap-0.5">
      {showIcon && (
        isPositive
          ? <TrendingUp size={s.icon} color={color} />
          : <TrendingDown size={s.icon} color={color} />
      )}
      {showDollar && (
        <Text className={`${s.text} font-body tabular-nums ${colorClass}`}>
          {isPositive ? '+' : ''}{formatCurrency(value, false, stockSymbol)}
        </Text>
      )}
      {percent !== undefined && (
        <Text className={`${s.text} font-body tabular-nums ${colorClass}`}>
          {formatPct(percent)}
        </Text>
      )}
    </View>
  );
}
