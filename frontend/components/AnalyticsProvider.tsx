'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { initAnalytics, trackPageview, identifyUser } from '@/lib/analytics';

export default function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const pathname = usePathname();

  useEffect(() => {
    initAnalytics();
  }, []);

  useEffect(() => {
    if (pathname) trackPageview();
  }, [pathname]);

  useEffect(() => {
    if (user) identifyUser(user.id, { email: user.email });
  }, [user?.id]);

  return <>{children}</>;
}
