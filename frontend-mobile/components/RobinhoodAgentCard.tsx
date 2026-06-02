import { View, Text, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react-native';
import { robinhoodApi } from '@/lib/api';
import { connectRobinhood } from '@/lib/robinhoodAuth';

/**
 * AI Trading Agent card (Robinhood) for the mobile home — mirrors the web card.
 * Connect runs the on-device loopback OAuth (see lib/robinhoodAuth.ts).
 */
export default function RobinhoodAgentCard({ userId }: { userId: string }) {
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    robinhoodApi.checkStatus(userId).then(d => setConnected(d.is_connected)).catch(() => {});
  }, [userId]);

  const handlePress = async () => {
    if (connected) {
      Alert.alert('Disconnect Robinhood?', 'Your agent will no longer be able to trade.', [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Disconnect', style: 'destructive', onPress: async () => {
          await robinhoodApi.disconnect(userId).catch(() => {});
          setConnected(false);
        } },
      ]);
      return;
    }
    setBusy(true);
    try {
      await connectRobinhood(userId);
      setConnected(true);
    } catch (e: any) {
      Alert.alert('Connection failed', e?.message === 'timed_out'
        ? 'Timed out waiting for approval. Approve the request in your Robinhood app.'
        : 'Could not connect Robinhood. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <View className="rounded-2xl border border-gray-200 p-4 mb-3">
      <View className="flex-row items-center gap-2.5">
        <View className="h-8 w-8 rounded-lg items-center justify-center" style={{ backgroundColor: '#10b981' }}>
          <Sparkles size={16} color="#ffffff" />
        </View>
        <View className="flex-1">
          <Text className="text-[13px] font-body-medium text-gray-900">AI Trading Agent</Text>
          {connected
            ? <Text className="text-[11px] font-body" style={{ color: '#059669' }}>● Active</Text>
            : <Text className="text-[11px] font-body text-gray-400">Powered by Robinhood</Text>}
        </View>
      </View>

      {connected ? (
        <TouchableOpacity onPress={handlePress} className="mt-3" activeOpacity={0.7}>
          <Text className="text-[11px] text-gray-400">Tap to disconnect · trades your agentic account</Text>
        </TouchableOpacity>
      ) : (
        <View className="mt-3">
          <Text className="text-[12px] leading-5 text-gray-500">
            An agent that places real trades for you — in an isolated account, never your main portfolio.
          </Text>
          <TouchableOpacity
            onPress={handlePress}
            disabled={busy}
            className="mt-3 rounded-lg py-2 items-center"
            style={{ backgroundColor: '#059669', opacity: busy ? 0.6 : 1 }}
            activeOpacity={0.8}
          >
            {busy ? <ActivityIndicator size="small" color="#fff" />
                  : <Text className="text-[12px] font-body-medium text-white">Enable trading</Text>}
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}
