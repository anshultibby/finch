'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiKeysApi } from '@/lib/api';
import type { ApiKeyInfo } from '@/lib/types';

interface ApiKeysModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ApiKeysModal({ isOpen, onClose }: ApiKeysModalProps) {
  const { user } = useAuth();
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Form state for adding Kalshi credentials
  const [showAddForm, setShowAddForm] = useState(false);
  const [apiKeyId, setApiKeyId] = useState('');
  const [privateKey, setPrivateKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    if (isOpen && user?.id) {
      loadKeys();
    }
  }, [isOpen, user?.id]);

  const loadKeys = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiKeysApi.getApiKeys(user.id);
      if (response.success) {
        setKeys(response.keys);
      }
    } catch (err) {
      console.error('Error loading API keys:', err);
      setError('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleTestCredentials = async () => {
    if (!user?.id || !apiKeyId || !privateKey) return;
    
    setTesting(true);
    setTestResult(null);
    setError(null);
    
    try {
      const result = await apiKeysApi.testCredentialsBeforeSave(user.id, 'kalshi', {
        api_key_id: apiKeyId,
        private_key: privateKey,
      });
      setTestResult(result);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.response?.data?.detail || 'Failed to test credentials',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveCredentials = async () => {
    if (!user?.id || !apiKeyId || !privateKey) return;
    
    setSaving(true);
    setError(null);
    setSuccess(null);
    
    try {
      const response = await apiKeysApi.saveApiKey(user.id, 'kalshi', {
        api_key_id: apiKeyId,
        private_key: privateKey,
      });
      
      if (response.success) {
        setSuccess('Kalshi credentials saved securely!');
        setShowAddForm(false);
        setApiKeyId('');
        setPrivateKey('');
        setTestResult(null);
        await loadKeys();
      } else {
        setError(response.message);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save credentials');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteKey = async (service: string) => {
    if (!user?.id) return;
    
    if (!confirm(`Are you sure you want to delete your ${service} credentials? This cannot be undone.`)) {
      return;
    }
    
    try {
      const response = await apiKeysApi.deleteApiKey(user.id, service);
      if (response.success) {
        setSuccess(`${service} credentials deleted`);
        await loadKeys();
      } else {
        setError(response.message);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete credentials');
    }
  };

  const handleTestSavedKey = async (service: string) => {
    if (!user?.id) return;
    
    setTesting(true);
    setTestResult(null);
    
    try {
      const result = await apiKeysApi.testApiKey(user.id, service);
      setTestResult(result);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.response?.data?.detail || 'Failed to test credentials',
      });
    } finally {
      setTesting(false);
    }
  };

  if (!isOpen) return null;

  const kalshiKey = keys.find(k => k.service === 'kalshi');

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-6 py-5 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              API Keys
            </h2>
            <p className="text-emerald-100 text-sm mt-1">Securely manage your trading platform credentials</p>
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
          {/* Security Notice */}
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <div>
                <h4 className="font-semibold text-blue-900">Your credentials are encrypted</h4>
                <p className="text-sm text-blue-800 mt-1">
                  Private keys are encrypted with AES-128 before storage and are never exposed in API responses.
                  Only you can access your credentials through authenticated requests.
                </p>
              </div>
            </div>
          </div>

          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
              <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          )}

          {success && (
            <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2">
              <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              {success}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
            </div>
          ) : (
            <>
              {/* Kalshi Section */}
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                        <span className="text-xl">📊</span>
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">Kalshi</h3>
                        <p className="text-sm text-gray-600">Prediction market trading</p>
                      </div>
                    </div>
                    {kalshiKey ? (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                        Connected
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-full">
                        Not configured
                      </span>
                    )}
                  </div>
                </div>

                <div className="p-4">
                  {kalshiKey ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-600">API Key ID</p>
                          <p className="font-mono text-sm">{kalshiKey.api_key_id_masked}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleTestSavedKey('kalshi')}
                            disabled={testing}
                            className="px-3 py-1.5 text-sm bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50"
                          >
                            {testing ? 'Testing...' : 'Test'}
                          </button>
                          <button
                            onClick={() => handleDeleteKey('kalshi')}
                            className="px-3 py-1.5 text-sm bg-red-50 text-red-700 hover:bg-red-100 rounded-lg transition-colors"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                      
                      {kalshiKey.created_at && (
                        <p className="text-xs text-gray-500">
                          Added {new Date(kalshiKey.created_at).toLocaleDateString()}
                        </p>
                      )}

                      {testResult && (
                        <div className={`p-3 rounded-lg ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                          <p className="text-sm">{testResult.message}</p>
                        </div>
                      )}

                      <button
                        onClick={() => {
                          setShowAddForm(true);
                          setTestResult(null);
                        }}
                        className="w-full py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors"
                      >
                        Update credentials
                      </button>
                    </div>
                  ) : !showAddForm ? (
                    <button
                      onClick={() => setShowAddForm(true)}
                      className="w-full py-3 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg transition-colors font-medium"
                    >
                      + Add Kalshi Credentials
                    </button>
                  ) : null}

                  {showAddForm && (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          API Key ID
                        </label>
                        <input
                          type="text"
                          value={apiKeyId}
                          onChange={(e) => setApiKeyId(e.target.value)}
                          placeholder="Enter your Kalshi API Key ID"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Private Key (PEM format)
                        </label>
                        <textarea
                          value={privateKey}
                          onChange={(e) => setPrivateKey(e.target.value)}
                          placeholder="-----BEGIN PRIVATE KEY-----&#10;...&#10;-----END PRIVATE KEY-----"
                          rows={6}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 font-mono text-sm"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Paste the contents of your .key file from Kalshi
                        </p>
                      </div>

                      {testResult && (
                        <div className={`p-3 rounded-lg ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                          <p className="text-sm font-medium">{testResult.success ? '✓ ' : '✗ '}{testResult.message}</p>
                        </div>
                      )}

                      <div className="flex gap-3">
                        <button
                          onClick={handleTestCredentials}
                          disabled={!apiKeyId || !privateKey || testing}
                          className="flex-1 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {testing ? 'Testing...' : 'Test Credentials'}
                        </button>
                        <button
                          onClick={handleSaveCredentials}
                          disabled={!apiKeyId || !privateKey || saving}
                          className="flex-1 py-2 bg-emerald-600 text-white hover:bg-emerald-700 rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {saving ? 'Saving...' : 'Save Credentials'}
                        </button>
                      </div>

                      <button
                        onClick={() => {
                          setShowAddForm(false);
                          setApiKeyId('');
                          setPrivateKey('');
                          setTestResult(null);
                        }}
                        className="w-full py-2 text-sm text-gray-600 hover:text-gray-900"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Help Section */}
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium text-gray-900 mb-2">How to get your Kalshi API credentials</h4>
                <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
                  <li>Log in to your Kalshi account at <a href="https://kalshi.com" target="_blank" rel="noopener noreferrer" className="text-emerald-600 hover:underline">kalshi.com</a></li>
                  <li>Go to Account & Security → API Keys</li>
                  <li>Click "Create Key" and download the private key file</li>
                  <li>Copy your API Key ID and paste the private key contents here</li>
                </ol>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t px-6 py-4 bg-gray-50 flex justify-end">
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
