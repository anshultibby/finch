import { useCallback } from 'react';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useAuth } from '@/contexts/AuthContext';
import { chatApi } from '@/lib/api';

/**
 * Open a fresh chat, optionally auto-sending `seed` (the chat screen reads the
 * `seed` param). Guests are sent to login — chat is account-based.
 */
export function useStartChat() {
  const router = useRouter();
  const { user } = useAuth();

  return useCallback(async (seed?: string) => {
    if (!user) {
      router.push('/(auth)/login');
      return;
    }
    Haptics.selectionAsync();
    try {
      const chatId = await chatApi.createChat(user.id);
      router.push(
        seed
          ? `/(tabs)/chat/${chatId}?seed=${encodeURIComponent(seed)}`
          : `/(tabs)/chat/${chatId}`
      );
    } catch {}
  }, [user, router]);
}
