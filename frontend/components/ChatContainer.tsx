'use client';

import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import RobinhoodLoginModal from './RobinhoodLoginModal';
import { chatApi, robinhoodApi, Message } from '@/lib/api';

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [isPortfolioConnected, setIsPortfolioConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize session on mount so user can connect portfolio immediately
  useEffect(() => {
    if (!sessionId) {
      setSessionId(`session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
    }
  }, []);

  const handleSendMessage = async (content: string) => {
    setError(null);
    
    // Add user message optimistically
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage(content, sessionId || undefined);
      
      // Save session ID if this is the first message
      if (!sessionId) {
        setSessionId(response.session_id);
      }

      // Check if login is required (only show modal if not already connected)
      if (!isPortfolioConnected && (response.needs_auth || response.response.includes('action_required'))) {
        setShowLoginModal(true);
      }

      // Add assistant response (filter out standalone login success messages)
      const shouldAddMessage = !response.response.includes('Successfully connected to Robinhood');
      
      if (shouldAddMessage) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: response.response,
          timestamp: response.timestamp,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (err) {
      setError('Failed to send message. Please try again.');
      console.error('Error sending message:', err);
      // Remove the optimistic user message
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const handleRobinhoodLogin = async (username: string, password: string, mfaCode?: string) => {
    if (!sessionId) {
      throw new Error('No session ID available');
    }

    const response = await robinhoodApi.login(username, password, sessionId, mfaCode);
    
    if (response.success) {
      setIsPortfolioConnected(true);
      setShowLoginModal(false);
      // No chat message - portfolio connection is separate from chat
    } else {
      throw new Error(response.message);
    }
  };

  const handleClearChat = async () => {
    if (sessionId) {
      try {
        await chatApi.clearChatHistory(sessionId);
      } catch (err) {
        console.error('Error clearing chat:', err);
      }
    }
    setMessages([]);
    setSessionId(null);
    setError(null);
  };

  return (
    <div className="flex flex-col h-screen max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Finch</h1>
          <p className="text-sm text-gray-600">Your Portfolio Assistant</p>
        </div>
        
        <div className="flex items-center space-x-3">
          {/* Portfolio Connection Status/Button */}
          {isPortfolioConnected ? (
            <div className="flex items-center space-x-2 bg-green-50 px-4 py-2 rounded-lg border border-green-200">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm font-medium text-green-700">Portfolio Connected</span>
            </div>
          ) : (
            <button
              onClick={() => setShowLoginModal(true)}
              className="flex items-center space-x-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors font-medium text-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <span>Connect Portfolio</span>
            </button>
          )}
          
          {/* Clear Chat Button */}
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="text-sm text-gray-600 hover:text-gray-900 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              Clear Chat
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 chat-scrollbar bg-gray-50">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="bg-white rounded-full p-6 shadow-lg mb-6">
              <svg
                className="w-16 h-16 text-primary-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">
              Welcome to Finch!
            </h2>
            <p className="text-gray-600 max-w-md mb-8">
              I'm your AI portfolio assistant. Ask me anything about investments,
              portfolio management, or market insights.
            </p>
            <div className="grid gap-3 max-w-2xl">
              <button
                onClick={() => handleSendMessage("What stocks do I own?")}
                className="bg-green-50 hover:bg-green-100 text-left px-6 py-4 rounded-lg border-2 border-green-500 transition-colors"
              >
                <p className="font-medium text-green-900">📊 What stocks do I own?</p>
                <p className="text-xs text-green-700 mt-1">Connect to Robinhood and view your portfolio</p>
              </button>
              <button
                onClick={() => handleSendMessage("What can you help me with?")}
                className="bg-white hover:bg-gray-50 text-left px-6 py-4 rounded-lg border border-gray-200 transition-colors"
              >
                <p className="font-medium text-gray-900">What can you help me with?</p>
              </button>
              <button
                onClick={() => handleSendMessage("Explain portfolio diversification")}
                className="bg-white hover:bg-gray-50 text-left px-6 py-4 rounded-lg border border-gray-200 transition-colors"
              >
                <p className="font-medium text-gray-900">Explain portfolio diversification</p>
              </button>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <ChatMessage
                key={index}
                role={message.role}
                content={message.content}
                timestamp={message.timestamp}
              />
            ))}
            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="bg-gray-200 rounded-2xl rounded-bl-none px-4 py-3">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="px-6 py-3 bg-red-50 border-t border-red-200">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Input */}
      <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />

      {/* Robinhood Login Modal */}
      <RobinhoodLoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        onSubmit={handleRobinhoodLogin}
      />
    </div>
  );
}

