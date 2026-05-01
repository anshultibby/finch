import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Modal, ActivityIndicator, Alert } from 'react-native';
import { X } from 'lucide-react-native';
import { alpacaBrokerApi } from '@/lib/api';

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
  const [qty, setQty] = useState('');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [limitPrice, setLimitPrice] = useState('');
  const [loading, setLoading] = useState(false);

  const estimatedCost = parseFloat(qty || '0') * (orderType === 'limit' ? parseFloat(limitPrice || '0') : currentPrice);

  const handleTrade = async () => {
    const quantity = parseFloat(qty);
    if (!quantity || quantity <= 0) {
      Alert.alert('Invalid Quantity', 'Please enter a valid number of shares.');
      return;
    }

    setLoading(true);
    try {
      const order: any = {
        symbol,
        side,
        qty: quantity,
        order_type: orderType,
        time_in_force: 'day',
      };
      if (orderType === 'limit') {
        order.limit_price = parseFloat(limitPrice);
      }

      await alpacaBrokerApi.placeOrder(userId, order);
      Alert.alert('Order Placed', `${side === 'buy' ? 'Buy' : 'Sell'} order for ${quantity} shares of ${symbol} submitted.`);
      onTradeComplete?.();
      onClose();
      setQty('');
      setLimitPrice('');
    } catch (err: any) {
      Alert.alert('Order Failed', err.message || 'Failed to place order.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View className="flex-1 justify-end bg-black/40">
        <View className="bg-white rounded-t-3xl px-5 pb-8 pt-4">
          {/* Handle & Close */}
          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-lg font-body-bold text-slate-900">Trade {symbol}</Text>
            <TouchableOpacity onPress={onClose} className="p-1" activeOpacity={0.7}>
              <X size={22} color="#64748b" />
            </TouchableOpacity>
          </View>

          {/* Buy/Sell Toggle */}
          <View className="flex-row rounded-xl bg-slate-100 p-1 mb-4">
            {(['buy', 'sell'] as const).map(s => (
              <TouchableOpacity
                key={s}
                onPress={() => setSide(s)}
                className={`flex-1 py-2.5 rounded-lg items-center ${
                  side === s
                    ? s === 'buy' ? 'bg-emerald-500' : 'bg-red-500'
                    : 'bg-transparent'
                }`}
                activeOpacity={0.8}
              >
                <Text className={`text-sm font-body-bold uppercase ${side === s ? 'text-white' : 'text-slate-500'}`}>
                  {s}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Current Price */}
          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-sm font-body text-slate-500">Current Price</Text>
            <Text className="text-base font-body-bold text-slate-900">${currentPrice.toFixed(2)}</Text>
          </View>

          {/* Order Type */}
          <View className="flex-row gap-2 mb-4">
            {(['market', 'limit'] as const).map(t => (
              <TouchableOpacity
                key={t}
                onPress={() => setOrderType(t)}
                className={`flex-1 py-2 rounded-xl items-center border ${
                  orderType === t ? 'bg-slate-900 border-slate-900' : 'bg-white border-black/5'
                }`}
                activeOpacity={0.8}
              >
                <Text className={`text-sm font-body-medium capitalize ${orderType === t ? 'text-white' : 'text-slate-600'}`}>
                  {t}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Quantity */}
          <View className="mb-3">
            <Text className="text-sm font-body text-slate-500 mb-1">Shares</Text>
            <TextInput
              value={qty}
              onChangeText={setQty}
              placeholder="0"
              placeholderTextColor="#cbd5e1"
              keyboardType="numeric"
              className="bg-slate-50 rounded-xl px-4 py-3 text-lg font-body-bold text-slate-900 border border-black/5"
            />
          </View>

          {/* Limit Price */}
          {orderType === 'limit' && (
            <View className="mb-3">
              <Text className="text-sm font-body text-slate-500 mb-1">Limit Price</Text>
              <TextInput
                value={limitPrice}
                onChangeText={setLimitPrice}
                placeholder="0.00"
                placeholderTextColor="#cbd5e1"
                keyboardType="numeric"
                className="bg-slate-50 rounded-xl px-4 py-3 text-lg font-body-bold text-slate-900 border border-black/5"
              />
            </View>
          )}

          {/* Estimated */}
          {parseFloat(qty || '0') > 0 && (
            <View className="flex-row items-center justify-between py-3 mb-3 border-t border-black/5">
              <Text className="text-sm font-body text-slate-500">Estimated {side === 'buy' ? 'Cost' : 'Proceeds'}</Text>
              <Text className="text-base font-body-bold text-slate-900">${estimatedCost.toFixed(2)}</Text>
            </View>
          )}

          {/* Submit */}
          <TouchableOpacity
            onPress={handleTrade}
            disabled={loading || !qty}
            className={`py-4 rounded-2xl items-center ${
              side === 'buy' ? 'bg-emerald-500' : 'bg-red-500'
            } ${(!qty || loading) ? 'opacity-50' : ''}`}
            activeOpacity={0.8}
          >
            {loading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text className="text-white font-body-bold text-base">
                {side === 'buy' ? 'Buy' : 'Sell'} {symbol}
              </Text>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}
