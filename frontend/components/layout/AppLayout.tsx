'use client';

import React, { ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import ProfileDropdown from '../ProfileDropdown';
import { useAuth } from '@/contexts/AuthContext';

interface AppLayoutProps {
  chatView: ReactNode;
}

export default function AppLayout({ 
  chatView,
}: AppLayoutProps) {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();


  // Determine if we're on a main nav page
  const isChat = pathname === '/';
  const isStrategies = pathname === '/strategies';
  const isPortfolio = pathname === '/portfolio';
  const showMainNav = isChat || isStrategies;

  return (
    <div className="flex flex-col h-screen">
      {/* Header - Mobile optimized with safe area support */}
      <div className="bg-white border-b border-gray-200 px-3 sm:px-6 py-2 safe-area-top">
        <div className="flex items-center justify-between gap-4">
          {/* Logo */}
          <button 
            onClick={() => router.push('/')}
            className="flex-shrink-0 text-left hover:opacity-80 transition-opacity"
          >
            <h1 className="text-base sm:text-lg font-bold text-gray-900">Finch</h1>
            <p className="text-[10px] sm:text-xs text-gray-500 hidden xs:block">Your AI Trading Assistant</p>
          </button>

          {/* Main Navigation - Center */}
          {showMainNav && (
            <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => router.push('/')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all ${
                  isChat
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span className="hidden sm:inline">Agent</span>
              </button>

              <button
                onClick={() => router.push('/strategies')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all ${
                  isStrategies
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span className="hidden sm:inline">Strategies</span>
              </button>
            </div>
          )}

          {/* Spacer */}
          <div className="flex-1 min-w-2" />

          {/* Actions */}
          <div className="flex items-center gap-1.5 sm:gap-2">
            {/* Portfolio Link */}
            <button
              onClick={() => router.push('/portfolio')}
              className={`flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg font-medium transition-all text-xs touch-manipulation ${
                pathname === '/portfolio'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
              }`}
              style={{ minHeight: '44px', minWidth: '44px' }}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span className="hidden xs:inline">Portfolio</span>
            </button>

            {/* Profile */}
            <div className="border-l pl-1.5 sm:pl-2 ml-1.5 sm:ml-2">
              <ProfileDropdown />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        {chatView}
      </div>
    </div>
  );
}

