'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiKeysApi } from '@/lib/api';
import type { ApiKeyInfo } from '@/lib/types';

interface ApiKeysModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type ServiceType = 'kalshi' | 'polymarket';

interface ServiceConfig {
  name: string;
  displayName: string;
  icon: string;
  description: string;
  fields: Array<{
    key: string;
    label: string;
    type: 'text' | 'textarea';
    placeholder: string;
    helpText?: string;
  }>;
  instructions: {
    title: string;
    steps: Array<{
      text: string;
      link?: { url: string; label: string };
    }>;
  };
}

const SERVICE_CONFIGS: Record<ServiceType, ServiceConfig> = {
  kalshi: {
    name: 'kalshi',
    displayName: 'Kalshi',
    icon: '📊',
    description: 'Prediction market trading',
    fields: [
      {
        key: 'api_key_id',
        label: 'API Key ID',
        type: 'text',
        placeholder: 'Enter your Kalshi API Key ID',
      },
      {
        key: 'private_key',
        label: 'Private Key (PEM format)',
        type: 'textarea',
        placeholder: '-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----',
        helpText: 'Paste the contents of your .key file from Kalshi',
      },
    ],
    instructions: {
      title: 'How to get your Kalshi API credentials',
      steps: [
        {
          text: 'Log in to your Kalshi account',
          link: { url: 'https://kalshi.com', label: 'kalshi.com' },
        },
        { text: 'Go to Account & Security → API Keys' },
        { text: 'Click "Create Key" and download the private key file' },
        { text: 'Copy your API Key ID and paste the private key contents above' },
      ],
    },
  },
  polymarket: {
    name: 'polymarket',
    displayName: 'Polymarket',
    icon: '🎯',
    description: 'Prediction market platform',
    fields: [
      {
        key: 'private_key',
        label: 'Wallet Private Key',
        type: 'text',
        placeholder: '0x...',
        helpText: 'Your Ethereum wallet private key (starts with 0x)',
      },
      {
        key: 'funder_address',
        label: 'Funder Address (Optional)',
        type: 'text',
        placeholder: '0x...',
        helpText: 'Optional: Address to fund trades from',
      },
    ],
    instructions: {
      title: 'How to get your Polymarket credentials',
      steps: [
        { text: 'Export your wallet private key from MetaMask or your wallet provider' },
        { text: 'In MetaMask: Click account menu → Account Details → Show Private Key' },
        { text: 'Copy the private key (starts with 0x) and paste it above' },
        {
          text: 'Important: Never share your private key with anyone else',
        },
      ],
    },
  },
};

export default function ApiKeysModal({ isOpen, onClose }: ApiKeysModalProps) {
  const { user } = useAuth();
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Form state
  const [activeService, setActiveService] = useState<ServiceType | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
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
    if (!user?.id || !activeService) return;
    
    const config = SERVICE_CONFIGS[activeService];
    const hasAllRequired = config.fields
      .filter(f => !f.label.includes('Optional'))
      .every(f => formData[f.key]?.trim());
    
    if (!hasAllRequired) return;
    
    setTesting(true);
    setTestResult(null);
    setError(null);
    
    try {
      const result = await apiKeysApi.testCredentialsBeforeSave(user.id, activeService, formData);
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
    if (!user?.id || !activeService) return;
    
    const config = SERVICE_CONFIGS[activeService];
    const hasAllRequired = config.fields
      .filter(f => !f.label.includes('Optional'))
      .every(f => formData[f.key]?.trim());
    
    if (!hasAllRequired) return;
    
    setSaving(true);
    setError(null);
    setSuccess(null);
    
    try {
      const response = await apiKeysApi.saveApiKey(user.id, activeService, formData);
      
      if (response.success) {
        setSuccess(`${config.displayName} credentials saved securely!`);
        setActiveService(null);
        setFormData({});
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

  const handleShowAddForm = (service: ServiceType) => {
    setActiveService(service);
    setFormData({});
    setTestResult(null);
    setError(null);
  };

  const handleCancelForm = () => {
    setActiveService(null);
    setFormData({});
    setTestResult(null);
  };

  if (!isOpen) return null;

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
                <h4 className="font-semibold text-blue-900">Your credentials are encrypted and secure</h4>
                <p className="text-sm text-blue-800 mt-1">
                  All private keys are encrypted with AES-128 before storage and are never exposed in API responses.
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
            <div className="space-y-4">
              {/* Render each service */}
              {(Object.keys(SERVICE_CONFIGS) as ServiceType[]).map((serviceType) => {
                const config = SERVICE_CONFIGS[serviceType];
                const savedKey = keys.find(k => k.service === serviceType);
                const isEditing = activeService === serviceType;

                return (
                  <div key={serviceType} className="border border-gray-200 rounded-xl overflow-hidden">
                    {/* Service Header */}
                    <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-gradient-to-br from-purple-100 to-blue-100 rounded-lg flex items-center justify-center">
                            <span className="text-xl">{config.icon}</span>
                          </div>
                          <div>
                            <h3 className="font-semibold text-gray-900">{config.displayName}</h3>
                            <p className="text-sm text-gray-600">{config.description}</p>
                          </div>
                        </div>
                        {savedKey ? (
                          <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full flex items-center gap-1">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            Connected
                          </span>
                        ) : (
                          <span className="px-3 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-full">
                            Not configured
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Service Content */}
                    <div className="p-4">
                      {savedKey && !isEditing ? (
                        // Show saved key info
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-gray-600 mb-1">
                                {config.fields[0].label}
                              </p>
                              <p className="font-mono text-sm text-gray-900">
                                {savedKey.api_key_id_masked}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleTestSavedKey(serviceType)}
                                disabled={testing}
                                className="px-3 py-1.5 text-sm bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50 font-medium"
                              >
                                {testing ? 'Testing...' : 'Test'}
                              </button>
                              <button
                                onClick={() => handleDeleteKey(serviceType)}
                                className="px-3 py-1.5 text-sm bg-red-50 text-red-700 hover:bg-red-100 rounded-lg transition-colors font-medium"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                          
                          {savedKey.created_at && (
                            <p className="text-xs text-gray-500">
                              Added {new Date(savedKey.created_at).toLocaleDateString()}
                            </p>
                          )}

                          {testResult && (
                            <div className={`p-3 rounded-lg ${testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                              <p className={`text-sm font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
                                {testResult.success ? '✓ ' : '✗ '}{testResult.message}
                              </p>
                            </div>
                          )}

                          <button
                            onClick={() => handleShowAddForm(serviceType)}
                            className="w-full py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors font-medium"
                          >
                            Update credentials
                          </button>
                        </div>
                      ) : isEditing ? (
                        // Show edit form
                        <div className="space-y-4">
                          {/* Render form fields */}
                          {config.fields.map((field) => (
                            <div key={field.key}>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                {field.label}
                              </label>
                              {field.type === 'textarea' ? (
                                <textarea
                                  value={formData[field.key] || ''}
                                  onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                                  placeholder={field.placeholder}
                                  rows={6}
                                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 font-mono text-sm"
                                />
                              ) : (
                                <input
                                  type={field.key.includes('private_key') ? 'password' : 'text'}
                                  value={formData[field.key] || ''}
                                  onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                                  placeholder={field.placeholder}
                                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                                />
                              )}
                              {field.helpText && (
                                <p className="text-xs text-gray-500 mt-1">{field.helpText}</p>
                              )}
                            </div>
                          ))}

                          {testResult && (
                            <div className={`p-3 rounded-lg ${testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                              <p className={`text-sm font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
                                {testResult.success ? '✓ ' : '✗ '}{testResult.message}
                              </p>
                            </div>
                          )}

                          <div className="flex gap-3">
                            <button
                              onClick={handleTestCredentials}
                              disabled={testing || saving}
                              className="flex-1 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {testing ? 'Testing...' : 'Test Credentials'}
                            </button>
                            <button
                              onClick={handleSaveCredentials}
                              disabled={testing || saving}
                              className="flex-1 py-2 bg-emerald-600 text-white hover:bg-emerald-700 rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {saving ? 'Saving...' : 'Save Credentials'}
                            </button>
                          </div>

                          <button
                            onClick={handleCancelForm}
                            className="w-full py-2 text-sm text-gray-600 hover:text-gray-900 font-medium"
                          >
                            Cancel
                          </button>

                          {/* Instructions */}
                          <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                            <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              {config.instructions.title}
                            </h4>
                            <ol className="text-sm text-gray-600 space-y-2">
                              {config.instructions.steps.map((step, idx) => (
                                <li key={idx} className="flex items-start gap-2">
                                  <span className="font-semibold text-gray-900 min-w-[20px]">{idx + 1}.</span>
                                  <span>
                                    {step.text}
                                    {step.link && (
                                      <>
                                        {' '}
                                        <a
                                          href={step.link.url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="text-emerald-600 hover:underline font-medium"
                                        >
                                          {step.link.label}
                                        </a>
                                      </>
                                    )}
                                  </span>
                                </li>
                              ))}
                            </ol>
                          </div>
                        </div>
                      ) : (
                        // Show "Connect" button
                        <button
                          onClick={() => handleShowAddForm(serviceType)}
                          className="w-full py-3 bg-gradient-to-r from-emerald-50 to-teal-50 text-emerald-700 hover:from-emerald-100 hover:to-teal-100 rounded-lg transition-all font-semibold flex items-center justify-center gap-2"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                          </svg>
                          Connect {config.displayName}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
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
