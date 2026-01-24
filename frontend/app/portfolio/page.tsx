'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { snaptradeApi } from '@/lib/api';
import type { PortfolioResponse, PortfolioPerformance, AccountDetail, Position, BrokerageAccount, Brokerage } from '@/lib/types';

export default function PortfolioPage() {
  const { user } = useAuth();
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [allAccounts, setAllAccounts] = useState<BrokerageAccount[]>([]);
  const [brokerages, setBrokerages] = useState<Brokerage[]>([]);
  const [loading, setLoading] = useState(true);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [showManageModal, setShowManageModal] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [selectedBroker, setSelectedBroker] = useState<string | null>(null);

  useEffect(() => {
    if (user?.id) {
      loadData();
    }
  }, [user?.id]);

  const loadData = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    try {
      const [portfolioData, performanceData, accountsResponse, brokeragesResponse] = await Promise.all([
        snaptradeApi.getPortfolio(user.id),
        snaptradeApi.getPortfolioPerformance(user.id),
        snaptradeApi.getAccounts(user.id),
        snaptradeApi.getBrokerages(),
      ]);
      
      setPortfolio(portfolioData);
      setPerformance(performanceData);
      
      if (accountsResponse.success) {
        setAllAccounts(accountsResponse.accounts);
      }
      
      if (brokeragesResponse.success) {
        setBrokerages(brokeragesResponse.brokerages);
      }
    } catch (error) {
      console.error('Error loading portfolio:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnectBroker = async (brokerId: string) => {
    if (!user?.id) return;
    
    setConnecting(true);
    setSelectedBroker(brokerId);
    
    try {
      const redirectUri = `${window.location.origin}${window.location.pathname}?snaptrade_callback=true`;
      const response = await snaptradeApi.connectBroker(user.id, redirectUri, brokerId);
      
      if (response.success && response.redirect_uri) {
        const popup = window.open(
          response.redirect_uri,
          'SnapTrade Connection',
          'width=500,height=700,resizable=yes,scrollbars=yes'
        );
        
        if (!popup || popup.closed) {
          alert('Popup was blocked. Please allow popups for this site.');
          setConnecting(false);
          return;
        }
        
        const handleMessage = (event: MessageEvent) => {
          if (event.origin !== window.location.origin) return;
          
          if (event.data.type === 'SNAPTRADE_CONNECTION') {
            window.removeEventListener('message', handleMessage);
            setConnecting(false);
            setSelectedBroker(null);
            setShowConnectModal(false);
            
            if (event.data.success) {
              loadData();
            }
          }
        };
        
        window.addEventListener('message', handleMessage);
        
        setTimeout(() => {
          window.removeEventListener('message', handleMessage);
          if (connecting) {
            setConnecting(false);
            setSelectedBroker(null);
          }
        }, 300000);
      }
    } catch (err) {
      console.error('Error connecting broker:', err);
      setConnecting(false);
      setSelectedBroker(null);
    }
  };

  const handleToggleAccount = async (accountId: string, currentState: boolean) => {
    if (!user?.id) return;
    
    try {
      await snaptradeApi.toggleAccountVisibility(user.id, accountId, !currentState);
      await loadData();
    } catch (error) {
      console.error('Error toggling account:', error);
    }
  };

  const handleDisconnectAccount = async (accountId: string, accountName: string) => {
    if (!user?.id) return;
    
    if (!confirm(`Disconnect ${accountName}? This will remove it from your portfolio.`)) {
      return;
    }
    
    try {
      await snaptradeApi.disconnectAccount(user.id, accountId);
      await loadData();
    } catch (error) {
      console.error('Error disconnecting account:', error);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercent = (percent: number) => {
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(2)}%`;
  };

  const parseHoldings = (csv: string): Position[] => {
    if (!csv) return [];
    
    const lines = csv.split('\n');
    if (lines.length < 2) return [];
    
    const headers = lines[0].split(',');
    const positions: Position[] = [];
    
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',');
      if (values.length < headers.length) continue;
      
      const position: any = {};
      headers.forEach((header, index) => {
        const value = values[index];
        if (value && value !== 'None') {
          const numValue = parseFloat(value);
          position[header] = isNaN(numValue) ? value : numValue;
        }
      });
      
      if (position.symbol) {
        positions.push(position as Position);
      }
    }
    
    return positions;
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Please sign in</h2>
          <p className="text-gray-600">You need to be signed in to view your portfolio</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Not connected state
  if (allAccounts.length === 0) {
    return (
      <>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
            <div className="text-6xl mb-4">📊</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Connect Your Brokerage</h1>
            <p className="text-gray-600 mb-6">
              Connect your brokerage accounts to view your portfolio and manage your investments.
            </p>
            <button
              onClick={() => setShowConnectModal(true)}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
            >
              Connect Account
            </button>
            <p className="text-sm text-gray-500 mt-4">
              Supports Robinhood, Schwab, Fidelity, E*TRADE, and 8+ more brokerages
            </p>
          </div>
        </div>
        
        {/* Connect Modal */}
        {showConnectModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setShowConnectModal(false)}>
            <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-blue-600 to-indigo-600">
                <h3 className="text-xl font-bold text-white">Select Your Brokerage</h3>
                <button onClick={() => setShowConnectModal(false)} className="text-white hover:bg-white/20 rounded-full p-2">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {brokerages.map((broker) => (
                    <button
                      key={broker.id}
                      onClick={() => handleConnectBroker(broker.id)}
                      disabled={connecting && selectedBroker !== broker.id}
                      className={`flex items-center gap-3 p-4 border-2 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all ${
                        connecting && selectedBroker === broker.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                      } ${connecting && selectedBroker !== broker.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <span className="text-3xl">{broker.logo}</span>
                      <div className="flex-1 text-left">
                        <p className="font-semibold text-gray-900 text-sm">{broker.name}</p>
                        {connecting && selectedBroker === broker.id && (
                          <p className="text-xs text-blue-600 mt-1">Connecting...</p>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  const holdings = parseHoldings(portfolio?.holdings_csv || '');
  const activeAccounts = allAccounts.filter(acc => acc.balance !== null);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Portfolio</h1>
              <p className="text-gray-600 mt-1">{allAccounts.length} connected account{allAccounts.length !== 1 ? 's' : ''}</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowManageModal(true)}
                className="flex items-center gap-2 bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg font-medium transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Manage
              </button>
              <button
                onClick={() => setShowConnectModal(true)}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Connect
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Performance Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="text-sm text-gray-600 mb-1">Total Value</div>
            <div className="text-2xl font-bold text-gray-900">
              {formatCurrency(portfolio?.total_value || 0)}
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="text-sm text-gray-600 mb-1">Total Return</div>
            <div className={`text-2xl font-bold ${(performance?.total_gain_loss || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(performance?.total_gain_loss || 0)}
            </div>
            <div className={`text-sm ${(performance?.total_gain_loss || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatPercent(performance?.total_gain_loss_percent || 0)}
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="text-sm text-gray-600 mb-1">Total Cost</div>
            <div className="text-2xl font-bold text-gray-900">
              {formatCurrency(performance?.total_cost || 0)}
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="text-sm text-gray-600 mb-1">Positions</div>
            <div className="text-2xl font-bold text-gray-900">
              {portfolio?.total_positions || 0}
            </div>
            <div className="text-sm text-gray-600">
              {activeAccounts.length} active account{activeAccounts.length !== 1 ? 's' : ''}
            </div>
          </div>
        </div>

        {/* Holdings Table */}
        {holdings.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Holdings</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">Symbol</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">Quantity</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">Price</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">Market Value</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">Avg Cost</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">Gain/Loss</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {holdings.map((position, index) => {
                    const gainLoss = position.gain_loss || 0;
                    const gainLossPct = position.gain_loss_percent || 0;
                    
                    return (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="font-semibold text-gray-900">{position.symbol}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-gray-900">
                          {position.quantity?.toFixed(4)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-gray-900">
                          {formatCurrency(position.price)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right font-semibold text-gray-900">
                          {formatCurrency(position.value)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-gray-600">
                          {position.average_purchase_price ? formatCurrency(position.average_purchase_price) : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          {gainLoss !== 0 ? (
                            <div>
                              <div className={`font-semibold ${gainLoss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {formatCurrency(gainLoss)}
                              </div>
                              <div className={`text-sm ${gainLossPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {formatPercent(gainLossPct)}
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Connect Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setShowConnectModal(false)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-blue-600 to-indigo-600">
              <h3 className="text-xl font-bold text-white">Connect Brokerage</h3>
              <button onClick={() => setShowConnectModal(false)} className="text-white hover:bg-white/20 rounded-full p-2">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
              <p className="text-gray-600 mb-4">Select a brokerage to connect. All accounts from that brokerage will be imported.</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {brokerages.map((broker) => (
                  <button
                    key={broker.id}
                    onClick={() => handleConnectBroker(broker.id)}
                    disabled={connecting && selectedBroker !== broker.id}
                    className={`flex items-center gap-3 p-4 border-2 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all ${
                      connecting && selectedBroker === broker.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    } ${connecting && selectedBroker !== broker.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <span className="text-3xl">{broker.logo}</span>
                    <div className="flex-1 text-left">
                      <p className="font-semibold text-gray-900 text-sm">{broker.name}</p>
                      {connecting && selectedBroker === broker.id && (
                        <p className="text-xs text-blue-600 mt-1">Connecting...</p>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Manage Accounts Modal */}
      {showManageModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setShowManageModal(false)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-gray-700 to-gray-900">
              <h3 className="text-xl font-bold text-white">Manage Accounts</h3>
              <button onClick={() => setShowManageModal(false)} className="text-white hover:bg-white/20 rounded-full p-2">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
              <p className="text-gray-600 mb-4">Toggle which accounts are included in your portfolio view.</p>
              
              <div className="space-y-3">
                {allAccounts.map((account) => (
                  <div key={account.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-3 flex-1">
                      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-xl">🏦</span>
                      </div>
                      <div className="flex-1">
                        <div className="font-semibold text-gray-900">{account.name}</div>
                        <div className="text-sm text-gray-600">{account.broker_name} • {account.type}</div>
                      </div>
                      <div className="text-right mr-4">
                        <div className="font-semibold text-gray-900">{formatCurrency(account.balance)}</div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={account.balance !== null}
                          onChange={() => handleToggleAccount(account.account_id, account.balance !== null)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                      
                      <button
                        onClick={() => handleDisconnectAccount(account.account_id, account.name)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50 p-2 rounded-lg transition-colors"
                        title="Disconnect account"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
