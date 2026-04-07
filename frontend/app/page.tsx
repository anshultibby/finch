'use client';

import AuthGate from '@/components/PasswordGate';
import AppLayout from '@/components/layout/AppLayout';

export default function Home() {
  return (
    <AuthGate>
      <AppLayout />
    </AuthGate>
  );
}
