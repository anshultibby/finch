import { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, Modal, ActivityIndicator, StyleSheet, Alert, Linking, Platform } from 'react-native';
import { Check, X, Sparkles } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import {
  getProPackage,
  purchasePro,
  restorePro,
  isUserCancelled,
  purchasesAvailable,
} from '@/lib/purchases';
import type { PurchasesPackage } from 'react-native-purchases';

const PRO_PERKS = [
  '2,500 monthly credits',
  'Priority agent runs',
  'Unlimited brokerage connections',
  'Morning brief + smart move alerts',
];

/**
 * Apple In-App Purchase paywall for the Pro subscription (App Store 3.1.1).
 * On success the StoreKit receipt is validated by RevenueCat, which webhooks
 * the backend to flip the user's plan — so we just refresh balance afterwards.
 */
export default function PaywallModal({
  visible,
  onClose,
  onPurchased,
}: {
  visible: boolean;
  onClose: () => void;
  onPurchased: () => void;
}) {
  const [pkg, setPkg] = useState<PurchasesPackage | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!visible) return;
    setLoading(true);
    getProPackage()
      .then(setPkg)
      .finally(() => setLoading(false));
  }, [visible]);

  const handleBuy = async () => {
    if (!pkg || busy) return;
    setBusy(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    try {
      const ok = await purchasePro(pkg);
      if (ok) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        onPurchased();
        onClose();
      }
    } catch (e: any) {
      if (!isUserCancelled(e)) {
        Alert.alert('Purchase failed', 'Something went wrong. Please try again.');
      }
    } finally {
      setBusy(false);
    }
  };

  const handleRestore = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const ok = await restorePro();
      if (ok) {
        Alert.alert('Restored', 'Your Pro subscription is active.');
        onPurchased();
        onClose();
      } else {
        Alert.alert('Nothing to restore', 'No active Pro subscription was found for this Apple ID.');
      }
    } finally {
      setBusy(false);
    }
  };

  const priceLabel = pkg?.product?.priceString || '$20';
  const unavailable = !purchasesAvailable();

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <TouchableOpacity onPress={onClose} style={styles.close} hitSlop={10}>
            <X size={20} color="#9ca3af" />
          </TouchableOpacity>

          <View style={styles.iconBadge}>
            <Sparkles size={22} color="#059669" />
          </View>
          <Text style={styles.title}>Finch Pro</Text>
          <Text style={styles.subtitle}>More credits, priority runs, and the full agent.</Text>

          <View style={styles.perks}>
            {PRO_PERKS.map((p) => (
              <View key={p} style={styles.perkRow}>
                <View style={styles.checkCircle}>
                  <Check size={13} color="#059669" />
                </View>
                <Text style={styles.perkText}>{p}</Text>
              </View>
            ))}
          </View>

          {loading ? (
            <ActivityIndicator color="#059669" style={{ marginVertical: 24 }} />
          ) : unavailable || !pkg ? (
            <Text style={styles.unavailable}>
              In-app purchases aren’t available on this device right now.
            </Text>
          ) : (
            <>
              <TouchableOpacity
                onPress={handleBuy}
                disabled={busy}
                style={[styles.buyBtn, busy && { opacity: 0.6 }]}
                activeOpacity={0.85}
              >
                {busy ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.buyText}>Subscribe — {priceLabel}/month</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity onPress={handleRestore} disabled={busy} style={styles.restoreBtn}>
                <Text style={styles.restoreText}>Restore purchases</Text>
              </TouchableOpacity>
            </>
          )}

          <Text style={styles.legal}>
            Auto-renews monthly until cancelled. Manage or cancel anytime in your{' '}
            <Text
              style={styles.link}
              onPress={() => Linking.openURL('https://apps.apple.com/account/subscriptions')}
            >
              Apple ID subscriptions
            </Text>
            .{'\n'}
            <Text
              style={styles.link}
              onPress={() => Linking.openURL('https://finchapp.ai/terms')}
            >
              Terms
            </Text>{' '}
            ·{' '}
            <Text
              style={styles.link}
              onPress={() => Linking.openURL('https://finchapp.ai/privacy')}
            >
              Privacy
            </Text>
          </Text>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: 24,
    paddingTop: 12,
    paddingBottom: Platform.OS === 'ios' ? 40 : 28,
  },
  handle: { width: 36, height: 4, backgroundColor: '#e5e7eb', borderRadius: 2, alignSelf: 'center', marginBottom: 12 },
  close: { position: 'absolute', top: 16, right: 16, padding: 4, zIndex: 2 },
  iconBadge: {
    width: 52, height: 52, borderRadius: 16, backgroundColor: '#ecfdf5',
    alignItems: 'center', justifyContent: 'center', alignSelf: 'center', marginTop: 8,
  },
  title: { fontSize: 22, fontFamily: 'DMSans-Bold', color: '#111827', textAlign: 'center', marginTop: 12 },
  subtitle: { fontSize: 13, fontFamily: 'DMSans', color: '#6b7280', textAlign: 'center', marginTop: 4, marginBottom: 20 },
  perks: { gap: 12, marginBottom: 8 },
  perkRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  checkCircle: {
    width: 22, height: 22, borderRadius: 11, backgroundColor: '#ecfdf5',
    alignItems: 'center', justifyContent: 'center',
  },
  perkText: { fontSize: 14, fontFamily: 'DMSans-Medium', color: '#374151' },
  buyBtn: { marginTop: 24, backgroundColor: '#059669', borderRadius: 14, paddingVertical: 15, alignItems: 'center' },
  buyText: { color: '#fff', fontSize: 15, fontFamily: 'DMSans-Bold' },
  restoreBtn: { paddingVertical: 12, alignItems: 'center' },
  restoreText: { fontSize: 13, fontFamily: 'DMSans-Medium', color: '#6b7280' },
  unavailable: { fontSize: 13, fontFamily: 'DMSans', color: '#9ca3af', textAlign: 'center', marginVertical: 24 },
  legal: { fontSize: 10, fontFamily: 'DMSans', color: '#9ca3af', textAlign: 'center', marginTop: 8, lineHeight: 15 },
  link: { color: '#059669', textDecorationLine: 'underline' },
});
