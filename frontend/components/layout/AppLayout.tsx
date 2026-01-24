'use client';

import React, { ReactNode } from 'react';
import ProfileDropdown from '../ProfileDropdown';
import AccountManagementModal from '../AccountManagementModal';
import { useAuth } from '@/contexts/AuthContext';
import { snaptradeApi } from '@/lib/api';

interface AppLayoutProps {
  chatView: ReactNode;
}

export default function AppLayout({ 
  chatView,
}: AppLayoutProps) {
  const { user } = useAuth();
  const [showAccountModal, setShowAccountModal] = React.useState(false);
  const [isPortfolioConnected, setIsPortfolioConnected] = React.useState(false);

  // Check portfolio connection on mount
  React.useEffect(() => {
    const checkConnection = async () => {
      if (!user?.id) return;
      
      try {
        const status = await snaptradeApi.checkStatus(user.id);
        setIsPortfolioConnected(status.is_connected);
      } catch (err) {
        console.error('Error checking connection:', err);
      }
    };
    
    checkConnection();
  }, [user?.id]);

  return (
    <div className="flex flex-col h-screen">
      {/* Header - Mobile optimized with safe area support */}
      <div className="bg-white border-b border-gray-200 px-3 sm:px-6 py-2 safe-area-top">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex-shrink-0">
            <h1 className="text-base sm:text-lg font-bold text-gray-900">Finch</h1>
            <p className="text-[10px] sm:text-xs text-gray-500 hidden xs:block">Your AI Trading Assistant</p>
          </div>

          {/* Spacer */}
          <div className="flex-1 min-w-2" />

          {/* Actions */}
          <div className="flex items-center gap-1.5 sm:gap-2">
            {/* Manage Accounts Button */}
            <button
              onClick={() => setShowAccountModal(true)}
              className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg font-medium bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white transition-all text-xs touch-manipulation"
              style={{ minHeight: '44px', minWidth: '44px' }}
            >
              <span className="text-sm">🏦</span>
              <span className="hidden xs:inline">Accounts</span>
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

      {/* Account Management Modal */}
      <AccountManagementModal
        isOpen={showAccountModal}
        onClose={() => setShowAccountModal(false)}
        onConnectionChange={async () => {
          if (user?.id) {
            try {
              const status = await snaptradeApi.checkStatus(user.id);
              setIsPortfolioConnected(status.is_connected);
            } catch (err) {
              console.error('Error checking connection status:', err);
            }
          }
        }}
      />
    </div>
  );
}

