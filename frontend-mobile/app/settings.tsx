import { View, Text, TouchableOpacity, ScrollView, Alert, TextInput, ActivityIndicator, Modal, StyleSheet, Platform, Switch, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { useState, useEffect, useCallback } from 'react';
import { creditsApi, apiKeysApi, robinhoodApi, accountApi, UserPreferences, CreditBalance } from '@/lib/api';
import { connectRobinhood } from '@/lib/robinhoodAuth';
import { purchasesAvailable } from '@/lib/purchases';
import PaywallModal from '@/components/PaywallModal';
import { CreditCard, LogOut, ChevronRight, Key, Shield, Bell, X, Check, Trash2, Sparkles, Sunrise } from 'lucide-react-native';
import { COLORS } from '@/lib/constants';
import * as Haptics from 'expo-haptics';
import FinchLogo from '@/components/FinchLogo';

interface ApiKeyEntry {
  service: string;
  api_key_id_masked: string;
  has_private_key: boolean;
}

export default function SettingsScreen() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [showPaywall, setShowPaywall] = useState(false);
  const [apiKeys, setApiKeys] = useState<ApiKeyEntry[]>([]);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [rhConnected, setRhConnected] = useState(false);
  const [rhBusy, setRhBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [requireApproval, setRequireApproval] = useState(true);
  const [prefsBusy, setPrefsBusy] = useState(false);
  const [briefEnabled, setBriefEnabled] = useState(false);
  const [briefTime, setBriefTime] = useState('08:00');
  const [briefPhoneDraft, setBriefPhoneDraft] = useState('');
  const [briefPhoneSaved, setBriefPhoneSaved] = useState('');

  const refreshBalance = useCallback(() => {
    if (user) creditsApi.getBalance(user.id).then(setBalance).catch(() => {});
  }, [user]);

  useEffect(() => {
    if (user) {
      refreshBalance();
      apiKeysApi.getKeys(user.id).then(data => setApiKeys(data.keys || [])).catch(() => {});
      robinhoodApi.checkStatus(user.id).then(d => setRhConnected(d.is_connected)).catch(() => {});
      accountApi.getPreferences(user.id).then(p => {
        setRequireApproval(p.require_trade_approval);
        setBriefEnabled(p.morning_brief_enabled ?? false);
        setBriefTime(p.morning_brief_time || '08:00');
        setBriefPhoneDraft(p.morning_brief_phone || '');
        setBriefPhoneSaved(p.morning_brief_phone || '');
      }).catch(() => {});
    }
  }, [user]);

  // The brief schedule is pinned to the device's timezone on every change, so
  // it lands at the right local hour without ever asking the user.
  const deviceTimezone = () => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    } catch {
      return 'UTC';
    }
  };

  const saveBriefPrefs = async (updates: Partial<UserPreferences>, revert: () => void) => {
    if (!user) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      const p = await accountApi.updatePreferences(user.id, {
        ...updates,
        morning_brief_timezone: deviceTimezone(),
      });
      setBriefEnabled(p.morning_brief_enabled);
      setBriefTime(p.morning_brief_time);
      setBriefPhoneSaved(p.morning_brief_phone || '');
    } catch {
      revert();
      Alert.alert('Could not save', 'Please try again.');
    }
  };

  const handleToggleBrief = (value: boolean) => {
    const prev = briefEnabled;
    setBriefEnabled(value); // optimistic
    saveBriefPrefs({ morning_brief_enabled: value }, () => setBriefEnabled(prev));
  };

  const handleSelectBriefTime = (time: string) => {
    const prev = briefTime;
    setBriefTime(time); // optimistic
    saveBriefPrefs({ morning_brief_time: time }, () => setBriefTime(prev));
  };

  const handleSaveBriefPhone = () => {
    const phone = briefPhoneDraft.trim();
    if (phone === briefPhoneSaved) return;
    if (phone && !/^\+[1-9]\d{6,14}$/.test(phone)) {
      Alert.alert('Invalid number', 'Use international format, e.g. +15551234567.');
      return;
    }
    saveBriefPrefs({ morning_brief_phone: phone }, () => setBriefPhoneDraft(briefPhoneSaved));
  };

  const handleToggleApproval = async (value: boolean) => {
    if (!user || prefsBusy) return;
    const previous = requireApproval;
    setRequireApproval(value); // optimistic
    setPrefsBusy(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      const updated = await accountApi.updatePreferences(user.id, { require_trade_approval: value });
      setRequireApproval(updated.require_trade_approval);
    } catch {
      setRequireApproval(previous); // revert
      Alert.alert('Could not save', 'Please try again.');
    } finally {
      setPrefsBusy(false);
    }
  };

  const handleConnectRobinhood = async () => {
    if (!user) return;
    if (rhConnected) {
      Alert.alert('Disconnect Robinhood?', 'Your agent will no longer be able to trade.', [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Disconnect', style: 'destructive', onPress: async () => {
          await robinhoodApi.disconnect(user.id).catch(() => {});
          setRhConnected(false);
        } },
      ]);
      return;
    }
    setRhBusy(true);
    try {
      await connectRobinhood(user.id);
      setRhConnected(true);
    } catch (e: any) {
      Alert.alert('Connection failed', e?.message === 'timed_out'
        ? 'Timed out waiting for approval. Make sure to approve in your Robinhood app.'
        : 'Could not connect Robinhood. Please try again.');
    } finally {
      setRhBusy(false);
    }
  };

  // Apple requires a path to manage/cancel from inside the app. iOS subscriptions
  // are managed in the system Apple ID sheet; web (Stripe) subscriptions on the site.
  const handleManageSubscription = () => {
    if (balance?.subscription_provider === 'apple') {
      Linking.openURL('https://apps.apple.com/account/subscriptions');
    } else {
      Alert.alert(
        'Manage on the web',
        'This subscription was started on finchapp.ai. Manage or cancel it there.',
        [
          { text: 'Close', style: 'cancel' },
          { text: 'Open finchapp.ai', onPress: () => Linking.openURL('https://finchapp.ai') },
        ],
      );
    }
  };

  const handleSignOut = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    if (Platform.OS === 'web') {
      if (window.confirm('Sign out?')) signOut();
      return;
    }
    Alert.alert('Sign Out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: signOut },
    ]);
  };

  const handleDeleteAccount = () => {
    const doDelete = async () => {
      if (!user) return;
      setDeleting(true);
      try {
        await accountApi.deleteAccount(user.id);
        await signOut();
      } catch {
        setDeleting(false);
        const msg = 'Could not delete your account. Please try again or email support@finchapp.ai.';
        if (Platform.OS === 'web') window.alert(msg);
        else Alert.alert('Error', msg);
      }
    };
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    const message = 'This permanently deletes your Finch account and all associated data. This cannot be undone.';
    if (Platform.OS === 'web') {
      if (window.confirm(`Delete your account?\n\n${message}`)) doDelete();
      return;
    }
    Alert.alert('Delete account?', message, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete account', style: 'destructive', onPress: doDelete },
    ]);
  };

  const deleteApiKey = async (service: string) => {
    if (!user) return;
    if (Platform.OS === 'web') {
      if (!window.confirm(`Remove ${service} API key?`)) return;
      try { await apiKeysApi.deleteKey(user.id, service); setApiKeys(prev => prev.filter(k => k.service !== service)); } catch {}
      return;
    }
    Alert.alert('Remove Key', `Remove ${service} API key?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove', style: 'destructive',
        onPress: async () => {
          try { await apiKeysApi.deleteKey(user.id, service); setApiKeys(prev => prev.filter(k => k.service !== service)); } catch {}
        },
      },
    ]);
  };

  const isPro = balance?.plan === 'pro';

  return (
    <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={[]}>
      <ScrollView contentContainerClassName="px-4 pb-8">
        {/* Profile */}
        <View style={styles.card} className="mb-3">
          <View className="flex-row items-center gap-3">
            <View style={styles.avatar}>
              <Text className="text-lg font-body-bold text-gray-600">
                {(user?.user_metadata?.full_name || 'U')[0].toUpperCase()}
              </Text>
            </View>
            <View className="flex-1">
              <Text className="text-[15px] font-body-bold text-gray-900">
                {user?.user_metadata?.full_name || 'User'}
              </Text>
              <Text className="text-[13px] font-body text-gray-500">{user?.email}</Text>
            </View>
          </View>
        </View>

        {/* Plan & Credits */}
        <View style={styles.menuCard} className="mb-3">
          <View className="p-3.5 flex-row items-center justify-between">
            <View className="flex-row items-center gap-3">
              <View style={[styles.iconBox, { backgroundColor: isPro ? '#ecfdf5' : '#fffbeb' }]}>
                {isPro
                  ? <Sparkles size={16} color="#059669" />
                  : <CreditCard size={16} color="#d97706" />}
              </View>
              <View>
                <View className="flex-row items-center gap-1.5">
                  <Text className="text-[13px] font-body-medium text-gray-900">
                    {isPro ? 'Finch Pro' : 'Free plan'}
                  </Text>
                  {isPro && (
                    <View style={styles.proBadge}><Text style={styles.proBadgeText}>PRO</Text></View>
                  )}
                </View>
                <Text className="text-[11px] font-body text-gray-500">
                  {balance !== null ? `${balance.credits.toLocaleString()} credits remaining` : 'Loading...'}
                </Text>
              </View>
            </View>
            {/* Upgrade CTA — only where IAP can run (App Store 3.1.1). */}
            {!isPro && purchasesAvailable() && (
              <TouchableOpacity onPress={() => setShowPaywall(true)} style={styles.upgradeBtn} activeOpacity={0.85}>
                <Text style={styles.upgradeBtnText}>Upgrade</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Manage subscription (Pro only) */}
          {isPro && (
            <TouchableOpacity
              className="p-3.5 flex-row items-center justify-between border-t border-gray-100"
              onPress={handleManageSubscription}
              activeOpacity={0.7}
            >
              <Text className="text-[13px] font-body-medium text-gray-700">Manage subscription</Text>
              <ChevronRight size={16} color="#d1d5db" />
            </TouchableOpacity>
          )}
        </View>

        {/* API Keys */}
        <View style={styles.menuCard} className="mb-3">
          <TouchableOpacity className="p-3.5 flex-row items-center justify-between" onPress={() => setShowApiKeyModal(true)} activeOpacity={0.7}>
            <View className="flex-row items-center gap-3">
              <View style={[styles.iconBox, { backgroundColor: '#f5f3ff' }]}>
                <Key size={16} color="#7c3aed" />
              </View>
              <View>
                <Text className="text-[13px] font-body-medium text-gray-900">API Keys</Text>
                <Text className="text-[11px] font-body text-gray-500">
                  {apiKeys.length > 0 ? `${apiKeys.length} key${apiKeys.length > 1 ? 's' : ''} saved` : 'Manage credentials'}
                </Text>
              </View>
            </View>
            <ChevronRight size={16} color="#d1d5db" />
          </TouchableOpacity>
        </View>

        {/* AI Trading Agent (Robinhood) */}
        <View style={styles.menuCard} className="mb-3">
          <TouchableOpacity className="p-3.5 flex-row items-center justify-between" onPress={handleConnectRobinhood} activeOpacity={0.7} disabled={rhBusy}>
            <View className="flex-row items-center gap-3">
              <View style={[styles.iconBox, { backgroundColor: '#ecfdf5' }]}>
                <Sparkles size={16} color="#059669" />
              </View>
              <View>
                <Text className="text-[13px] font-body-medium text-gray-900">AI Trading Agent</Text>
                <Text className="text-[11px] font-body text-gray-500">
                  {rhConnected ? 'Connected · Robinhood' : 'Connect Robinhood to enable trading'}
                </Text>
              </View>
            </View>
            {rhBusy
              ? <ActivityIndicator size="small" color="#059669" />
              : rhConnected
                ? <Check size={16} color="#059669" />
                : <ChevronRight size={16} color="#d1d5db" />}
          </TouchableOpacity>

          {/* Require approval for every trade */}
          <View className="p-3.5 flex-row items-center justify-between border-t border-gray-100">
            <View className="flex-row items-center gap-3 flex-1 pr-3">
              <View style={[styles.iconBox, { backgroundColor: '#ecfdf5' }]}>
                <Shield size={16} color="#059669" />
              </View>
              <View className="flex-1">
                <Text className="text-[13px] font-body-medium text-gray-900">Approve every trade</Text>
                <Text className="text-[11px] font-body text-gray-500">
                  {requireApproval
                    ? 'Finch asks before placing any order'
                    : 'Unattended — Finch can trade without asking'}
                </Text>
              </View>
            </View>
            <Switch
              value={requireApproval}
              onValueChange={handleToggleApproval}
              disabled={prefsBusy}
              trackColor={{ false: '#d6d3d1', true: '#059669' }}
              thumbColor="#ffffff"
            />
          </View>
        </View>

        {/* Morning Brief */}
        <View style={styles.menuCard} className="mb-3">
          <View className="p-3.5 flex-row items-center justify-between">
            <View className="flex-row items-center gap-3 flex-1 pr-3">
              <View style={[styles.iconBox, { backgroundColor: '#fff7ed' }]}>
                <Sunrise size={16} color="#ea580c" />
              </View>
              <View className="flex-1">
                <Text className="text-[13px] font-body-medium text-gray-900">Morning brief</Text>
                <Text className="text-[11px] font-body text-gray-500">
                  {briefEnabled
                    ? `Daily at ${briefTime} — your holdings & watchlist news`
                    : 'A daily digest of your holdings & watchlist'}
                </Text>
              </View>
            </View>
            <Switch
              value={briefEnabled}
              onValueChange={handleToggleBrief}
              trackColor={{ false: '#d6d3d1', true: '#059669' }}
              thumbColor="#ffffff"
            />
          </View>

          {briefEnabled && (
            <View className="px-3.5 pb-3.5 border-t border-gray-100">
              <Text className="text-[11px] font-body-medium text-gray-400 mt-3 mb-2 uppercase tracking-wide">Delivery time</Text>
              <View className="flex-row flex-wrap gap-1.5">
                {['06:30', '07:00', '07:30', '08:00', '08:30', '09:00'].map(t => (
                  <TouchableOpacity
                    key={t}
                    onPress={() => handleSelectBriefTime(t)}
                    style={[styles.timeChip, briefTime === t && styles.timeChipActive]}
                    activeOpacity={0.7}
                  >
                    <Text style={[styles.timeChipText, briefTime === t && styles.timeChipTextActive]}>{t}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <Text className="text-[11px] font-body-medium text-gray-400 mt-3.5 mb-1.5 uppercase tracking-wide">WhatsApp (optional)</Text>
              <TextInput
                value={briefPhoneDraft}
                onChangeText={setBriefPhoneDraft}
                onBlur={handleSaveBriefPhone}
                onSubmitEditing={handleSaveBriefPhone}
                placeholder="+15551234567"
                placeholderTextColor="#d1d5db"
                keyboardType="phone-pad"
                autoCapitalize="none"
                style={styles.textInput}
                returnKeyType="done"
              />
              <Text className="text-[10px] font-body text-gray-400">
                Delivered by push and email{briefPhoneSaved ? ' and WhatsApp' : ''}, in your local timezone.
              </Text>
            </View>
          )}
        </View>

        {/* Notifications */}
        <View style={styles.menuCard} className="mb-3">
          <TouchableOpacity className="p-3.5 flex-row items-center justify-between" onPress={() => router.push('/notification-settings')} activeOpacity={0.7}>
            <View className="flex-row items-center gap-3">
              <View style={[styles.iconBox, { backgroundColor: '#eef2ff' }]}>
                <Bell size={16} color="#6366f1" />
              </View>
              <Text className="text-[13px] font-body-medium text-gray-900">Notifications</Text>
            </View>
            <ChevronRight size={16} color="#d1d5db" />
          </TouchableOpacity>
        </View>

        {/* Privacy */}
        <View style={styles.menuCard} className="mb-3">
          <TouchableOpacity className="p-3.5 flex-row items-center justify-between" onPress={() => router.push('/privacy')} activeOpacity={0.7}>
            <View className="flex-row items-center gap-3">
              <View style={[styles.iconBox, { backgroundColor: '#f9fafb' }]}>
                <Shield size={16} color={COLORS.gray500} />
              </View>
              <Text className="text-[13px] font-body-medium text-gray-900">Privacy & Security</Text>
            </View>
            <ChevronRight size={16} color="#d1d5db" />
          </TouchableOpacity>
        </View>

        {/* Sign Out */}
        <TouchableOpacity
          onPress={handleSignOut}
          style={styles.menuCard}
          className="py-3 flex-row items-center justify-center gap-2"
          activeOpacity={0.8}
        >
          <LogOut size={15} color="#ef4444" />
          <Text className="text-[13px] font-body-medium text-red-500">Sign Out</Text>
        </TouchableOpacity>

        {/* Delete Account (required for App Store) */}
        <TouchableOpacity
          onPress={handleDeleteAccount}
          disabled={deleting}
          className="mt-3 py-3 flex-row items-center justify-center gap-2"
          activeOpacity={0.7}
        >
          {deleting
            ? <ActivityIndicator size="small" color="#9ca3af" />
            : <Trash2 size={14} color="#9ca3af" />}
          <Text className="text-[13px] font-body-medium text-gray-400">
            {deleting ? 'Deleting…' : 'Delete account'}
          </Text>
        </TouchableOpacity>

        <View className="items-center mt-8 gap-1.5">
          <FinchLogo size={18} />
          <Text className="text-[11px] font-body text-gray-300">v1.0.0</Text>
        </View>
      </ScrollView>

      <ApiKeysModal
        visible={showApiKeyModal}
        onClose={() => setShowApiKeyModal(false)}
        apiKeys={apiKeys}
        userId={user?.id || ''}
        onKeysChanged={(keys) => setApiKeys(keys)}
        onDelete={deleteApiKey}
      />

      <PaywallModal
        visible={showPaywall}
        onClose={() => setShowPaywall(false)}
        onPurchased={refreshBalance}
      />
    </SafeAreaView>
  );
}

function ApiKeysModal({ visible, onClose, apiKeys, userId, onKeysChanged, onDelete }: {
  visible: boolean; onClose: () => void; apiKeys: ApiKeyEntry[]; userId: string;
  onKeysChanged: (keys: ApiKeyEntry[]) => void; onDelete: (service: string) => void;
}) {
  const [service, setService] = useState('');
  const [keyId, setKeyId] = useState('');
  const [privateKey, setPrivateKey] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!service.trim() || !keyId.trim()) return;
    setSaving(true);
    try {
      const credentials: Record<string, string> = { api_key_id: keyId };
      if (privateKey.trim()) credentials.private_key = privateKey;
      await apiKeysApi.saveKey(userId, service, credentials);
      const data = await apiKeysApi.getKeys(userId);
      onKeysChanged(data.keys || []);
      setService(''); setKeyId(''); setPrivateKey('');
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch {
      Alert.alert('Error', 'Failed to save API key');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View className="flex-1 justify-end bg-black/40">
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-lg font-body-bold text-gray-900">API Keys</Text>
            <TouchableOpacity onPress={onClose} className="p-1"><X size={20} color="#9ca3af" /></TouchableOpacity>
          </View>

          {apiKeys.length > 0 && (
            <View className="mb-4">
              {apiKeys.map((key) => (
                <View key={key.service} className="flex-row items-center justify-between py-2.5 border-b border-gray-100">
                  <View>
                    <Text className="text-[13px] font-body-medium text-gray-900 capitalize">{key.service}</Text>
                    <Text className="text-[11px] font-body text-gray-400">{key.api_key_id_masked}</Text>
                  </View>
                  <View className="flex-row items-center gap-2">
                    <Check size={13} color={COLORS.emerald} />
                    <TouchableOpacity onPress={() => onDelete(key.service)} className="p-1">
                      <Trash2 size={13} color="#d1d5db" />
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </View>
          )}

          <Text className="text-[13px] font-body-bold text-gray-900 mb-2.5">Add Key</Text>
          <TextInput value={service} onChangeText={setService} placeholder="Service (e.g., kalshi)" placeholderTextColor="#d1d5db" autoCapitalize="none" style={styles.textInput} />
          <TextInput value={keyId} onChangeText={setKeyId} placeholder="API Key ID" placeholderTextColor="#d1d5db" autoCapitalize="none" style={styles.textInput} />
          <TextInput value={privateKey} onChangeText={setPrivateKey} placeholder="Private Key (optional)" placeholderTextColor="#d1d5db" autoCapitalize="none" secureTextEntry style={[styles.textInput, { marginBottom: 14 }]} />
          <TouchableOpacity
            onPress={handleSave}
            disabled={saving || !service.trim() || !keyId.trim()}
            style={[styles.saveBtn, (!service.trim() || !keyId.trim() || saving) && { opacity: 0.5 }]}
            activeOpacity={0.8}
          >
            {saving ? <ActivityIndicator color="#fff" /> : <Text className="text-white font-body-medium text-[13px]">Save Key</Text>}
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  menuCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    overflow: 'hidden',
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#f3f4f6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  proBadge: {
    backgroundColor: '#059669',
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  proBadgeText: {
    fontSize: 9,
    fontFamily: 'DMSans-Bold',
    color: '#fff',
    letterSpacing: 0.5,
  },
  upgradeBtn: {
    backgroundColor: '#059669',
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 7,
  },
  upgradeBtnText: {
    fontSize: 12,
    fontFamily: 'DMSans-Bold',
    color: '#fff',
  },
  sheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: 20,
    paddingBottom: 32,
    paddingTop: 12,
    maxHeight: '80%',
  },
  handle: {
    width: 36,
    height: 4,
    backgroundColor: '#e5e7eb',
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 16,
  },
  textInput: {
    backgroundColor: '#f9fafb',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 13,
    fontFamily: 'DMSans',
    color: '#111827',
    borderWidth: 1,
    borderColor: '#f3f4f6',
    marginBottom: 8,
  },
  saveBtn: {
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: 'center',
    backgroundColor: '#111827',
  },
  timeChip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#e7e5e4',
    backgroundColor: '#fff',
  },
  timeChipActive: {
    borderColor: '#059669',
    backgroundColor: '#ecfdf5',
  },
  timeChipText: {
    fontSize: 12,
    fontFamily: 'DMSans-Medium',
    color: '#6b7280',
  },
  timeChipTextActive: {
    color: '#059669',
  },
});
