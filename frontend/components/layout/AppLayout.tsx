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


  return (
    <div className="flex flex-col h-screen">
      {/* Header - Mobile optimized with safe area support */}
      <div className="bg-white border-b border-gray-200 px-3 sm:px-6 py-2 safe-area-top">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <button 
            onClick={() => router.push('/')}
            className="flex-shrink-0 text-left hover:opacity-80 transition-opacity"
          >
            <h1 className="text-base sm:text-lg font-bold text-gray-900">Finch</h1>
            <p className="text-[10px] sm:text-xs text-gray-500 hidden xs:block">Your AI Trading Assistant</p>
          </button>

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
              <span className="text-sm">📊</span>
              <span className="hidden xs:inline">Portfolio</span>
            </button>

            {/* Strategies Link */}
            <button
              onClick={() => router.push('/strategies')}
              className={`flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg font-medium transition-all text-xs touch-manipulation ${
                pathname === '/strategies'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
              }`}
              style={{ minHeight: '44px', minWidth: '44px' }}
            >
              <span className="text-sm">🤖</span>
              <span className="hidden xs:inline">Bots</span>
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

