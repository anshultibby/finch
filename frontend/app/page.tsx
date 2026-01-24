'use client';

import AuthGate from '@/components/PasswordGate';
import AppLayout from '@/components/layout/AppLayout';
import ChatView from '@/components/chat/ChatView';
import { NavigationProvider } from '@/contexts/NavigationContext';
import { ChatModeProvider } from '@/contexts/ChatModeContext';

export default function Home() {
  return (
    <AuthGate>
      <NavigationProvider>
        <ChatModeProvider>
          <main className="min-h-screen bg-gray-50">
            <AppLayout chatView={<ChatView />} />
          </main>
        </ChatModeProvider>
      </NavigationProvider>
    </AuthGate>
  );
}
