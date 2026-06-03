'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface AuthGateProps {
  children: React.ReactNode;
}

const prompts = [
  'Is NVDA overvalued right now?',
  'Build me a momentum bot for tech stocks',
  'Who bought their own stock this week?',
  'Compare Apple and Microsoft margins',
  'What are prediction markets pricing for the Fed?',
  'Show me my biggest winners this month',
];

export default function AuthGate({ children }: AuthGateProps) {
  const { user, loading, signInWithGoogle, signInWithEmail, signUpWithEmail } = useAuth();
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState('');
  const [currentPrompt, setCurrentPrompt] = useState(0);
  const [displayText, setDisplayText] = useState('');
  const [typing, setTyping] = useState(true);
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (user) return;
    const full = prompts[currentPrompt];
    if (typing) {
      if (displayText.length < full.length) {
        const timeout = setTimeout(() => setDisplayText(full.slice(0, displayText.length + 1)), 40);
        return () => clearTimeout(timeout);
      } else {
        const timeout = setTimeout(() => setTyping(false), 2000);
        return () => clearTimeout(timeout);
      }
    } else {
      if (displayText.length > 0) {
        const timeout = setTimeout(() => setDisplayText(displayText.slice(0, -1)), 20);
        return () => clearTimeout(timeout);
      } else {
        setCurrentPrompt((prev) => (prev + 1) % prompts.length);
        setTyping(true);
      }
    }
  }, [displayText, typing, currentPrompt, user]);

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

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    try {
      setSigningIn(true);
      setError('');
      setMessage('');
      if (mode === 'signup') {
        const { needsConfirmation } = await signUpWithEmail(email, password);
        if (needsConfirmation) {
          setMessage('Account created. Check your email to confirm, then sign in.');
          setMode('signin');
        }
      } else {
        await signInWithEmail(email, password);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to authenticate');
    } finally {
      setSigningIn(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-teal-50">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 flex flex-col">
        {/* Nav */}
        <nav className="flex items-center px-6 py-5">
          <div className="flex items-center gap-2.5">
            <img src="/logo.svg" alt="Finch" className="w-8 h-8 rounded-lg" />
            <span className="text-lg font-semibold tracking-tight text-gray-900">Finch</span>
          </div>
        </nav>

        {/* Hero */}
        <div className="flex-1 flex flex-col items-center justify-center px-4 -mt-16">
          <h1 className="text-5xl sm:text-7xl font-bold tracking-tight text-center max-w-3xl leading-[1.1] text-gray-900">
            Bloomberg Terminal<br />
            <span className="bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent">for pennies</span>
          </h1>

          <div className="flex items-center gap-6 mt-6 text-sm text-gray-500">
            <span>Real-time portfolio sync</span>
            <span className="text-gray-300">|</span>
            <span>Built-in code sandbox</span>
            <span className="text-gray-300">|</span>
            <span>Multi-hour research tasks</span>
          </div>

          {/* Fake chat input */}
          <div className="mt-10 w-full max-w-xl">
            <div className="bg-white/70 backdrop-blur border border-gray-200 rounded-2xl px-5 py-4 shadow-sm flex items-center gap-3">
              <div className="flex-1 text-gray-400 text-[15px] font-mono truncate">
                {displayText}
                <span className="inline-block w-[2px] h-4 bg-emerald-500 ml-0.5 animate-pulse align-middle" />
              </div>
            </div>
          </div>

          {/* CTA */}
          <button
            onClick={handleGoogleSignIn}
            disabled={signingIn}
            className="mt-6 bg-gray-900 text-white font-semibold py-3 px-8 rounded-full flex items-center gap-3 hover:bg-gray-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-[15px] shadow-lg"
          >
            <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            {signingIn ? 'Signing in...' : 'Start with Google'}
          </button>

          {/* Email / password */}
          <div className="mt-6 w-full max-w-xs">
            <div className="flex items-center gap-3 mb-4">
              <div className="h-px bg-gray-200 flex-1" />
              <span className="text-xs text-gray-400">or</span>
              <div className="h-px bg-gray-200 flex-1" />
            </div>

            <form onSubmit={handleEmailSubmit} className="flex flex-col gap-2.5">
              <input
                type="email"
                autoComplete="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-gray-200 bg-white/70 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
              <input
                type="password"
                autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-gray-200 bg-white/70 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
              <button
                type="submit"
                disabled={signingIn}
                className="w-full rounded-full bg-emerald-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
              >
                {signingIn ? 'Please wait…' : mode === 'signup' ? 'Create account' : 'Sign in'}
              </button>
            </form>

            <p className="mt-3 text-center text-xs text-gray-500">
              {mode === 'signup' ? 'Already have an account?' : "Don't have an account?"}{' '}
              <button
                type="button"
                onClick={() => {
                  setMode(mode === 'signup' ? 'signin' : 'signup');
                  setError('');
                  setMessage('');
                }}
                className="font-semibold text-emerald-600 hover:text-emerald-700"
              >
                {mode === 'signup' ? 'Sign in' : 'Sign up'}
              </button>
            </p>
          </div>

          {error && (
            <p className="text-red-500 text-sm mt-3">{error}</p>
          )}
          {message && (
            <p className="text-emerald-700 text-sm mt-3">{message}</p>
          )}

          <p className="text-gray-400 text-xs mt-4">Free to sign up. No credit card.</p>
        </div>

        {/* Footer */}
        <footer className="py-6 text-center text-xs text-gray-400 space-x-4">
          <a href="/privacy" className="hover:text-gray-600 transition-colors">Privacy Policy</a>
          <a href="/contact" className="hover:text-gray-600 transition-colors">Contact Us</a>
        </footer>
      </div>
    );
  }

  return <>{children}</>;
}

