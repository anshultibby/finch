'use client';

import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ResourcesSidebar from './ResourcesSidebar';
import ResourceViewer from './ResourceViewer';
import { 
  chatApi, 
  snaptradeApi, 
  resourcesApi, 
  Message, 
  ToolCallStatus, 
  Resource,
  SSEToolCallStartEvent,
  SSEToolCallCompleteEvent,
  SSEAssistantMessageEvent 
} from '@/lib/api';

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [userId, setUserId] = useState<string | null>(null); // Persistent - for brokerage connection
  const [chatId, setChatId] = useState<string | null>(null); // Per-session - for chat history
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isCheckingConnection, setIsCheckingConnection] = useState(false);
  const [isPortfolioConnected, setIsPortfolioConnected] = useState(false);
  const [ephemeralToolCalls, setEphemeralToolCalls] = useState<ToolCallStatus[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string>('');  // Accumulate streaming tokens
  const [resources, setResources] = useState<Resource[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize user ID (persistent - for brokerage) and chat ID (new each time - for chat history)
  useEffect(() => {
    // Get or create persistent user ID for brokerage connection
    let existingUserId = localStorage.getItem('finch_user_id');
    if (!existingUserId) {
      existingUserId = `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('finch_user_id', existingUserId);
    }
    setUserId(existingUserId);
    
    // Create new chat ID for this conversation (resets on page refresh)
    const newChatId = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setChatId(newChatId);
  }, []);

  // Load resources when chat ID changes
  useEffect(() => {
    const loadResources = async () => {
      if (!chatId) return;
      
      try {
        const chatResources = await resourcesApi.getChatResources(chatId);
        setResources(chatResources);
      } catch (err) {
        console.error('Error loading resources:', err);
      }
    };
    
    loadResources();
  }, [chatId]);

  // Check if user has an existing SnapTrade connection on mount
  useEffect(() => {
    const checkExistingConnection = async () => {
      if (!userId) return;
      
      setIsCheckingConnection(true);
      try {
        const status = await snaptradeApi.checkStatus(userId);
        if (status.is_connected) {
          console.log('✅ Found existing SnapTrade connection');
          setIsPortfolioConnected(true);
        }
      } catch (err) {
        console.log('No existing connection found or error checking status:', err);
      } finally {
        setIsCheckingConnection(false);
      }
    };
    
    checkExistingConnection();
  }, [userId]);

  // Check for OAuth callback (when redirected back from SnapTrade)
  useEffect(() => {
    const handleCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      if (params.get('snaptrade_callback') === 'true' && userId) {
        // If this is a popup window, notify the parent and close
        if (window.opener && window.opener !== window) {
          try {
            const result = await snaptradeApi.handleCallback(userId);
            // Send message to parent window
            window.opener.postMessage({
              type: 'SNAPTRADE_CONNECTION',
              success: result.success,
              is_connected: result.is_connected,
              message: result.message
            }, window.location.origin);
            
            // Close this popup immediately
            setTimeout(() => window.close(), 100);
          } catch (err) {
            console.error('Error handling callback:', err);
            window.opener.postMessage({
              type: 'SNAPTRADE_CONNECTION',
              success: false,
              is_connected: false,
              message: 'Error during connection'
            }, window.location.origin);
            setTimeout(() => window.close(), 300);
          }
          return;
        }
        
        // If not in a popup (fallback), handle normally
        setIsConnecting(true);
        try {
          const result = await snaptradeApi.handleCallback(userId);
          if (result.success && result.is_connected) {
            setIsPortfolioConnected(true);
            window.history.replaceState({}, '', window.location.pathname);
          } else {
            setError(result.message || 'Failed to connect');
          }
        } catch (err) {
          console.error('Error handling callback:', err);
          setError('Error during connection callback');
        } finally {
          setIsConnecting(false);
        }
      }
    };
    
    if (userId) {
      handleCallback();
    }
  }, [userId]);

  // Listen for messages from popup window
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Verify origin for security
      if (event.origin !== window.location.origin) return;
      
      if (event.data.type === 'SNAPTRADE_CONNECTION') {
        setIsConnecting(false);
        if (event.data.success && event.data.is_connected) {
          setIsPortfolioConnected(true);
          setError(null);
        } else {
          setError(event.data.message || 'Failed to connect');
        }
      }
    };
    
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleSendMessage = async (content: string) => {
    if (!userId || !chatId) {
      setError('Session not initialized. Please refresh the page.');
      return;
    }
    
    setError(null);
    
    // Add user message optimistically
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setEphemeralToolCalls([]);
    setIsThinking(false);
    setStreamingMessage(''); // Clear any previous streaming message

    // Track tool calls and resources
    const toolCallsMap = new Map<string, ToolCallStatus>();
    let needsAuth = false;

    try {
      // Use streaming API for real-time updates
      const eventSource = chatApi.sendMessageStream(
        content,
        userId,
        chatId,
        {
          onToolCallStart: (event: SSEToolCallStartEvent) => {
            console.log('🔧 Tool call started:', event.tool_name);
            
            // Clear any streaming message if tool calls are starting
            setStreamingMessage('');
            
            // IMMEDIATELY show ephemeral message when tool call starts
            const toolCallStatus: ToolCallStatus = {
              tool_call_id: event.tool_call_id,
              tool_name: event.tool_name,
              status: 'calling',
            };
            toolCallsMap.set(event.tool_call_id, toolCallStatus);
            setEphemeralToolCalls(Array.from(toolCallsMap.values()));
          },
          
          onToolCallComplete: (event: SSEToolCallCompleteEvent) => {
            console.log('✅ Tool call completed:', event.tool_name, event.status);
            
            // Update ephemeral message with completion status
            const toolCallStatus = toolCallsMap.get(event.tool_call_id);
            if (toolCallStatus) {
              toolCallStatus.status = event.status;
              toolCallStatus.resource_id = event.resource_id;
              toolCallStatus.error = event.error;
              setEphemeralToolCalls(Array.from(toolCallsMap.values()));
            }
          },
          
          onThinking: (event) => {
            console.log('🤔 AI is thinking:', event.message);
            // Show thinking indicator
            setIsThinking(true);
          },
          
          onAssistantMessageDelta: (event) => {
            console.log('💬 Streaming delta received:', event.delta.substring(0, 50));
            // Accumulate streaming text as it arrives
            setStreamingMessage((prev) => {
              const newContent = prev + event.delta;
              console.log('📝 Current streaming message length:', newContent.length);
              return newContent;
            });
          },
          
          onAssistantMessage: (event: SSEAssistantMessageEvent) => {
            console.log('💬 Assistant message received (complete)');
            
            needsAuth = event.needs_auth;
            
            // Hide thinking indicator
            setIsThinking(false);
            
            // Clear streaming message
            setStreamingMessage('');
            
            // Add assistant response (filter out standalone connection success messages)
            const shouldAddMessage = !event.content.includes('Successfully connected');
            
            if (shouldAddMessage) {
              const assistantMessage: Message = {
                role: 'assistant',
                content: event.content,
                timestamp: event.timestamp,
              };
              setMessages((prev) => [...prev, assistantMessage]);
            }
          },
          
          onDone: async () => {
            console.log('✨ Stream complete');
            setIsLoading(false);
            
            // Reload resources to include new ones
            try {
              const chatResources = await resourcesApi.getChatResources(chatId);
              setResources(chatResources);
            } catch (err) {
              console.error('Error reloading resources:', err);
            }
            
            // Check if connection is required
            if (needsAuth && !isPortfolioConnected) {
              setIsPortfolioConnected(false);
              await handleBrokerageConnection();
            }
            
            // Clear ephemeral tool calls after a delay
            setTimeout(() => setEphemeralToolCalls([]), 5000);
          },
          
          onError: (event) => {
            console.error('❌ SSE error:', event.error);
            setError(`Error: ${event.error}`);
            setIsLoading(false);
            setIsThinking(false);
            setStreamingMessage(''); // Clear streaming message on error
            // Remove the optimistic user message
            setMessages((prev) => prev.slice(0, -1));
          },
        }
      );

      // Store event source for cleanup if needed
      // (In case user navigates away)
      
    } catch (err) {
      setError('Failed to send message. Please try again.');
      console.error('Error sending message:', err);
      // Remove the optimistic user message
      setMessages((prev) => prev.slice(0, -1));
      setIsLoading(false);
      setIsThinking(false);
      setStreamingMessage(''); // Clear streaming message on error
    }
  };

  const handleBrokerageConnection = async () => {
    if (!userId) {
      setError('No user ID available');
      return;
    }

    setIsConnecting(true);
    try {
      // Get redirect URI from backend
      const redirectUri = `${window.location.origin}${window.location.pathname}?snaptrade_callback=true`;
      const response = await snaptradeApi.initiateConnection(userId, redirectUri);
      
      if (response.success && response.redirect_uri) {
        // Open SnapTrade Connection Portal in a new window
        const width = 500;
        const height = 700;
        const left = (window.screen.width - width) / 2;
        const top = (window.screen.height - height) / 2;
        
        window.open(
          response.redirect_uri,
          'SnapTrade Connection',
          `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );
        
        // Keep connecting state active until callback is received
      } else {
        // Check if we need a new user session
        if (response.message?.includes('refresh the page') || response.message?.includes('new session')) {
          setError(response.message);
          // Clear the old user and generate a new one
          localStorage.removeItem('finch_user_id');
          const newUserId = `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          setUserId(newUserId);
          localStorage.setItem('finch_user_id', newUserId);
          setIsConnecting(false);
          // Prompt user to try again
          setTimeout(() => {
            setError('New user session created. Please click "Connect Brokerage" again.');
          }, 100);
        } else {
          setError(response.message || 'Failed to initiate connection');
          setIsConnecting(false);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to connect');
      setIsConnecting(false);
    }
  };

  const handleClearChat = async () => {
    // Just create a new chat - don't clear the current one or disconnect brokerage
    setMessages([]);
    setResources([]);
    setEphemeralToolCalls([]);
    
    // Generate new chat ID (user ID stays the same)
    const newChatId = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setChatId(newChatId);
    setError(null);
    // Keep portfolio connected
  };

  const handleSelectResource = (resource: Resource) => {
    setSelectedResource(resource);
  };

  const getToolIcon = (toolName: string) => {
    if (toolName.includes('portfolio')) return '📊';
    if (toolName.includes('reddit')) return '📱';
    if (toolName.includes('senate') || toolName.includes('house')) return '🏛️';
    if (toolName.includes('insider')) return '💼';
    return '🔧';
  };

  return (
    <>
      <div className="flex flex-col h-screen max-w-5xl mx-auto">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Finch</h1>
          <p className="text-sm text-gray-600">Your Portfolio Assistant</p>
        </div>
        
        <div className="flex items-center space-x-3">
          {/* Portfolio Connection Status/Button */}
          <button
            onClick={handleBrokerageConnection}
            disabled={isConnecting || isCheckingConnection}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              isPortfolioConnected
                ? 'bg-green-600 hover:bg-green-700 text-white'
                : (isConnecting || isCheckingConnection)
                ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            } disabled:opacity-50`}
          >
            <span className="text-lg">
              {(isConnecting || isCheckingConnection) ? '⏳' : isPortfolioConnected ? '🚀' : '🔗'}
            </span>
            {(isConnecting || isCheckingConnection) ? 'Connecting...' : isPortfolioConnected ? 'Connected' : 'Connect Brokerage'}
          </button>
          
          {/* Resources Button - Always visible */}
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className={`relative flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              resources.length > 0
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <span className="text-lg">📦</span>
            Resources
            {resources.length > 0 && (
              <span className="bg-white text-blue-600 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                {resources.length}
              </span>
            )}
          </button>
          
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

      {/* Connection Prompt Banner */}
      {!isPortfolioConnected && !isConnecting && !isCheckingConnection && messages.length === 0 && (
        <div className="mx-6 mt-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-500 rounded-lg p-4 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="text-2xl">🔗</div>
            <div className="flex-1">
              <h3 className="font-semibold text-blue-900 mb-1">
                Connect Your Brokerage Account
              </h3>
              <p className="text-sm text-blue-700 mb-3">
                Securely connect your brokerage account (Robinhood, TD Ameritrade, etc.) via SnapTrade to ask questions about your portfolio, get insights, and track your investments. No passwords stored!
              </p>
              <button
                onClick={handleBrokerageConnection}
                className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
              >
                Connect via SnapTrade
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Connecting Banner */}
      {isConnecting && (
        <div className="mx-6 mt-4 bg-gradient-to-r from-yellow-50 to-amber-50 border-2 border-yellow-500 rounded-lg p-4 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="text-2xl animate-pulse">🔗</div>
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-900 mb-1">
                Connecting...
              </h3>
              <p className="text-sm text-yellow-700">
                Please complete the connection process in the popup window. The popup will close automatically once you're connected.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 chat-scrollbar bg-white">
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
                onClick={() => handleSendMessage("review my portfolio")}
                className="bg-blue-50 hover:bg-blue-100 text-left px-6 py-4 rounded-lg border-2 border-blue-500 transition-colors"
              >
                <p className="font-medium text-blue-900">📊 Review my portfolio</p>
                <p className="text-xs text-blue-700 mt-1">Get insights on your holdings and performance</p>
              </button>
              <button
                onClick={() => handleSendMessage("what are the most recent Reddit trends?")}
                className="bg-white hover:bg-gray-50 text-left px-6 py-4 rounded-lg border border-gray-200 transition-colors"
              >
                <p className="font-medium text-gray-900">📱 What are the most recent Reddit trends?</p>
                <p className="text-xs text-gray-600 mt-1">See what stocks are trending on Reddit</p>
              </button>
              <button
                onClick={() => handleSendMessage("get recent insider trades")}
                className="bg-white hover:bg-gray-50 text-left px-6 py-4 rounded-lg border border-gray-200 transition-colors"
              >
                <p className="font-medium text-gray-900">💼 Get recent insider trades</p>
                <p className="text-xs text-gray-600 mt-1">Track corporate insider buying and selling</p>
              </button>
              <button
                onClick={() => handleSendMessage("get recent house trades")}
                className="bg-white hover:bg-gray-50 text-left px-6 py-4 rounded-lg border border-gray-200 transition-colors"
              >
                <p className="font-medium text-gray-900">🏛️ Get recent house trades</p>
                <p className="text-xs text-gray-600 mt-1">See what members of Congress are trading</p>
              </button>
              <button
                onClick={() => handleSendMessage("what are the top trending stocks right now?")}
                className="bg-white hover:bg-gray-50 text-left px-6 py-4 rounded-lg border border-gray-200 transition-colors"
              >
                <p className="font-medium text-gray-900">🔥 What are the top trending stocks right now?</p>
                <p className="text-xs text-gray-600 mt-1">Discover hot stocks from social media</p>
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
            {/* Ephemeral Tool Call Messages - Flashing text that fades out */}
            {ephemeralToolCalls.length > 0 && (
              <div className="space-y-2 mb-4 px-2">
                {ephemeralToolCalls.map((toolCall) => (
                  <div
                    key={toolCall.tool_call_id}
                    className={`flex justify-start items-center gap-2 ${
                      toolCall.status === 'calling' ? 'animate-pulse' : 'animate-fadeOut'
                    }`}
                  >
                    <span className="text-lg">{getToolIcon(toolCall.tool_name)}</span>
                    <p className="text-sm text-gray-500 font-medium">
                      {toolCall.tool_name.replace(/_/g, ' ')}
                      {toolCall.status === 'calling' && '...'}
                      {toolCall.status === 'completed' && ' ✓'}
                      {toolCall.status === 'error' && ` ✗`}
                    </p>
                    {toolCall.resource_id && (
                      <button
                        onClick={async () => {
                          const resource = await resourcesApi.getResource(toolCall.resource_id!);
                          handleSelectResource(resource);
                        }}
                        className="text-sm text-blue-500 hover:text-blue-700 font-medium underline"
                      >
                        view
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
            {/* Thinking Indicator - Flashing text */}
            {isThinking && (
              <div className="flex justify-start mb-4 px-2">
                <div className="flex items-center gap-2 animate-pulse">
                  <span className="text-lg">🤔</span>
                  <p className="text-sm text-gray-500 font-medium">
                    analyzing results...
                  </p>
                </div>
              </div>
            )}
            {/* Streaming Message - Show text as it arrives */}
            {streamingMessage && (
              <ChatMessage
                role="assistant"
                content={streamingMessage}
                timestamp={new Date().toISOString()}
              />
            )}
            {isLoading && (
              <div className="flex justify-start mb-4 px-2">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
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
        <ChatInput onSendMessage={handleSendMessage} disabled={isLoading || isConnecting || isCheckingConnection} />
      </div>

      {/* Resources Sidebar */}
      <ResourcesSidebar
        resources={resources}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onSelectResource={handleSelectResource}
      />

      {/* Resource Viewer Modal */}
      <ResourceViewer
        resource={selectedResource}
        isOpen={!!selectedResource}
        onClose={() => setSelectedResource(null)}
      />
    </>
  );
}

