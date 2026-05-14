import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import PriceChange from '@/components/ui/PriceChange';
import { formatCurrency } from '@/lib/constants';

interface StockRowProps {
  symbol: string;
  name?: string;
  price?: number;
  changePct?: number;
  onPress: () => void;
  rightContent?: React.ReactNode;
  subtitle?: string;
}

export default function StockRow({ symbol, name, price, changePct, onPress, rightContent, subtitle }: StockRowProps) {
  return (
    <TouchableOpacity
      onPress={onPress}
      className="flex-row items-center justify-between py-3"
      activeOpacity={0.6}
    >
      <View className="flex-1 mr-3">
        <Text className="text-[14px] font-body-bold text-gray-900">{symbol}</Text>
        {(name || subtitle) && (
          <Text className="text-[12px] font-body text-gray-500 mt-px" numberOfLines={1}>
            {subtitle || name}
          </Text>
        )}
      </View>
      {rightContent || (
        <View className="items-end">
          {price !== undefined && (
            <Text className="text-[14px] font-body-medium text-gray-900 tabular-nums">
              {formatCurrency(price)}
            </Text>
          )}
          {changePct !== undefined && (
            <PriceChange value={changePct} percent={changePct} showIcon={false} size="sm" />
          )}
        </View>
      )}
    </TouchableOpacity>
  );
}
