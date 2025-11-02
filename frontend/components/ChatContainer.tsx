'use client';

import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ResourcesSidebar from './ResourcesSidebar';
import ResourceViewer from './ResourceViewer';
import ProfileDropdown from './ProfileDropdown';
import { useAuth } from '@/contexts/AuthContext';
import { 
  chatApi, 
  snaptradeApi, 
  resourcesApi, 
  Message, 
  ToolCallStatus, 
  Resource,
  SSEToolCallStartEvent,
  SSEToolCallCompleteEvent,
  SSEAssistantMessageEvent,
  SSEOptionsEvent,
  OptionButton
} from '@/lib/api';

export default function ChatContainer() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatId, setChatId] = useState<string | null>(null); // Per-session - for chat history
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isPortfolioConnected, setIsPortfolioConnected] = useState(false);
  const [connectionUrl, setConnectionUrl] = useState<string | null>(null);
  const [ephemeralToolCalls, setEphemeralToolCalls] = useState<ToolCallStatus[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string>('');  // Accumulate streaming tokens
  const [resources, setResources] = useState<Resource[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [pendingOptions, setPendingOptions] = useState<SSEOptionsEvent | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Use Supabase user ID
  const userId = user?.id || null;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize chat ID (new each time - for chat history)
  useEffect(() => {
    if (!userId) return;
    
    // Create new chat ID for this conversation (resets on page refresh)
    const newChatId = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setChatId(newChatId);
  }, [userId]);

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
      if (!userId) {
        console.log('⏸️  No userId yet, skipping connection check');
        return;
      }
      
      console.log('🔍 Checking connection status for userId:', userId);
      
      try {
        const status = await snaptradeApi.checkStatus(userId);
        console.log('📊 Connection status response:', status);
        
        if (status.is_connected) {
          console.log('✅ Found existing SnapTrade connection');
          setIsPortfolioConnected(true);
        } else {
          console.log('❌ No active connection found');
          setIsPortfolioConnected(false);
        }
      } catch (err) {
        console.error('⚠️  Error checking connection status:', err);
        setIsPortfolioConnected(false);
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
            setConnectionUrl(null); // Clear the connection URL
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
      console.log('📨 Received postMessage:', event.data);
      
      // Verify origin for security
      if (event.origin !== window.location.origin) {
        console.log('⚠️  Message from different origin, ignoring:', event.origin);
        return;
      }
      
      if (event.data.type === 'SNAPTRADE_CONNECTION') {
        console.log('🔗 SnapTrade connection message received:', event.data);
        setIsConnecting(false);
        setConnectionUrl(null); // Clear the connection URL
        if (event.data.success && event.data.is_connected) {
          console.log('✅ Setting portfolio to connected');
          setIsPortfolioConnected(true);
          setError(null);
        } else {
          console.log('❌ Connection failed:', event.data.message);
          setError(event.data.message || 'Failed to connect');
        }
      }
    };
    
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleOptionSelect = (option: OptionButton) => {
    // Clear pending options
    const selectedOptions = pendingOptions;
    setPendingOptions(null);
    
    // Add a user message showing what they selected (using the nice label)
    const userMessage: Message = {
      role: 'user',
      content: option.label,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    
    // Send the option value to the backend (this is what the LLM sees)
    setIsLoading(true);
    setEphemeralToolCalls([]);
    setIsThinking(false);
    setStreamingMessage('');
    
    // Track tool calls and resources
    const toolCallsMap = new Map<string, ToolCallStatus>();
    let needsAuth = false;

    if (!userId || !chatId) {
      setError('Session not initialized. Please refresh the page.');
      return;
    }

    try {
      // Use streaming API - send the label to backend
      const eventSource = chatApi.sendMessageStream(
        option.label, // Backend gets the full label (e.g., "Short term (1-4 weeks)")
        userId,
        chatId,
        {
          onToolCallStart: (event: SSEToolCallStartEvent) => {
            console.log('🔧 Tool call started:', event.tool_name);
            setStreamingMessage('');
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
            setIsThinking(true);
          },
          
          onAssistantMessageDelta: (event) => {
            console.log('💬 Streaming delta received:', event.delta.substring(0, 50));
            setIsThinking(false);
            setStreamingMessage((prev) => {
              const newContent = prev + event.delta;
              console.log('📝 Current streaming message length:', newContent.length);
              return newContent;
            });
          },
          
          onAssistantMessage: (event: SSEAssistantMessageEvent) => {
            console.log('💬 Assistant message received (complete)');
            needsAuth = event.needs_auth;
            setIsThinking(false);
            setStreamingMessage('');
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
          
          onOptions: (event: SSEOptionsEvent) => {
            console.log('🔘 Options received:', event.question, event.options);
            setPendingOptions(event);
            setIsThinking(false);
            setStreamingMessage('');
          },
          
          onDone: async () => {
            console.log('✨ Stream complete');
            setIsLoading(false);
            try {
              const chatResources = await resourcesApi.getChatResources(chatId);
              setResources(chatResources);
            } catch (err) {
              console.error('Error reloading resources:', err);
            }
            if (needsAuth && !isPortfolioConnected) {
              setIsPortfolioConnected(false);
              await handleBrokerageConnection();
            }
            setTimeout(() => setEphemeralToolCalls([]), 5000);
          },
          
          onError: (event) => {
            console.error('❌ SSE error:', event.error);
            setError(`Error: ${event.error}`);
            setIsLoading(false);
            setIsThinking(false);
            setStreamingMessage('');
            setMessages((prev) => prev.slice(0, -1));
          },
        }
      );
    } catch (err) {
      setError('Failed to send message. Please try again.');
      console.error('Error sending message:', err);
      setMessages((prev) => prev.slice(0, -1));
      setIsLoading(false);
      setIsThinking(false);
      setStreamingMessage('');
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!userId || !chatId) {
      setError('Session not initialized. Please refresh the page.');
      return;
    }
    
    setError(null);
    
    // Clear pending options when sending a new message
    setPendingOptions(null);
    
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
            
            setIsThinking(false);
            
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
          
          onOptions: (event: SSEOptionsEvent) => {
            console.log('🔘 Options received:', event.question, event.options);
            
            // Store pending options to display
            setPendingOptions(event);
            
            // Hide thinking and streaming indicators
            setIsThinking(false);
            setStreamingMessage('');
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

    console.log('🔗 Starting brokerage connection for userId:', userId);
    setIsConnecting(true);
    setError(null); // Clear any previous errors
    
    try {
      // Get redirect URI from backend
      const redirectUri = `${window.location.origin}${window.location.pathname}?snaptrade_callback=true`;
      console.log('🌐 Current origin:', window.location.origin);
      console.log('📡 Redirect URI being sent to backend:', redirectUri);
      console.log('📡 Calling backend API to get redirect URI...');
      const response = await snaptradeApi.initiateConnection(userId, redirectUri);
      console.log('📡 Backend response:', response);
      console.log('📡 SnapTrade OAuth URL:', response.redirect_uri);
      
      if (response.success && response.redirect_uri) {
        console.log('✅ Got redirect URI');
        
        // Detect if we're on mobile
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        
        // Try to open popup/new tab
        const width = 500;
        const height = 700;
        const left = (window.screen.width - width) / 2;
        const top = (window.screen.height - height) / 2;
        
        const popup = window.open(
          response.redirect_uri,
          'SnapTrade Connection',
          isMobile ? '_blank' : `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );
        
        // Check if popup was blocked
        if (!popup || popup.closed || typeof popup.closed === 'undefined') {
          console.error('❌ Popup was blocked!');
          // Store the URL so we can show a clickable link
          setConnectionUrl(response.redirect_uri);
          setError(null); // Clear error, we'll show a better UI
          // Stay in connecting state to show the link UI
        } else {
          console.log('✅ Popup/tab opened successfully');
          // Keep connecting state active until callback is received
        }
      } else {
        console.error('❌ Failed to get redirect URI:', response.message);
        
        // Check if we need a new user session
        if (response.message?.includes('refresh the page') || response.message?.includes('new session')) {
          setError('Session error. Please sign out and sign back in.');
          setIsConnecting(false);
        } else {
          setError(response.message || 'Failed to initiate connection');
          setIsConnecting(false);
        }
      }
    } catch (err: any) {
      console.error('❌ Error during connection:', err);
      setError(err.message || 'Failed to connect to backend. Make sure the backend server is running.');
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
            disabled={isConnecting}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              isPortfolioConnected
                ? 'bg-green-600 hover:bg-green-700 text-white'
                : isConnecting
                ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            } disabled:opacity-50`}
          >
            <span className="text-lg">
              {isConnecting ? '⏳' : isPortfolioConnected ? '🚀' : '🔗'}
            </span>
            {isConnecting ? 'Connecting...' : isPortfolioConnected ? 'Connected' : 'Connect Brokerage'}
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
          
          {/* Profile Dropdown */}
          <div className="border-l pl-3 ml-3">
            <ProfileDropdown />
          </div>
        </div>
      </div>

      {/* Connection Prompt Banner */}
      {!isPortfolioConnected && !isConnecting && messages.length === 0 && (
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
      {isConnecting && !connectionUrl && (
        <div className="mx-6 mt-4 bg-gradient-to-r from-yellow-50 to-amber-50 border-2 border-yellow-500 rounded-lg p-4 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="text-2xl animate-pulse">🔗</div>
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-900 mb-1">
                Connecting...
              </h3>
              <p className="text-sm text-yellow-700">
                Please complete the connection process in the popup window. The window will close automatically once you're connected.
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Connection Link Banner (when popup is blocked) */}
      {isConnecting && connectionUrl && (
        <div className="mx-6 mt-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-500 rounded-lg p-4 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="text-2xl">🔗</div>
            <div className="flex-1">
              <h3 className="font-semibold text-blue-900 mb-1">
                Popup Blocked
              </h3>
              <p className="text-sm text-blue-700 mb-3">
                Your browser blocked the popup. Click the button below to connect your brokerage in a new tab. You'll be redirected back here automatically after connecting.
              </p>
              <a
                href={connectionUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
              >
                <span>🚀</span>
                Open Connection Page
              </a>
              <button
                onClick={() => {
                  setConnectionUrl(null);
                  setIsConnecting(false);
                }}
                className="ml-3 text-sm text-blue-600 hover:text-blue-800 underline"
              >
                Cancel
              </button>
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
            {messages.map((message, index) => {
              // Find resources created around the time of this message
              // Resources are created when tools complete, so match by timestamp proximity
              const messageTime = message.timestamp ? new Date(message.timestamp).getTime() : 0;
              const messageResources = resources.filter(r => {
                const resourceTime = new Date(r.created_at).getTime();
                // Match resources created within 5 seconds of this message
                return Math.abs(resourceTime - messageTime) < 5000;
              });
              
              return (
                <ChatMessage
                  key={index}
                  role={message.role}
                  content={message.content}
                  timestamp={message.timestamp}
                  resources={messageResources}
                />
              );
            })}
            {/* Options Display - Inline with messages */}
            {pendingOptions && (
              <div className="flex justify-start mb-6 px-2 animate-fadeIn">
                <div className="max-w-[95%]">
                  <div className="mb-3 px-1">
                    <p className="text-[15px] text-gray-900 font-medium leading-relaxed">
                      {pendingOptions.question}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    {pendingOptions.options.map((option, index) => (
                      <button
                        key={option.id}
                        onClick={() => handleOptionSelect(option)}
                        className="group relative bg-gradient-to-br from-gray-50 to-gray-100/80 hover:from-gray-100 hover:to-gray-200/80 text-left px-6 py-4 rounded-xl border border-gray-200/80 hover:border-gray-300 transition-all duration-300 ease-out shadow-sm hover:shadow-md hover:scale-[1.02] active:scale-[0.98] min-w-[200px] max-w-[320px] flex-1"
                        style={{ 
                          animationDelay: `${index * 75}ms`,
                          animation: 'slideInFromLeft 0.4s ease-out forwards'
                        }}
                        title={option.description}
                      >
                        <div className="relative z-10">
                          <p className="font-semibold text-gray-900 text-[15px] mb-1.5 leading-tight">
                            {option.label}
                          </p>
                          {option.description && (
                            <p className="text-[13px] text-gray-600 leading-relaxed">
                              {option.description}
                            </p>
                          )}
                        </div>
                        {/* Subtle shine effect on hover */}
                        <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                        {/* Accent border glow on hover */}
                        <div className="absolute inset-0 rounded-xl ring-2 ring-primary-400/0 group-hover:ring-primary-400/30 transition-all duration-300 pointer-events-none"></div>
                      </button>
                    ))}
                  </div>
                  <style jsx>{`
                    @keyframes slideInFromLeft {
                      from {
                        opacity: 0;
                        transform: translateX(-20px);
                      }
                      to {
                        opacity: 1;
                        transform: translateX(0);
                      }
                    }
                    @keyframes fadeIn {
                      from {
                        opacity: 0;
                      }
                      to {
                        opacity: 1;
                      }
                    }
                  `}</style>
                </div>
              </div>
            )}
            
            {/* Status Area - All indicators occupy the same space and overwrite each other */}
            {(ephemeralToolCalls.length > 0 || isThinking || streamingMessage) && (
              <div className="mb-4">
                {/* Show streaming message first if available */}
                {streamingMessage ? (
                  <ChatMessage
                    role="assistant"
                    content={streamingMessage}
                    timestamp={new Date().toISOString()}
                  />
                ) : isThinking ? (
                  /* Show thinking indicator if no streaming message */
                  <div className="flex justify-start px-2">
                    <div className="flex items-center gap-2 animate-pulse">
                      <span className="text-lg">🤔</span>
                      <p className="text-sm text-gray-500 font-medium">
                        analyzing results...
                      </p>
                    </div>
                  </div>
                ) : ephemeralToolCalls.length > 0 ? (
                  /* Show tool calls if no thinking or streaming */
                  <div className="space-y-2 px-2">
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
                ) : null}
              </div>
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
      <ChatInput onSendMessage={handleSendMessage} disabled={isLoading || isConnecting || !!pendingOptions} />
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

