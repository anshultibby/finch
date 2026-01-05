'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { snaptradeApi } from '@/lib/api';
import type { BrokerageAccount, Brokerage } from '@/lib/types';

interface AccountManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnectionChange?: () => void;
}

export default function AccountManagementModal({ isOpen, onClose, onConnectionChange }: AccountManagementModalProps) {
  const { user } = useAuth();
  const [accounts, setAccounts] = useState<BrokerageAccount[]>([]);
  const [brokerages, setBrokerages] = useState<Brokerage[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [selectedBroker, setSelectedBroker] = useState<string | null>(null);
  const [showBrokerList, setShowBrokerList] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && user?.id) {
      loadData();
    }
  }, [isOpen, user?.id]);

  const loadData = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const [accountsResponse, brokeragesResponse] = await Promise.all([
        snaptradeApi.getAccounts(user.id),
        snaptradeApi.getBrokerages(),
      ]);
      
      if (accountsResponse.success) {
        setAccounts(accountsResponse.accounts);
      }
      
      if (brokeragesResponse.success) {
        setBrokerages(brokeragesResponse.brokerages);
      }
    } catch (err) {
      console.error('Error loading account data:', err);
      setError('Failed to load account data');
    } finally {
      setLoading(false);
    }
  };

  const handleConnectBroker = async (brokerId: string) => {
    if (!user?.id) return;
    
    setConnecting(true);
    setSelectedBroker(brokerId);
    setError(null);
    
    try {
      const redirectUri = `${window.location.origin}${window.location.pathname}?snaptrade_callback=true`;
      const response = await snaptradeApi.connectBroker(user.id, redirectUri, brokerId);
      
      if (response.success && response.redirect_uri) {
        // Open popup for connection
        const width = 500;
        const height = 700;
        const left = (window.screen.width - width) / 2;
        const top = (window.screen.height - height) / 2;
        
        const popup = window.open(
          response.redirect_uri,
          'SnapTrade Connection',
          `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );
        
        if (!popup || popup.closed) {
          setError('Popup was blocked. Please allow popups for this site.');
          setConnecting(false);
          return;
        }
        
        // Wait for callback message
        const handleMessage = (event: MessageEvent) => {
          if (event.origin !== window.location.origin) return;
          
          if (event.data.type === 'SNAPTRADE_CONNECTION') {
            window.removeEventListener('message', handleMessage);
            setConnecting(false);
            setSelectedBroker(null);
            setShowBrokerList(false);
            
            if (event.data.success) {
              loadData(); // Reload accounts
              onConnectionChange?.();
            } else {
              setError(event.data.message || 'Connection failed');
            }
          }
        };
        
        window.addEventListener('message', handleMessage);
        
        // Cleanup on modal close or timeout
        setTimeout(() => {
          window.removeEventListener('message', handleMessage);
          if (connecting) {
            setConnecting(false);
            setSelectedBroker(null);
          }
        }, 300000); // 5 minute timeout
      } else {
        setError(response.message || 'Failed to initiate connection');
        setConnecting(false);
        setSelectedBroker(null);
      }
    } catch (err: any) {
      console.error('Error connecting broker:', err);
      setError(err.message || 'Failed to connect broker');
      setConnecting(false);
      setSelectedBroker(null);
    }
  };

  const handleDisconnectAccount = async (accountId: string, accountName: string) => {
    if (!user?.id) return;
    
    if (!confirm(`Are you sure you want to disconnect ${accountName}?`)) {
      return;
    }
    
    try {
      const response = await snaptradeApi.disconnectAccount(user.id, accountId);
      
      if (response.success) {
        await loadData(); // Reload accounts
        onConnectionChange?.();
      } else {
        setError(response.message || 'Failed to disconnect account');
      }
    } catch (err: any) {
      console.error('Error disconnecting account:', err);
      setError(err.message || 'Failed to disconnect account');
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-5 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Account Management</h2>
            <p className="text-blue-100 text-sm mt-1">Manage your connected brokerage accounts</p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <>
              {/* Connected Accounts */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Connected Accounts</h3>
                  <button
                    onClick={() => setShowBrokerList(!showBrokerList)}
                    disabled={connecting}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Connect Account
                  </button>
                </div>

                {accounts.length === 0 ? (
                  <div className="text-center py-12 bg-gray-50 rounded-lg">
                    <div className="text-5xl mb-4">🔗</div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No Connected Accounts</h3>
                    <p className="text-gray-600 mb-4">
                      Connect your brokerage account to get started
                    </p>
                    <button
                      onClick={() => setShowBrokerList(true)}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                    >
                      Connect Your First Account
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {accounts.map((account) => (
                      <div
                        key={account.id}
                        className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <div className="text-2xl">{brokerages.find(b => b.id === account.broker_id)?.logo || '🏦'}</div>
                              <div>
                                <h4 className="font-semibold text-gray-900">{account.name}</h4>
                                <p className="text-sm text-gray-600">{account.broker_name}</p>
                              </div>
                            </div>
                            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mt-3">
                              <div>
                                <span className="text-gray-500">Account Number:</span>
                                <span className="ml-2 font-medium">{account.number || 'N/A'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Type:</span>
                                <span className="ml-2 font-medium">{account.type}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Balance:</span>
                                <span className="ml-2 font-medium text-green-600">{formatCurrency(account.balance)}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Connected:</span>
                                <span className="ml-2 font-medium">{formatDate(account.connected_at)}</span>
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={() => handleDisconnectAccount(account.account_id, account.name)}
                            className="ml-4 text-red-600 hover:text-red-700 hover:bg-red-50 px-3 py-2 rounded-lg transition-colors text-sm font-medium"
                          >
                            Disconnect
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Broker Selection */}
              {showBrokerList && (
                <div className="border-t pt-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">Select a Broker</h3>
                    <button
                      onClick={() => setShowBrokerList(false)}
                      className="text-gray-500 hover:text-gray-700 text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {brokerages.map((broker) => (
                      <button
                        key={broker.id}
                        onClick={() => handleConnectBroker(broker.id)}
                        disabled={connecting && selectedBroker !== broker.id}
                        className={`flex items-center gap-3 p-4 border-2 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all ${
                          connecting && selectedBroker === broker.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200'
                        } ${
                          connecting && selectedBroker !== broker.id
                            ? 'opacity-50 cursor-not-allowed'
                            : ''
                        }`}
                      >
                        <span className="text-3xl">{broker.logo}</span>
                        <div className="flex-1 text-left">
                          <p className="font-semibold text-gray-900">{broker.name}</p>
                          {connecting && selectedBroker === broker.id && (
                            <p className="text-xs text-blue-600 mt-1">Connecting...</p>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                  <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-900">
                      <strong>Note:</strong> A popup window will open for secure authentication. 
                      Make sure popups are enabled for this site.
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t px-6 py-4 bg-gray-50 flex justify-between items-center">
          <p className="text-sm text-gray-600">
            Powered by <strong>SnapTrade</strong> • Secure OAuth Authentication
          </p>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

