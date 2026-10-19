import { View, Text, TouchableOpacity, Alert } from 'react-native';
import { useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import { Sparkles } from 'lucide-react-native';
import { robinhoodApi } from '@/lib/api';

/**
 * AI Trading Agent card (Robinhood). Robinhood only renders agent consent in a
 * desktop browser on a loopback redirect, so linking can't happen on a phone —
 * the card explains that instead of offering a button that would fail. Once
 * linked (from Finch Connect on desktop), it shows status and links to Trader.
 */
export default function RobinhoodAgentCard({ userId }: { userId: string }) {
  const router = useRouter();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    robinhoodApi.checkStatus(userId).then(d => setConnected(d.is_connected)).catch(() => {});
  }, [userId]);

  const disconnect = () => {
    Alert.alert('Disconnect Robinhood?', 'Your agent will no longer be able to trade.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Disconnect', style: 'destructive', onPress: async () => {
        await robinhoodApi.disconnect(userId).catch(() => {});
        setConnected(false);
      } },
    ]);
  };

  return (
    <View className="rounded-2xl border border-gray-200 p-4 mb-3">
      <TouchableOpacity
        className="flex-row items-center gap-2.5"
        activeOpacity={connected ? 0.7 : 1}
        disabled={!connected}
        onPress={() => router.push('/trader')}
      >
        <View className="h-8 w-8 rounded-lg items-center justify-center" style={{ backgroundColor: '#10b981' }}>
          <Sparkles size={16} color="#ffffff" />
        </View>
        <View className="flex-1">
          <Text className="text-[13px] font-body-medium text-gray-900">AI Trading Agent</Text>
          {connected
            ? <Text className="text-[11px] font-body" style={{ color: '#059669' }}>● Active · tap to view</Text>
            : <Text className="text-[11px] font-body text-gray-400">Powered by Robinhood</Text>}
        </View>
      </TouchableOpacity>

      {connected ? (
        <TouchableOpacity onPress={disconnect} className="mt-3" activeOpacity={0.7}>
          <Text className="text-[11px] text-gray-400">Tap to disconnect · trades your agentic account</Text>
        </TouchableOpacity>
      ) : (
        <View className="mt-3">
          <Text className="text-[12px] leading-5 text-gray-500">
            An agent that places real trades for you — in an isolated account, never your main portfolio, and only with your approval.
          </Text>
          <Text className="mt-2 text-[11px] leading-4 text-gray-400">
            Robinhood only allows linking an agent from a computer. Open Finch Connect on your desktop to link it — it shows up here once connected.
          </Text>
        </View>
      )}
    </View>
  );
}
