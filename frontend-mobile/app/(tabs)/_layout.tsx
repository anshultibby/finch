import React from 'react';
import { View, ActivityIndicator } from 'react-native';
import { Redirect, Stack } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { DrawerProvider } from '@/contexts/DrawerContext';
import Sidebar from '@/components/Sidebar';

export default function MainLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View className="flex-1 items-center justify-center bg-white">
        <ActivityIndicator color="#9ca3af" />
      </View>
    );
  }

  if (!user) {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <DrawerProvider>
      <View style={{ flex: 1 }}>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="chat" />
          <Stack.Screen name="profile" />
          <Stack.Screen name="watchlist" />
        </Stack>
        <Sidebar />
      </View>
    </DrawerProvider>
  );
}
