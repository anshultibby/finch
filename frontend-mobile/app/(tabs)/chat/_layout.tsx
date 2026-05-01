import { Stack } from 'expo-router';

export default function ChatLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen
        name="[id]"
        options={{
          headerShown: true,
          headerTitle: 'Chat',
          headerBackTitle: 'Back',
          headerStyle: { backgroundColor: '#fafaf9' },
          headerShadowVisible: false,
          headerTintColor: '#0f172a',
        }}
      />
    </Stack>
  );
}
