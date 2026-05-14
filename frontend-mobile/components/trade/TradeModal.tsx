import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Modal, ActivityIndicator, Alert, StyleSheet } from 'react-native';
import { X } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { alpacaBrokerApi } from '@/lib/api';
import { formatCurrency } from '@/lib/constants';
import SegmentedControl from '@/components/ui/SegmentedControl';

interface TradeModalProps {
  visible: boolean;
  onClose: () => void;
  symbol: string;
  currentPrice: number;
  userId: string;
  onTradeComplete?: () => void;
}

export default function TradeModal({ visible, onClose, symbol, currentPrice, userId, onTradeComplete }: TradeModalProps) {
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [inputMode, setInputMode] = useState<'shares' | 'dollars'>('shares');
  const [qty, setQty] = useState('');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [limitPrice, setLimitPrice] = useState('');
  const [loading, setLoading] = useState(false);

  const shares = inputMode === 'shares'
    ? parseFloat(qty || '0')
    : parseFloat(qty || '0') / currentPrice;

  const estimatedCost = shares * (orderType === 'limit' ? parseFloat(limitPrice || '0') : currentPrice);

  const handleTrade = async () => {
    if (shares <= 0) {
      Alert.alert('Invalid Amount', 'Please enter a valid amount.');
      return;
    }
    setLoading(true);
    try {
      const order: Record<string, any> = {
        symbol, side, order_type: orderType, time_in_force: 'day',
      };
      if (inputMode === 'shares') order.qty = shares;
      else order.notional = parseFloat(qty);
      if (orderType === 'limit') order.limit_price = parseFloat(limitPrice);

      await alpacaBrokerApi.placeOrder(userId, order as any);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      Alert.alert('Order Placed', `${side === 'buy' ? 'Buy' : 'Sell'} order for ${symbol} submitted.`);
      onTradeComplete?.();
      onClose();
      setQty('');
      setLimitPrice('');
    } catch (err: any) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      Alert.alert('Order Failed', err?.response?.data?.detail || err.message || 'Failed to place order.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View className="flex-1 justify-end bg-black/40">
        <View style={styles.sheet}>
          <View style={styles.handle} />

          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-lg font-body-bold text-gray-900">Trade {symbol}</Text>
            <TouchableOpacity onPress={onClose} className="p-1" activeOpacity={0.7}>
              <X size={20} color="#9ca3af" />
            </TouchableOpacity>
          </View>

          {/* Buy/Sell */}
          <View style={styles.sideToggle}>
            {(['buy', 'sell'] as const).map(s => (
              <TouchableOpacity
                key={s}
                onPress={() => { Haptics.selectionAsync(); setSide(s); }}
                style={[styles.sideBtn, side === s && (s === 'buy' ? styles.buyActive : styles.sellActive)]}
                activeOpacity={0.8}
              >
                <Text style={[styles.sideLabel, side === s && styles.sideLabelActive]}>{s.toUpperCase()}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <View className="flex-row items-center justify-between mb-3.5">
            <Text className="text-[13px] font-body text-gray-500">Current Price</Text>
            <Text className="text-[15px] font-body-bold text-gray-900 tabular-nums">{formatCurrency(currentPrice)}</Text>
          </View>

          <View className="mb-3.5">
            <SegmentedControl options={['market', 'limit']} selected={orderType} onChange={setOrderType} />
          </View>

          <View className="mb-1">
            <SegmentedControl
              options={['shares', 'dollars']}
              selected={inputMode}
              onChange={setInputMode}
              labels={{ shares: 'Shares', dollars: 'Dollars' }}
            />
          </View>

          <View className="mt-3 mb-3">
            <Text className="text-[13px] font-body text-gray-500 mb-1">
              {inputMode === 'shares' ? 'Number of Shares' : 'Dollar Amount'}
            </Text>
            <TextInput
              value={qty}
              onChangeText={setQty}
              placeholder={inputMode === 'shares' ? '0' : '0.00'}
              placeholderTextColor="#d1d5db"
              keyboardType="numeric"
              style={styles.numInput}
            />
          </View>

          {orderType === 'limit' && (
            <View className="mb-3">
              <Text className="text-[13px] font-body text-gray-500 mb-1">Limit Price</Text>
              <TextInput
                value={limitPrice}
                onChangeText={setLimitPrice}
                placeholder="0.00"
                placeholderTextColor="#d1d5db"
                keyboardType="numeric"
                style={styles.numInput}
              />
            </View>
          )}

          {estimatedCost > 0 && (
            <View className="flex-row items-center justify-between py-3 mb-3 border-t border-gray-100">
              <Text className="text-[13px] font-body text-gray-500">
                Est. {side === 'buy' ? 'Cost' : 'Proceeds'}
              </Text>
              <Text className="text-base font-body-bold text-gray-900 tabular-nums">{formatCurrency(estimatedCost)}</Text>
            </View>
          )}

          <TouchableOpacity
            onPress={handleTrade}
            disabled={loading || !qty}
            style={[
              styles.submitBtn,
              { backgroundColor: side === 'buy' ? '#059669' : '#dc2626' },
              (!qty || loading) && { opacity: 0.5 },
            ]}
            activeOpacity={0.8}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text className="text-white font-body-bold text-[15px]">
                {side === 'buy' ? 'Buy' : 'Sell'} {symbol}
              </Text>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  sheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: 20,
    paddingBottom: 32,
    paddingTop: 12,
  },
  handle: {
    width: 36,
    height: 4,
    backgroundColor: '#e5e7eb',
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 16,
  },
  sideToggle: {
    flexDirection: 'row',
    backgroundColor: '#f3f4f6',
    borderRadius: 10,
    padding: 3,
    marginBottom: 16,
  },
  sideBtn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
  },
  buyActive: { backgroundColor: '#059669' },
  sellActive: { backgroundColor: '#dc2626' },
  sideLabel: {
    fontSize: 13,
    fontFamily: 'DMSans-Bold',
    color: '#6b7280',
  },
  sideLabelActive: { color: '#fff' },
  numInput: {
    backgroundColor: '#f9fafb',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 20,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  submitBtn: {
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: 'center',
  },
});
