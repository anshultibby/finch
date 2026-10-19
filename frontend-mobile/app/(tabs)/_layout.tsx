import React from 'react';
import { View, ActivityIndicator } from 'react-native';
import { Stack } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';

export default function MainLayout() {
  const { loading } = useAuth();

  if (loading) {
    return (
      <View className="flex-1 items-center justify-center bg-white">
        <ActivityIndicator color="#9ca3af" />
      </View>
    );
  }

  // No auth wall here: guests may browse markets, news, and stock pages
  // (App Store guideline 5.1.1). Account-based screens render SignInPrompt.
  // Navigation is the home cards — no drawer, no tab bar.
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="chat" />
    </Stack>
  );
}
