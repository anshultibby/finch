'use client';

import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface AuthGateProps {
  children: React.ReactNode;
}

export default function AuthGate({ children }: AuthGateProps) {
  const { user, loading, signInWithGoogle } = useAuth();
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState('');

  const handleGoogleSignIn = async () => {
    try {
      setSigningIn(true);
      setError('');
      await signInWithGoogle();
    } catch (err: any) {
      setError(err.message || 'Failed to sign in');
      setSigningIn(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        {/* Hero section */}
        <div className="flex flex-col items-center justify-center min-h-screen p-4">
          <div className="text-center mb-10 max-w-2xl">
            <div className="flex items-center justify-center gap-3 mb-4">
              <img src="/logo.svg" alt="Finch" className="w-12 h-12 rounded-xl" />
              <h1 className="text-5xl font-bold text-gray-900">Finch</h1>
            </div>
            <p className="text-xl text-gray-600 mb-6">Your AI Financial Assistant</p>
            <p className="text-gray-500 max-w-lg mx-auto">
              Research markets, build automated trading bots, and manage your portfolio —
              all powered by AI. Connect your brokerage and let Finch do the heavy lifting.
            </p>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
            <h2 className="text-lg font-semibold text-gray-800 text-center mb-6">Get started</h2>
            <div className="space-y-4">
              <button
                onClick={handleGoogleSignIn}
                disabled={signingIn}
                className="w-full bg-white hover:bg-gray-50 text-gray-700 font-semibold py-3 px-6 rounded-lg border-2 border-gray-300 transition-colors flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                {signingIn ? 'Signing in...' : 'Continue with Google'}
              </button>

              {error && (
                <p className="text-red-500 text-sm text-center mt-4">{error}</p>
              )}
            </div>

            <p className="text-xs text-gray-500 text-center mt-6">
              By signing in, you agree to our{' '}
              <a href="/privacy" className="underline hover:text-gray-700">Privacy Policy</a>
            </p>
          </div>

          <footer className="mt-12 text-center text-xs text-gray-400">
            <a href="/privacy" className="hover:text-gray-600 underline">Privacy Policy</a>
            <span className="mx-2">·</span>
            <span>contact: anshul.tibrewal2203@gmail.com</span>
          </footer>
        </div>
      </div>
    );
  }

  return (
    <div>
      {children}
      {/* Optional: Add a sign out button somewhere accessible */}
    </div>
  );
}

