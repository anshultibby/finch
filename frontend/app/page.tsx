'use client';

import AuthGate from '@/components/PasswordGate';
import BotGrid from '@/components/bots/BotGrid';

export default function Home() {
  return (
    <AuthGate>
      <BotGrid />
    </AuthGate>
  );
}
