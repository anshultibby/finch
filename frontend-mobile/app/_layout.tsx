import '../global.css';
import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { useFonts } from 'expo-font';
import { AuthProvider } from '@/contexts/AuthContext';

export { ErrorBoundary } from 'expo-router';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  // The whole UI is styled with the DMSans family (font-body / DMSans-* in
  // styles). These must be registered at runtime or every label silently
  // falls back to the platform serif/sans default.
  const [fontsLoaded, fontError] = useFonts({
    DMSans: require('../assets/fonts/DMSans-Regular.ttf'),
    'DMSans-Medium': require('../assets/fonts/DMSans-Medium.ttf'),
    'DMSans-Bold': require('../assets/fonts/DMSans-Bold.ttf'),
    SpaceMono: require('../assets/fonts/SpaceMono-Regular.ttf'),
  });

  useEffect(() => {
    if (fontsLoaded || fontError) SplashScreen.hideAsync();
  }, [fontsLoaded, fontError]);

  // Hold on the splash until fonts resolve so we never flash the fallback face.
  if (!fontsLoaded && !fontError) return null;

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
          name="settings"
          options={{
            headerShown: true,
            headerTitle: 'Settings',
            headerBackTitle: 'Back',
            headerStyle: { backgroundColor: '#fafaf9' },
            headerShadowVisible: false,
          }}
        />
        <Stack.Screen
          name="privacy"
          options={{
            headerShown: true,
            headerTitle: 'Privacy & Security',
            headerBackTitle: 'Back',
            headerStyle: { backgroundColor: '#fafaf9' },
            headerShadowVisible: false,
          }}
        />
        <Stack.Screen
          name="notification-settings"
          options={{
            headerShown: true,
            headerTitle: 'Notifications',
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
