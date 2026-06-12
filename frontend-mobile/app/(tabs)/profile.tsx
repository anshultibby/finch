import { View, Text, TouchableOpacity, ScrollView, Alert, StyleSheet, Platform, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { useState, useEffect } from 'react';
import { creditsApi, accountApi } from '@/lib/api';
import { CreditCard, LogOut, ChevronRight, Key, Shield, Bell, Trash2 } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import FinchLogo from '@/components/FinchLogo';
import SignInPrompt from '@/components/SignInPrompt';

export default function ProfileScreen() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [credits, setCredits] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (user) {
      creditsApi.getBalance(user.id)
        .then(data => setCredits(data.credits))
        .catch(() => {});
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

  if (!user) {
    return (
      <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={['top']}>
        <View className="px-4 h-11 justify-center">
          <Text className="text-base font-body-bold text-gray-900">Profile</Text>
        </View>
        <SignInPrompt
          title="Create your Finch account"
          description="Sign in to manage your watchlist, portfolio connections, and notification settings."
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={['top']}>
      <ScrollView contentContainerClassName="pb-8">
        <View className="px-4 h-11 justify-center">
          <Text className="text-base font-body-bold text-gray-900">Profile</Text>
        </View>

        {/* User Card */}
        <View className="mx-4 mb-5 mt-1">
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

        {/* Menu Items */}
        <View style={styles.menuGroup} className="mx-4 mb-3">
          <MenuItem
            icon={<CreditCard size={17} color="#6b7280" />}
            label="Credits"
            detail={credits !== null ? `${credits.toLocaleString()} remaining` : '...'}
          />
          <MenuItem
            icon={<Key size={17} color="#6b7280" />}
            label="API Keys"
            detail="Manage"
            onPress={() => router.push('/settings')}
          />
          <MenuItem
            icon={<Bell size={17} color="#6b7280" />}
            label="Notifications"
            detail="Push & email"
            onPress={() => router.push('/notification-settings')}
            isLast
          />
        </View>

        <View style={styles.menuGroup} className="mx-4 mb-3">
          <MenuItem
            icon={<Shield size={17} color="#6b7280" />}
            label="Privacy & Security"
            onPress={() => router.push('/privacy')}
            isLast
          />
        </View>

        {/* Sign Out */}
        <TouchableOpacity
          onPress={handleSignOut}
          className="mx-4 rounded-xl border border-gray-100 py-3 flex-row items-center justify-center gap-2"
          activeOpacity={0.7}
        >
          <LogOut size={15} color="#ef4444" />
          <Text className="text-[13px] font-body-medium text-red-500">Sign Out</Text>
        </TouchableOpacity>

        {/* Delete Account (required for App Store) */}
        <TouchableOpacity
          onPress={handleDeleteAccount}
          disabled={deleting}
          className="mx-4 mt-3 py-3 flex-row items-center justify-center gap-2"
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
    </SafeAreaView>
  );
}

function MenuItem({ icon, label, detail, onPress, isLast }: {
  icon: React.ReactNode;
  label: string;
  detail?: string;
  onPress?: () => void;
  isLast?: boolean;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      className={`flex-row items-center gap-3 px-3.5 py-3 ${!isLast ? 'border-b border-gray-100' : ''}`}
      activeOpacity={0.6}
      disabled={!onPress}
    >
      {icon}
      <Text className="flex-1 text-[14px] font-body-medium text-gray-900">{label}</Text>
      {detail && <Text className="text-[12px] font-body text-gray-400 mr-1">{detail}</Text>}
      <ChevronRight size={15} color="#d1d5db" />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#f3f4f6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuGroup: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    backgroundColor: '#fff',
    overflow: 'hidden',
  },
});
