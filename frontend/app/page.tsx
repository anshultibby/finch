'use client';

import AuthGate from '@/components/PasswordGate';
import AppLayout from '@/components/layout/AppLayout';
import { NavigationProvider } from '@/contexts/NavigationContext';
import { ChatModeProvider } from '@/contexts/ChatModeContext';

export default function Home() {
  return (
    <AuthGate>
      <NavigationProvider>
        <ChatModeProvider>
          <AppLayout />
        </ChatModeProvider>
      </NavigationProvider>
    </AuthGate>
  );
}
