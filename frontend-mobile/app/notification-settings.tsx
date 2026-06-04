import { View, Text, ScrollView, StyleSheet, Switch, Platform, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useState, useEffect, useCallback } from 'react';
import * as Notifications from 'expo-notifications';
import * as Haptics from 'expo-haptics';
import { Bell, Mail } from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { registerForPushNotifications, unregisterPushToken } from '@/lib/pushNotifications';
import { COLORS } from '@/lib/constants';

export default function NotificationSettingsScreen() {
  const { session } = useAuth();
  const [pushEnabled, setPushEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const webUnsupported = Platform.OS === 'web';

  useEffect(() => {
    if (webUnsupported) { setLoading(false); return; }
    Notifications.getPermissionsAsync()
      .then(({ status }) => setPushEnabled(status === 'granted'))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [webUnsupported]);

  const togglePush = useCallback(async (value: boolean) => {
    if (!session?.access_token || busy) return;
    Haptics.selectionAsync();
    setBusy(true);
    try {
      if (value) {
        const token = await registerForPushNotifications(session.access_token);
        setPushEnabled(!!token);
      } else {
        try {
          const { data } = await Notifications.getExpoPushTokenAsync();
          if (data) await unregisterPushToken(session.access_token, data);
        } catch {}
        setPushEnabled(false);
      }
    } finally {
      setBusy(false);
    }
  }, [session, busy]);

  return (
    <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={[]}>
      <ScrollView contentContainerClassName="px-4 pt-4 pb-8" showsVerticalScrollIndicator={false}>
        <Text style={styles.sectionLabel}>PUSH</Text>
        <View style={styles.card} className="mb-2">
          <View className="flex-row items-center gap-3 px-4 py-3.5">
            <View style={[styles.iconBox, { backgroundColor: '#eef2ff' }]}>
              <Bell size={16} color="#6366f1" />
            </View>
            <View className="flex-1">
              <Text style={styles.rowTitle}>Push notifications</Text>
              <Text style={styles.rowSub}>
                {webUnsupported ? 'Available in the mobile app' : 'Alerts when your tasks finish or prices move'}
              </Text>
            </View>
            {loading ? (
              <ActivityIndicator color={COLORS.gray400} />
            ) : (
              <Switch
                value={pushEnabled}
                onValueChange={togglePush}
                disabled={webUnsupported || busy}
                trackColor={{ false: '#e5e7eb', true: '#a7f3d0' }}
                thumbColor={pushEnabled ? '#059669' : '#f9fafb'}
                ios_backgroundColor="#e5e7eb"
              />
            )}
          </View>
        </View>
        <Text style={styles.hint}>
          {webUnsupported
            ? 'Open Finch on iOS or Android to enable push notifications.'
            : 'You can also manage permissions in your device Settings.'}
        </Text>

        <Text style={[styles.sectionLabel, { marginTop: 20 }]}>EMAIL</Text>
        <View style={styles.card}>
          <View className="flex-row items-center gap-3 px-4 py-3.5">
            <View style={[styles.iconBox, { backgroundColor: '#fffbeb' }]}>
              <Mail size={16} color="#d97706" />
            </View>
            <View className="flex-1">
              <Text style={styles.rowTitle}>Email me when done</Text>
              <Text style={styles.rowSub}>
                Long tasks can email you on completion — toggle this from within a chat while it runs.
              </Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  sectionLabel: {
    fontSize: 11, fontFamily: 'DMSans-Bold', color: '#9ca3af',
    letterSpacing: 0.5, marginBottom: 8, marginLeft: 4,
  },
  card: {
    backgroundColor: '#fff', borderRadius: 12,
    borderWidth: 1, borderColor: '#f3f4f6', overflow: 'hidden',
  },
  iconBox: {
    width: 36, height: 36, borderRadius: 10,
    alignItems: 'center', justifyContent: 'center',
  },
  rowTitle: { fontSize: 14, fontFamily: 'DMSans-Medium', color: '#111827' },
  rowSub: { fontSize: 12, fontFamily: 'DMSans', color: '#9ca3af', marginTop: 2, lineHeight: 16 },
  hint: { fontSize: 11.5, fontFamily: 'DMSans', color: '#9ca3af', marginLeft: 4, marginTop: 2, lineHeight: 16 },
});
