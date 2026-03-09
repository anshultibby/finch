'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import AuthGate from '@/components/PasswordGate';
import { NavigationProvider } from '@/contexts/NavigationContext';
import { ChatModeProvider } from '@/contexts/ChatModeContext';
import BotView from '@/components/bots/BotView';

export default function BotPage() {
  const params = useParams();
  const botId = params.id as string;

  return (
    <AuthGate>
      <NavigationProvider>
        <ChatModeProvider>
          <BotView botId={botId} />
        </ChatModeProvider>
      </NavigationProvider>
    </AuthGate>
  );
}
