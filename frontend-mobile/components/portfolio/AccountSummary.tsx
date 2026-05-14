import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { formatCurrency } from '@/lib/constants';

interface AccountSummaryProps {
  equity: number;
  cash: number;
  buyingPower: number;
  unrealizedPl: number;
}

export default function AccountSummary({ equity, cash, buyingPower, unrealizedPl }: AccountSummaryProps) {
  const isPositive = unrealizedPl >= 0;

  return (
    <View style={styles.card}>
      <View className="flex-row justify-between mb-3.5">
        <View>
          <Text className="text-[12px] font-body text-gray-500">Total Equity</Text>
          <Text className="text-[22px] font-body-bold text-gray-900 mt-0.5 tabular-nums">
            {formatCurrency(equity)}
          </Text>
        </View>
        <View className="items-end">
          <Text className="text-[12px] font-body text-gray-500">Unrealized P&L</Text>
          <Text className={`text-base font-body-bold mt-0.5 tabular-nums ${isPositive ? 'text-emerald-600' : 'text-red-500'}`}>
            {isPositive ? '+' : ''}{formatCurrency(unrealizedPl)}
          </Text>
        </View>
      </View>
      <View className="flex-row gap-6 pt-3 border-t border-gray-100">
        <View>
          <Text className="text-[11px] font-body text-gray-400">Cash</Text>
          <Text className="text-[13px] font-body-medium text-gray-700 tabular-nums">{formatCurrency(cash)}</Text>
        </View>
        <View>
          <Text className="text-[11px] font-body text-gray-400">Buying Power</Text>
          <Text className="text-[13px] font-body-medium text-gray-700 tabular-nums">{formatCurrency(buyingPower)}</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
});
