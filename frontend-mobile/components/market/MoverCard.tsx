import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { formatCurrency, formatPct } from '@/lib/constants';
import MiniSparkline from '@/components/shared/MiniSparkline';
import { PressableScale } from '@/components/ui/PressableScale';
import { CountUp } from '@/components/ui/CountUp';

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
    <PressableScale onPress={onPress} style={styles.card}>
      <View className="flex-row items-start justify-between">
        <View className="flex-1 mr-1">
          <Text className="text-[13px] font-body-bold text-gray-900">{symbol}</Text>
          <Text className="text-[11px] font-body text-gray-400 mt-px" numberOfLines={1}>{name}</Text>
        </View>
        <MiniSparkline symbol={symbol} width={44} height={20} days={7} />
      </View>
      <CountUp
        value={price}
        format={(n) => formatCurrency(n, false, symbol)}
        style={styles.price}
      />
      <View className={`mt-1.5 self-start px-1.5 py-px rounded-md ${isPositive ? 'bg-emerald-50' : 'bg-red-50'}`}>
        <Text className={`text-[11px] font-body-bold tabular-nums ${isPositive ? 'text-emerald-600' : 'text-red-500'}`}>
          {formatPct(changePct)}
        </Text>
      </View>
    </PressableScale>
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
  price: {
    fontSize: 14,
    fontFamily: 'DMSans-Medium',
    color: '#111827',
    marginTop: 8,
    fontVariant: ['tabular-nums'],
  },
});
