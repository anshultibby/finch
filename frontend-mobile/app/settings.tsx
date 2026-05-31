import { View, Text, TouchableOpacity, ScrollView, Alert, TextInput, ActivityIndicator, Modal, StyleSheet, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { useState, useEffect } from 'react';
import { creditsApi, apiKeysApi } from '@/lib/api';
import { CreditCard, LogOut, ChevronRight, Key, Shield, Bell, X, Check, Trash2 } from 'lucide-react-native';
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
  const [credits, setCredits] = useState<number | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKeyEntry[]>([]);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);

  useEffect(() => {
    if (user) {
      creditsApi.getBalance(user.id).then(data => setCredits(data.credits)).catch(() => {});
      apiKeysApi.getKeys(user.id).then(data => setApiKeys(data.keys || [])).catch(() => {});
    }
  }, [user]);

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

  return (
    <SafeAreaView className="flex-1 bg-white" edges={[]}>
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

        {/* Credits */}
        <View style={styles.menuCard} className="mb-3">
          <View className="p-3.5 flex-row items-center justify-between">
            <View className="flex-row items-center gap-3">
              <View style={[styles.iconBox, { backgroundColor: '#fffbeb' }]}>
                <CreditCard size={16} color="#d97706" />
              </View>
              <View>
                <Text className="text-[13px] font-body-medium text-gray-900">Credits</Text>
                <Text className="text-[11px] font-body text-gray-500">
                  {credits !== null ? `${credits.toLocaleString()} remaining` : 'Loading...'}
                </Text>
              </View>
            </View>
          </View>
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
});
