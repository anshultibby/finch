'use client';

import React, { useState } from 'react';

interface RobinhoodLoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (username: string, password: string, mfaCode?: string) => Promise<void>;
}

export default function RobinhoodLoginModal({ isOpen, onClose, onSubmit }: RobinhoodLoginModalProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [showMfa, setShowMfa] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await onSubmit(username, password, mfaCode || undefined);
      // Reset form
      setUsername('');
      setPassword('');
      setMfaCode('');
      setShowMfa(false);
      onClose();
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to login. Please check your credentials.';
      
      // Check if MFA is required
      if (errorMessage.includes('MFA') || errorMessage.includes('two-factor') || errorMessage.includes('authenticator')) {
        setShowMfa(true);
        setError('Please enter your two-factor authentication code');
      } else if (errorMessage.includes('Device verification') || errorMessage.includes('push notification')) {
        // Device challenge - don't close modal, user needs to try again
        setError(errorMessage);
      } else {
        setError(errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setUsername('');
      setPassword('');
      setMfaCode('');
      setShowMfa(false);
      setError(null);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Login to Robinhood</h2>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          Enter your Robinhood credentials to access your portfolio data. Your credentials are sent securely and not stored.
        </p>
        
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6">
          <p className="text-xs text-blue-800">
            <strong>📱 Device Verification Required:</strong>
          </p>
          <ol className="text-xs text-blue-800 mt-2 ml-4 space-y-1">
            <li>1. Click "Login" below</li>
            <li>2. Robinhood will send a push notification to your phone</li>
            <li>3. Approve it in your Robinhood app</li>
            <li>4. The login will complete automatically (may take up to 60 seconds)</li>
            <li>5. Your session will be cached for future use!</li>
          </ol>
          <p className="text-xs text-green-700 mt-2 font-medium">
            ✅ Using robin-stocks 3.4.0 with automatic device verification handling
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Username or Email
            </label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={isLoading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50"
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50"
              placeholder="Enter your password"
            />
          </div>

          {showMfa && (
            <div>
              <label htmlFor="mfaCode" className="block text-sm font-medium text-gray-700 mb-1">
                Two-Factor Authentication Code
              </label>
              <input
                type="text"
                id="mfaCode"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                disabled={isLoading}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50"
                placeholder="Enter 6-digit code"
                maxLength={6}
              />
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div className="flex space-x-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={isLoading}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center justify-center"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span className="flex flex-col items-start">
                    <span>Logging in...</span>
                    <span className="text-xs opacity-90">Check your phone for approval</span>
                  </span>
                </>
              ) : (
                'Login'
              )}
            </button>
          </div>
        </form>

        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            🔒 Your credentials are encrypted and transmitted securely. Finch does not store your Robinhood password.
          </p>
        </div>
      </div>
    </div>
  );
}

