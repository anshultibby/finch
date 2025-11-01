'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    const handleCallback = async () => {
      // The session is automatically handled by Supabase
      // Just redirect back to home
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session) {
        router.push('/');
      } else {
        router.push('/');
      }
    };

    handleCallback();
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-gray-600">Completing sign in...</div>
    </div>
  );
}

