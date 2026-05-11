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
        {/* Hero */}
        <div className="flex flex-col items-center pt-20 pb-12 px-4">
          <div className="flex items-center gap-3 mb-4">
            <img src="/logo.svg" alt="Finch" className="w-12 h-12 rounded-xl" />
            <h1 className="text-5xl font-bold text-gray-900">Finch</h1>
          </div>
          <p className="text-xl text-gray-600 mb-3">Your AI Financial Assistant</p>
          <p className="text-gray-500 max-w-xl text-center">
            Chat with an AI that can research markets, analyze SEC filings,
            build trading bots, and execute trades on your behalf — all in one place.
          </p>
        </div>

        {/* Features */}
        <div className="max-w-4xl mx-auto px-4 pb-12">
          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">AI Chat</h3>
              <p className="text-sm text-gray-500">
                Ask anything about markets, stocks, or trading strategies. Finch searches the web,
                reads SEC filings, and analyzes financials to give you informed answers.
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">Trading Bots</h3>
              <p className="text-sm text-gray-500">
                Build autonomous trading bots that monitor markets, follow your strategy,
                and execute trades 24/7. Set risk rules, review trades, and track P&L.
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">Portfolio Tracking</h3>
              <p className="text-sm text-gray-500">
                Connect your brokerage account to view positions, track performance,
                and get AI-powered insights on your holdings.
              </p>
            </div>
          </div>
        </div>

        {/* Example flows */}
        <div className="max-w-3xl mx-auto px-4 pb-12">
          <h2 className="text-lg font-semibold text-gray-800 text-center mb-6">What you can do with Finch</h2>
          <div className="space-y-4">
            <div className="bg-white rounded-xl p-5 shadow-sm border-l-4 border-blue-500">
              <p className="text-sm font-medium text-gray-800">&ldquo;What are the top insider buys this week?&rdquo;</p>
              <p className="text-xs text-gray-500 mt-1">Finch scans insider trading data and surfaces the most notable purchases by company executives.</p>
            </div>
            <div className="bg-white rounded-xl p-5 shadow-sm border-l-4 border-green-500">
              <p className="text-sm font-medium text-gray-800">&ldquo;Build me a bot that buys NVDA on dips below the 20-day moving average&rdquo;</p>
              <p className="text-xs text-gray-500 mt-1">Finch creates a trading bot with your strategy, sets up risk rules, and runs it on a schedule. You approve every trade before it executes.</p>
            </div>
            <div className="bg-white rounded-xl p-5 shadow-sm border-l-4 border-purple-500">
              <p className="text-sm font-medium text-gray-800">&ldquo;Analyze Apple&apos;s latest 10-Q and compare margins to last year&rdquo;</p>
              <p className="text-xs text-gray-500 mt-1">Finch pulls the SEC filing, extracts financial data, and gives you a side-by-side margin comparison with citations.</p>
            </div>
            <div className="bg-white rounded-xl p-5 shadow-sm border-l-4 border-amber-500">
              <p className="text-sm font-medium text-gray-800">&ldquo;What&apos;s the sentiment on prediction markets for the Fed rate decision?&rdquo;</p>
              <p className="text-xs text-gray-500 mt-1">Finch checks Kalshi and Polymarket for real-time odds and summarizes what markets are pricing in.</p>
            </div>
          </div>
        </div>

        {/* Sign in */}
        <div className="flex justify-center px-4 pb-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
            <h2 className="text-lg font-semibold text-gray-800 text-center mb-6">Get started for free</h2>
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
        </div>

        <footer className="py-8 text-center text-xs text-gray-400">
          <a href="/privacy" className="hover:text-gray-600 underline">Privacy Policy</a>
          <span className="mx-2">·</span>
          <span>contact: anshul.tibrewal2203@gmail.com</span>
        </footer>
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

