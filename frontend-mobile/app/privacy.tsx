import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Platform, Alert, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { Shield, FileText, Lock, Trash2, ChevronRight, ExternalLink } from 'lucide-react-native';
import * as WebBrowser from 'expo-web-browser';
import * as Haptics from 'expo-haptics';
import { COLORS } from '@/lib/constants';

const PRIVACY_URL = 'https://finchapp.ai/privacy';
const SUPPORT_EMAIL = 'support@finchapp.ai';

export default function PrivacyScreen() {
  const { user, signOut } = useAuth();

  const openPrivacyPolicy = () => {
    if (Platform.OS === 'web') { window.open(PRIVACY_URL, '_blank'); return; }
    WebBrowser.openBrowserAsync(PRIVACY_URL);
  };

  const requestDeletion = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    const subject = encodeURIComponent('Account deletion request');
    const body = encodeURIComponent(
      `Please delete my Finch account and associated data.\n\nAccount email: ${user?.email || ''}`
    );
    const mailto = `mailto:${SUPPORT_EMAIL}?subject=${subject}&body=${body}`;
    const proceed = () => Linking.openURL(mailto).catch(() => {
      Alert.alert('Could not open mail', `Email us at ${SUPPORT_EMAIL} to delete your account.`);
    });
    if (Platform.OS === 'web') {
      if (window.confirm('Request account deletion? This opens an email to our support team.')) proceed();
      return;
    }
    Alert.alert(
      'Delete account',
      'This will open an email to our support team to permanently delete your account and data.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Continue', style: 'destructive', onPress: proceed },
      ]
    );
  };

  return (
    <SafeAreaView className="flex-1 bg-white" edges={[]}>
      <ScrollView contentContainerClassName="px-4 pt-4 pb-8" showsVerticalScrollIndicator={false}>
        {/* Account */}
        <Text style={styles.sectionLabel}>ACCOUNT</Text>
        <View style={styles.card} className="mb-5">
          <Row label="Signed in as" value={user?.email || '—'} />
          <Row label="Name" value={user?.user_metadata?.full_name || '—'} isLast />
        </View>

        {/* What we store */}
        <Text style={styles.sectionLabel}>YOUR DATA</Text>
        <View style={[styles.card, { padding: 16 }]} className="mb-5">
          <View className="flex-row items-start gap-3">
            <Lock size={16} color={COLORS.emerald} style={{ marginTop: 2 }} />
            <View className="flex-1">
              <Text style={styles.dataTitle}>Stored securely</Text>
              <Text style={styles.dataBody}>
                We store your chats, watchlists, and connected-account data to power the app.
                Any API keys you add are encrypted. We never sell your personal information.
              </Text>
            </View>
          </View>
        </View>

        {/* Links */}
        <View style={styles.menuCard} className="mb-5">
          <ActionRow
            icon={<FileText size={17} color="#6b7280" />}
            label="Privacy Policy"
            trailing={<ExternalLink size={15} color="#d1d5db" />}
            onPress={openPrivacyPolicy}
            isLast
          />
        </View>

        {/* Danger zone */}
        <Text style={styles.sectionLabel}>DANGER ZONE</Text>
        <View style={styles.menuCard} className="mb-3">
          <ActionRow
            icon={<Trash2 size={17} color="#ef4444" />}
            label="Delete account"
            labelColor="#ef4444"
            trailing={<ChevronRight size={15} color="#fca5a5" />}
            onPress={requestDeletion}
            isLast
          />
        </View>

        <TouchableOpacity onPress={() => signOut()} className="mt-2 items-center py-3" activeOpacity={0.7}>
          <Text className="text-[13px] font-body-medium text-gray-400">Sign out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ label, value, isLast }: { label: string; value: string; isLast?: boolean }) {
  return (
    <View className={`flex-row items-center justify-between px-4 py-3.5 ${!isLast ? 'border-b border-gray-100' : ''}`}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue} numberOfLines={1}>{value}</Text>
    </View>
  );
}

function ActionRow({ icon, label, labelColor, trailing, onPress, isLast }: {
  icon: React.ReactNode; label: string; labelColor?: string;
  trailing?: React.ReactNode; onPress?: () => void; isLast?: boolean;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      className={`flex-row items-center gap-3 px-3.5 py-3.5 ${!isLast ? 'border-b border-gray-100' : ''}`}
      activeOpacity={0.6}
    >
      {icon}
      <Text className="flex-1 text-[14px] font-body-medium" style={{ color: labelColor || '#111827' }}>{label}</Text>
      {trailing}
    </TouchableOpacity>
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
  menuCard: {
    backgroundColor: '#fff', borderRadius: 12,
    borderWidth: 1, borderColor: '#f3f4f6', overflow: 'hidden',
  },
  rowLabel: { fontSize: 13, fontFamily: 'DMSans', color: '#6b7280' },
  rowValue: { fontSize: 13, fontFamily: 'DMSans-Medium', color: '#111827', flex: 1, textAlign: 'right', marginLeft: 16 },
  dataTitle: { fontSize: 13, fontFamily: 'DMSans-Bold', color: '#111827', marginBottom: 4 },
  dataBody: { fontSize: 12.5, fontFamily: 'DMSans', color: '#6b7280', lineHeight: 18 },
});
