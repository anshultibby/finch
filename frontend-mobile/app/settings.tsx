import { View, Text, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { useState, useEffect } from 'react';
import { creditsApi } from '@/lib/api';
import { User, CreditCard, LogOut, ChevronRight, Shield, Bell } from 'lucide-react-native';
import FinchLogo from '@/components/FinchLogo';

export default function SettingsScreen() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [credits, setCredits] = useState<number | null>(null);

  useEffect(() => {
    if (user) {
      creditsApi.getBalance(user.id)
        .then(data => setCredits(data.credits))
        .catch(() => {});
    }
  }, [user]);

  const handleSignOut = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: signOut },
    ]);
  };

  return (
    <SafeAreaView className="flex-1 bg-finch-bg" edges={['top']}>
      <ScrollView contentContainerClassName="px-5 pb-8">
        <Text className="text-2xl font-body-bold text-slate-900 mt-2 mb-6">Settings</Text>

        {/* Profile */}
        <View className="bg-white rounded-2xl p-5 mb-4 border border-black/5">
          <View className="flex-row items-center gap-4">
            <View className="w-12 h-12 rounded-full bg-slate-100 items-center justify-center">
              <User size={24} color="#64748b" />
            </View>
            <View className="flex-1">
              <Text className="text-base font-body-medium text-slate-900">
                {user?.user_metadata?.full_name || 'User'}
              </Text>
              <Text className="text-sm font-body text-slate-500">
                {user?.email}
              </Text>
            </View>
          </View>
        </View>

        {/* Credits */}
        <View className="bg-white rounded-2xl border border-black/5 mb-4 overflow-hidden">
          <View className="p-4 flex-row items-center justify-between">
            <View className="flex-row items-center gap-3">
              <View className="w-9 h-9 rounded-lg bg-amber-50 items-center justify-center">
                <CreditCard size={18} color="#f59e0b" />
              </View>
              <View>
                <Text className="text-sm font-body-medium text-slate-900">Credits</Text>
                <Text className="text-xs font-body text-slate-500">
                  {credits !== null ? `${credits.toLocaleString()} remaining` : 'Loading...'}
                </Text>
              </View>
            </View>
            <ChevronRight size={18} color="#94a3b8" />
          </View>
        </View>

        {/* Account Actions */}
        <View className="bg-white rounded-2xl border border-black/5 mb-4 overflow-hidden">
          <TouchableOpacity
            className="p-4 flex-row items-center justify-between border-b border-black/5"
            activeOpacity={0.7}
          >
            <View className="flex-row items-center gap-3">
              <View className="w-9 h-9 rounded-lg bg-blue-50 items-center justify-center">
                <Bell size={18} color="#3b82f6" />
              </View>
              <Text className="text-sm font-body-medium text-slate-900">Notifications</Text>
            </View>
            <ChevronRight size={18} color="#94a3b8" />
          </TouchableOpacity>

          <TouchableOpacity
            className="p-4 flex-row items-center justify-between"
            activeOpacity={0.7}
          >
            <View className="flex-row items-center gap-3">
              <View className="w-9 h-9 rounded-lg bg-slate-50 items-center justify-center">
                <Shield size={18} color="#64748b" />
              </View>
              <Text className="text-sm font-body-medium text-slate-900">Privacy & Security</Text>
            </View>
            <ChevronRight size={18} color="#94a3b8" />
          </TouchableOpacity>
        </View>

        {/* Sign Out */}
        <TouchableOpacity
          onPress={handleSignOut}
          className="bg-white rounded-2xl p-4 border border-black/5 flex-row items-center justify-center gap-2"
          activeOpacity={0.8}
        >
          <LogOut size={18} color="#ef4444" />
          <Text className="text-sm font-body-medium text-red-500">Sign Out</Text>
        </TouchableOpacity>

        <View className="items-center mt-8 gap-2">
          <FinchLogo size={24} />
          <Text className="text-xs font-body text-slate-300">v1.0.0</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
