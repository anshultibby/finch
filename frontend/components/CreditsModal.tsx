'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { creditsApi, type CreditBalance, type CreditTransaction } from '@/lib/api';

interface CreditsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CreditsModal({ isOpen, onClose }: CreditsModalProps) {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'balance' | 'history' | 'request'>('balance');
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Request form state
  const [requestAmount, setRequestAmount] = useState('1000');
  const [requestReason, setRequestReason] = useState('');
  const [requestSuccess, setRequestSuccess] = useState(false);
  const [requestLoading, setRequestLoading] = useState(false);

  // Load balance and history when modal opens
  useEffect(() => {
    if (isOpen && user) {
      loadBalance();
      if (activeTab === 'history') {
        loadHistory();
      }
    }
  }, [isOpen, user, activeTab]);

  const loadBalance = async () => {
    if (!user) return;
    
    setLoading(true);
    setError(null);
    try {
      const data = await creditsApi.getBalance(user.id);
      setBalance(data);
    } catch (err) {
      setError('Failed to load balance');
      console.error('Error loading balance:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    if (!user) return;
    
    setLoading(true);
    setError(null);
    try {
      const data = await creditsApi.getHistory(user.id, 50);
      setTransactions(data.transactions);
    } catch (err) {
      setError('Failed to load transaction history');
      console.error('Error loading history:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !balance) return;

    setRequestLoading(true);
    setError(null);
    
    try {
      const response = await creditsApi.requestCredits({
        user_id: user.id,
        user_email: user.email || '',
        requested_credits: parseInt(requestAmount),
        reason: requestReason,
        current_balance: balance.credits,
        total_used: balance.total_credits_used,
      });

      if (response.success) {
        setRequestSuccess(true);
        setRequestReason('');
        setRequestAmount('1000');
      } else {
        setError(response.message || 'Failed to submit request');
      }
    } catch (err) {
      setError('Failed to submit request. Please try again.');
      console.error('Error submitting request:', err);
    } finally {
      setRequestLoading(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatAmount = (amount: number) => {
    return amount > 0 ? `+${amount}` : amount.toString();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">Credits</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="px-6 py-3 border-b border-gray-200 flex gap-4">
          <button
            onClick={() => setActiveTab('balance')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'balance'
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Balance
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'history'
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            History
          </button>
          <button
            onClick={() => setActiveTab('request')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'request'
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Request Credits
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Balance Tab */}
          {activeTab === 'balance' && (
            <div>
              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : balance ? (
                <div className="space-y-6">
                  {/* Current Balance Card */}
                  <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-6 text-white">
                    <p className="text-sm opacity-90 mb-2">Current Balance</p>
                    <p className="text-4xl font-bold">{balance.credits.toLocaleString()}</p>
                    <p className="text-sm opacity-75 mt-4">
                      ≈ ${(balance.credits / 1000 / 1.2).toFixed(2)} USD worth of API usage
                    </p>
                  </div>

                  {/* Usage Stats */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Total Used</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {balance.total_credits_used.toLocaleString()}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Remaining</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {balance.credits.toLocaleString()}
                      </p>
                    </div>
                  </div>

                  {/* Info Box */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="font-semibold text-blue-900 mb-2">How Credits Work</h3>
                    <ul className="text-sm text-blue-800 space-y-1">
                      <li>• 1,000 credits ≈ $1 USD of API costs (with 20% premium)</li>
                      <li>• Credits are deducted based on actual token usage</li>
                      <li>• Typical chat message costs 5-50 credits</li>
                      <li>• Complex code generation costs 50-200 credits</li>
                    </ul>
                  </div>

                  {/* Low Balance Warning */}
                  {balance.credits < 100 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <svg className="w-5 h-5 text-amber-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <div>
                          <p className="font-semibold text-amber-900">Low Balance</p>
                          <p className="text-sm text-amber-800 mt-1">
                            You're running low on credits. Request more credits to continue using the app.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">No balance data available</div>
              )}
            </div>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <div>
              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : transactions.length > 0 ? (
                <div className="space-y-3">
                  {transactions.map((tx) => (
                    <div
                      key={tx.id}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">{tx.description}</p>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-xs text-gray-500">{formatDate(tx.created_at)}</span>
                          <span className="text-xs text-gray-400">•</span>
                          <span className="text-xs text-gray-500 capitalize">{tx.transaction_type.replace('_', ' ')}</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-semibold ${tx.amount > 0 ? 'text-green-600' : 'text-gray-900'}`}>
                          {formatAmount(tx.amount)}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          Balance: {tx.balance_after.toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">No transactions yet</div>
              )}
            </div>
          )}

          {/* Request Tab */}
          {activeTab === 'request' && (
            <div>
              {requestSuccess ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Request Submitted!</h3>
                  <p className="text-gray-600 mb-6">
                    We've received your request and will review it shortly. You'll receive an email once approved.
                  </p>
                  <button
                    onClick={() => {
                      setRequestSuccess(false);
                      setActiveTab('balance');
                    }}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Back to Balance
                  </button>
                </div>
              ) : (
                <form onSubmit={handleRequestSubmit} className="space-y-6">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800">
                      Need more credits? Fill out this form and we'll review your request. You'll receive an email once approved.
                    </p>
                  </div>

                  {/* Current Balance Display */}
                  {balance && (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-2">Your Current Balance</p>
                      <p className="text-2xl font-semibold text-gray-900">{balance.credits.toLocaleString()} credits</p>
                    </div>
                  )}

                  {/* Amount Request */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      How many credits do you need?
                    </label>
                    <select
                      value={requestAmount}
                      onChange={(e) => setRequestAmount(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      required
                    >
                      <option value="1000">1,000 credits (~$1 worth)</option>
                      <option value="5000">5,000 credits (~$5 worth)</option>
                      <option value="10000">10,000 credits (~$10 worth)</option>
                      <option value="50000">50,000 credits (~$50 worth)</option>
                      <option value="100000">100,000 credits (~$100 worth)</option>
                    </select>
                  </div>

                  {/* Reason */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Why do you need more credits?
                    </label>
                    <textarea
                      value={requestReason}
                      onChange={(e) => setRequestReason(e.target.value)}
                      rows={4}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Tell us about your use case, what you're building, or why you need more credits..."
                      required
                    />
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={requestLoading}
                    className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
                  >
                    {requestLoading ? 'Submitting...' : 'Submit Request'}
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
