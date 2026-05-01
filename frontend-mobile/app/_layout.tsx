import '../global.css';
import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { AuthProvider } from '@/contexts/AuthContext';

export { ErrorBoundary } from 'expo-router';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  useEffect(() => {
    SplashScreen.hideAsync();
  }, []);

  return (
    <AuthProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="stock/[symbol]"
          options={{
            headerShown: true,
            headerBackTitle: 'Back',
            headerStyle: { backgroundColor: '#fafaf9' },
            headerShadowVisible: false,
          }}
        />
        <Stack.Screen
          name="orders"
          options={{
            headerShown: true,
            headerTitle: 'Orders',
            headerBackTitle: 'Back',
            headerStyle: { backgroundColor: '#fafaf9' },
            headerShadowVisible: false,
          }}
        />
        <Stack.Screen
          name="settings"
          options={{
            headerShown: true,
            headerTitle: 'Settings',
            headerBackTitle: 'Back',
            headerStyle: { backgroundColor: '#fafaf9' },
            headerShadowVisible: false,
          }}
        />
      </Stack>
      <StatusBar style="dark" />
    </AuthProvider>
  );
}
