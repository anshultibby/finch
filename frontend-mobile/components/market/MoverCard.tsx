import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { formatCurrency, formatPct } from '@/lib/constants';
import MiniSparkline from '@/components/shared/MiniSparkline';

interface MoverCardProps {
  symbol: string;
  name: string;
  price: number;
  changePct: number;
  onPress: () => void;
}

export default function MoverCard({ symbol, name, price, changePct, onPress }: MoverCardProps) {
  const isPositive = changePct >= 0;

  return (
    <TouchableOpacity onPress={onPress} style={styles.card} activeOpacity={0.7}>
      <View className="flex-row items-start justify-between">
        <View className="flex-1 mr-1">
          <Text className="text-[13px] font-body-bold text-gray-900">{symbol}</Text>
          <Text className="text-[11px] font-body text-gray-400 mt-px" numberOfLines={1}>{name}</Text>
        </View>
        <MiniSparkline symbol={symbol} width={44} height={20} days={7} />
      </View>
      <Text className="text-[14px] font-body-medium text-gray-900 mt-2 tabular-nums">
        {formatCurrency(price)}
      </Text>
      <View className={`mt-1.5 self-start px-1.5 py-px rounded-md ${isPositive ? 'bg-emerald-50' : 'bg-red-50'}`}>
        <Text className={`text-[11px] font-body-bold tabular-nums ${isPositive ? 'text-emerald-600' : 'text-red-500'}`}>
          {formatPct(changePct)}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    width: 130,
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 12,
    marginRight: 10,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
});
