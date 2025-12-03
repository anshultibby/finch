'use client';

import React, { ReactNode } from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import TabNavigation from './TabNavigation';
import ProfileDropdown from '../ProfileDropdown';
import AccountManagementModal from '../AccountManagementModal';
import { useAuth } from '@/contexts/AuthContext';
import { snaptradeApi } from '@/lib/api';

interface AppLayoutProps {
  chatView: ReactNode;
  filesView: ReactNode;
  analyticsView: ReactNode;
}

export default function AppLayout({ 
  chatView,
  filesView,
  analyticsView 
}: AppLayoutProps) {
  const { currentView } = useNavigation();
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

  const getCurrentView = () => {
    switch (currentView) {
      case 'chat':
        return chatView;
      case 'files':
        return filesView;
      case 'analytics':
        return analyticsView;
      default:
        return chatView;
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-2">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div>
            <h1 className="text-lg font-bold text-gray-900">Finch</h1>
            <p className="text-xs text-gray-500">Your AI Trading Assistant</p>
          </div>

          {/* Tab Navigation */}
          <div className="flex-1 flex justify-center">
            <TabNavigation />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {/* Manage Accounts Button */}
            <button
              onClick={() => setShowAccountModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium bg-blue-600 hover:bg-blue-700 text-white transition-all text-xs"
            >
              <span className="text-sm">🏦</span>
              Accounts
            </button>

            {/* Profile */}
            <div className="border-l pl-2 ml-2">
              <ProfileDropdown />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        {getCurrentView()}
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

