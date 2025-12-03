'use client';

import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from '../ChatMessage';
import ChatInput from '../ChatInput';
import ResourceViewer from '../ResourceViewer';
import ChatModeBanner from './ChatModeBanner';
import ChatFilesModal from './ChatFilesModal';
import ChatHistorySidebar from './ChatHistorySidebar';
import { useAuth } from '@/contexts/AuthContext';
import { useChatMode } from '@/contexts/ChatModeContext';
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
  SSEToolStatusEvent,
  SSEToolProgressEvent,
  SSEToolLogEvent,
  OptionButton
} from '@/lib/api';

// Track tool calls per turn
type TurnToolCalls = {
  turnId: string;
  toolCalls: ToolCallStatus[];
  expanded: boolean;
  messageIndex: number;
};

export default function ChatView() {
  const { user } = useAuth();
  const { mode } = useChatMode();
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatId, setChatId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isPortfolioConnected, setIsPortfolioConnected] = useState(false);
  const [connectionUrl, setConnectionUrl] = useState<string | null>(null);
  const [toolCallHistory, setToolCallHistory] = useState<TurnToolCalls[]>([]);
  const [currentTurnId, setCurrentTurnId] = useState<string | null>(null);
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCallStatus[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const streamingMessageRef = useRef<string>('');
  const [resources, setResources] = useState<Resource[]>([]);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [pendingOptions, setPendingOptions] = useState<SSEOptionsEvent | null>(null);
  const [toolStatusMessages, setToolStatusMessages] = useState<Map<string, string>>(new Map());
  const [isFilesModalOpen, setIsFilesModalOpen] = useState(false);
  const [isChatHistoryOpen, setIsChatHistoryOpen] = useState(true); // Open by default
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const userId = user?.id || null;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize chat ID - load most recent chat or create new one
  useEffect(() => {
    const initializeChat = async () => {
      if (!userId) return;
      
      try {
        // Try to load the user's most recent chat
        const response = await chatApi.getUserChats(userId);
        
        if (response.chats && response.chats.length > 0) {
          // Load the most recent chat
          const mostRecentChat = response.chats[0];
          console.log('📝 Loading most recent chat:', mostRecentChat.chat_id);
          setChatId(mostRecentChat.chat_id);
        } else {
          // No chats exist, create a new one
          const newChatId = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          console.log('📝 Creating first chat:', newChatId);
          setChatId(newChatId);
        }
      } catch (err) {
        console.error('Error loading chats:', err);
        // Fallback to creating a new chat
        const newChatId = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        console.log('📝 Creating fallback chat:', newChatId);
        setChatId(newChatId);
      }
    };
    
    initializeChat();
  }, [userId]);

  // Load chat history and resources
  useEffect(() => {
    const loadChatData = async () => {
      if (!chatId) return;
      
      try {
        const history = await chatApi.getChatHistory(chatId);
        const userMessages = history.messages
          .filter((msg: any) => msg.role === 'user' || msg.role === 'assistant')
          .map((msg: any) => ({
            role: msg.role,
            content: msg.content || '',
            timestamp: msg.timestamp
          }));
        setMessages(userMessages);
        
        const chatResources = await resourcesApi.getChatResources(chatId);
        setResources(chatResources);
      } catch (err) {
        console.error('Error loading chat data:', err);
      }
    };
    
    loadChatData();
  }, [chatId]);

  // Check portfolio connection
  useEffect(() => {
    const checkExistingConnection = async () => {
      if (!userId) return;
      
      try {
        const status = await snaptradeApi.checkStatus(userId);
        setIsPortfolioConnected(status.is_connected);
      } catch (err) {
        console.error('Error checking connection status:', err);
        setIsPortfolioConnected(false);
      }
    };
    
    checkExistingConnection();
  }, [userId]);

  // When mode changes, add a system message to guide the conversation
  useEffect(() => {
    if (mode.type !== 'general' && messages.length === 0) {
      const getModePrompt = () => {
        switch (mode.type) {
          case 'create_strategy':
            return "Let's create a new trading strategy! I'll use real market data from FMP to help design a viable strategy with specific rules and thresholds. Tell me what type of stocks you're interested in or what kind of strategy you have in mind.";
          case 'execute_strategy':
            return `Ready to execute "${mode.metadata?.strategyName}". I'll screen candidates, apply your rules, and show you buy/sell decisions.`;
          case 'edit_strategy':
            return `What would you like to change about "${mode.metadata?.strategyName}"? You can modify screening rules, risk parameters, or any other settings.`;
          case 'analyze_performance':
            return "I'll analyze your trading performance and help identify patterns. What would you like to know?";
          default:
            return null;
        }
      };

      const prompt = getModePrompt();
      if (prompt) {
        // Add initial assistant message
        const assistantMessage: Message = {
          role: 'assistant',
          content: prompt,
          timestamp: new Date().toISOString(),
        };
        setMessages([assistantMessage]);
      }
    }
  }, [mode.type]);

  const handleOptionSelect = (option: OptionButton) => {
    setPendingOptions(null);
    
    const userMessage: Message = {
      role: 'user',
      content: option.label,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    
    handleSendMessageInternal(option.label);
  };

  const handleSendMessage = async (content: string) => {
    handleSendMessageInternal(content);
  };

  const handleSendMessageInternal = async (content: string) => {
    if (!userId || !chatId) {
      setError('Session not initialized. Please refresh the page.');
      return;
    }
    
    setError(null);
    setPendingOptions(null);
    
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    const turnId = `turn-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setCurrentTurnId(turnId);
    setCurrentToolCalls([]);
    setIsThinking(false);
    setStreamingMessage('');
    streamingMessageRef.current = '';
    
    // Initialize turn in history BEFORE tools run (like ChatContainer.tsx does)
    const assistantMessageIndex = messages.length + 1;
    setToolCallHistory((prev) => [
      ...prev,
      {
        turnId,
        toolCalls: [],
        expanded: false,  // Start collapsed, users can click to expand
        messageIndex: assistantMessageIndex,
      },
    ]);

    const toolCallsMap = new Map<string, ToolCallStatus>();
    let needsAuth = false;

    const saveStreamingMessage = () => {
      const content = streamingMessageRef.current.trim();
      if (content) {
        const assistantMessage: Message = {
          role: 'assistant',
          content,
          timestamp: new Date().toISOString(),
        };
        setMessages((msgs) => [...msgs, assistantMessage]);
        streamingMessageRef.current = '';
        setStreamingMessage('');
      }
    };

    try {
      chatApi.sendMessageStream(content, userId, chatId, {
        onToolCallStart: (event: SSEToolCallStartEvent) => {
          saveStreamingMessage();
          const toolCallStatus: ToolCallStatus = {
            tool_call_id: event.tool_call_id,
            tool_name: event.tool_name,
            status: 'calling',
          };
          toolCallsMap.set(event.tool_call_id, toolCallStatus);
          setCurrentToolCalls(Array.from(toolCallsMap.values()));
          
          // Update ONLY the current turn in real-time (don't update frozen old turns)
          if (turnId === currentTurnId) {
            setToolCallHistory((prev) =>
              prev.map((turn) =>
                turn.turnId === turnId
                  ? { ...turn, toolCalls: Array.from(toolCallsMap.values()) }
                  : turn
              )
            );
          }
        },
        
        onToolCallComplete: (event: SSEToolCallCompleteEvent) => {
          const toolCallStatus = toolCallsMap.get(event.tool_call_id);
          if (toolCallStatus) {
            toolCallStatus.status = event.status;
            toolCallStatus.resource_id = event.resource_id;
            toolCallStatus.error = event.error;
            setCurrentToolCalls(Array.from(toolCallsMap.values()));
            
            // Update ONLY the current turn in real-time (don't update frozen old turns)
            if (turnId === currentTurnId) {
              setToolCallHistory((prev) =>
                prev.map((turn) =>
                  turn.turnId === turnId
                    ? { ...turn, toolCalls: Array.from(toolCallsMap.values()) }
                    : turn
                )
              );
            }
          }
          // Don't delete the status message - keep it for display even after completion
        },
        
        onToolStatus: (event: SSEToolStatusEvent) => {
          if (event.tool_call_id && (event.message || event.status)) {
            const statusText = event.message || event.status || '';
            
            // Update the status messages map for real-time display
            setToolStatusMessages((prev) => {
              const next = new Map(prev);
              next.set(event.tool_call_id!, statusText);
              return next;
            });
            
            // Also persist it to the tool call object
            const toolCallStatus = toolCallsMap.get(event.tool_call_id!);
            if (toolCallStatus) {
              toolCallStatus.statusMessage = statusText;
              setCurrentToolCalls(Array.from(toolCallsMap.values()));
              
              // Update ONLY the current turn in real-time
              if (turnId === currentTurnId) {
                setToolCallHistory((prev) =>
                  prev.map((turn) =>
                    turn.turnId === turnId
                      ? { ...turn, toolCalls: Array.from(toolCallsMap.values()) }
                      : turn
                  )
                );
              }
            }
          }
        },
        
        onToolProgress: (event: SSEToolProgressEvent) => {
          if (event.tool_call_id) {
            const statusText = event.message || `${Math.round(event.percent)}%`;
            
            // Update the status messages map for real-time display
            setToolStatusMessages((prev) => {
              const next = new Map(prev);
              next.set(event.tool_call_id!, statusText);
              return next;
            });
            
            // Also persist it to the tool call object
            const toolCallStatus = toolCallsMap.get(event.tool_call_id!);
            if (toolCallStatus) {
              toolCallStatus.statusMessage = statusText;
              setCurrentToolCalls(Array.from(toolCallsMap.values()));
              
              // Update ONLY the current turn in real-time
              if (turnId === currentTurnId) {
                setToolCallHistory((prev) =>
                  prev.map((turn) =>
                    turn.turnId === turnId
                      ? { ...turn, toolCalls: Array.from(toolCallsMap.values()) }
                      : turn
                  )
                );
              }
            }
          }
        },
        
        onToolLog: (event: SSEToolLogEvent) => {
          // Optional: show logs in UI
        },
        
        onThinking: (event) => {
          setIsThinking(true);
        },
        
        onAssistantMessageDelta: (event) => {
          setIsThinking(false);
          streamingMessageRef.current += event.delta;
          setStreamingMessage(streamingMessageRef.current);
        },
        
        onAssistantMessage: (event: SSEAssistantMessageEvent) => {
          needsAuth = event.needs_auth;
          setIsThinking(false);
        },
        
        onOptions: (event: SSEOptionsEvent) => {
          setPendingOptions(event);
          setIsThinking(false);
          streamingMessageRef.current = '';
          setStreamingMessage('');
        },
        
        onDone: async () => {
          saveStreamingMessage();
          
          // Tool call history was already updated in real-time
          // Just clean up if no tools were called
          if (turnId && Array.from(toolCallsMap.values()).length === 0) {
            // No tool calls were made, remove the empty turn from history
            setToolCallHistory((prev) => prev.filter((turn) => turn.turnId !== turnId));
          }
          
          setIsLoading(false);
          setCurrentTurnId(null);
          setCurrentToolCalls([]);
          
          try {
            const chatResources = await resourcesApi.getChatResources(chatId);
            setResources(chatResources);
          } catch (err) {
            console.error('Error reloading resources:', err);
          }
          
          if (needsAuth && !isPortfolioConnected) {
            await handleBrokerageConnection();
          }
        },
        
        onError: (event) => {
          console.error('❌ SSE error:', event.error);
          setError(`Error: ${event.error}`);
          setIsLoading(false);
          setIsThinking(false);
          streamingMessageRef.current = '';
          setStreamingMessage('');
          setMessages((prev) => prev.slice(0, -1));
        },
      });
    } catch (err) {
      setError('Failed to send message. Please try again.');
      console.error('Error sending message:', err);
      setMessages((prev) => prev.slice(0, -1));
      setIsLoading(false);
      setIsThinking(false);
      streamingMessageRef.current = '';
      setStreamingMessage('');
    }
  };

  const handleBrokerageConnection = async () => {
    if (!userId) {
      setError('No user ID available');
      return;
    }

    setIsConnecting(true);
    setError(null);
    
    try {
      const redirectUri = `${window.location.origin}${window.location.pathname}?snaptrade_callback=true`;
      const response = await snaptradeApi.initiateConnection(userId, redirectUri);
      
      if (response.success && response.redirect_uri) {
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        const width = 500;
        const height = 700;
        const left = (window.screen.width - width) / 2;
        const top = (window.screen.height - height) / 2;
        
        const popup = window.open(
          response.redirect_uri,
          'SnapTrade Connection',
          isMobile ? '_blank' : `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );
        
        if (!popup || popup.closed || typeof popup.closed === 'undefined') {
          setConnectionUrl(response.redirect_uri);
          setError(null);
        }
      } else {
        setError(response.message || 'Failed to initiate connection');
        setIsConnecting(false);
      }
    } catch (err: any) {
      console.error('Error during connection:', err);
      setError(err.message || 'Failed to connect to backend');
      setIsConnecting(false);
    }
  };

  const handleClearChat = async () => {
    setMessages([]);
    setResources([]);
    setToolCallHistory([]);
    setCurrentToolCalls([]);
    setCurrentTurnId(null);
    
    const newChatId = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setChatId(newChatId);
    setError(null);
  };

  const handleSelectChat = async (selectedChatId: string) => {
    if (selectedChatId === chatId) {
      // Already on this chat
      setIsChatHistoryOpen(false);
      return;
    }

    // Clear current state
    setMessages([]);
    setResources([]);
    setToolCallHistory([]);
    setCurrentToolCalls([]);
    setCurrentTurnId(null);
    setError(null);
    setStreamingMessage('');
    streamingMessageRef.current = '';
    setPendingOptions(null);

    // Set the new chat ID (this will trigger the useEffect to load its data)
    setChatId(selectedChatId);
    setIsChatHistoryOpen(false);
  };

  const handleNewChat = () => {
    const newChatId = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    console.log('📝 Creating new chat:', newChatId);
    
    // Clear current state
    setMessages([]);
    setResources([]);
    setToolCallHistory([]);
    setCurrentToolCalls([]);
    setCurrentTurnId(null);
    setError(null);
    setStreamingMessage('');
    streamingMessageRef.current = '';
    setPendingOptions(null);
    
    setChatId(newChatId);
    setIsChatHistoryOpen(false);
  };

  const handleSelectResource = (resource: Resource) => {
    setSelectedResource(resource);
  };

  const getToolIcon = (toolName: string) => {
    if (toolName.includes('portfolio')) return '📊';
    if (toolName.includes('reddit')) return '📱';
    if (toolName.includes('senate') || toolName.includes('house')) return '🏛️';
    if (toolName.includes('insider')) return '💼';
    if (toolName.includes('fmp')) return '📈';
    if (toolName.includes('strategy')) return '🎯';
    return '🔧';
  };

  const formatToolName = (toolName: string) => {
    const nameMap: Record<string, string> = {
      'get_fmp_company_data': 'company data',
      'get_fmp_quote': 'stock quote',
      'get_fmp_historical_prices': 'historical prices',
      'get_fmp_financial_statements': 'financial statements',
      'get_portfolio_positions': 'portfolio positions',
      'get_reddit_trending': 'reddit trends',
      'get_house_trades': 'house trades',
      'get_senate_trades': 'senate trades',
      'get_insider_trades': 'insider trades',
      'create_strategy_v2': 'create strategy',
      'execute_strategy_v2': 'execute strategy',
    };

    return nameMap[toolName] || toolName.replace(/_/g, ' ').replace('get ', '');
  };

  const renderToolActivity = (turnId: string) => {
    const turn = toolCallHistory.find(t => t.turnId === turnId);
    if (!turn || turn.toolCalls.length === 0) return null;

    const isCurrentTurn = turnId === currentTurnId;
    const allCompleted = turn.toolCalls.every(c => c.status === 'completed');
    const anyError = turn.toolCalls.some(c => c.status === 'error');
    const anyRunning = turn.toolCalls.some(c => c.status === 'calling');

    // For current turn, always show expanded. For completed turns, respect the expanded state.
    const shouldExpand = isCurrentTurn || turn.expanded;

    return (
      <div className="mb-3 px-2">
        {/* Expandable header */}
        <button
          onClick={() => {
            if (!isCurrentTurn) {
              setToolCallHistory((prev) => 
                prev.map((t) => 
                  t.turnId === turnId 
                    ? { ...t, expanded: !t.expanded }
                    : t
                )
              );
            }
          }}
          className={`flex items-start gap-2 w-full text-left ${!isCurrentTurn ? 'group hover:bg-gray-50' : ''} -mx-2 px-2 py-1 rounded-lg transition-colors`}
        >
          {/* Status Icon */}
          <div className="mt-0.5 flex-shrink-0">
            {allCompleted && !isCurrentTurn && (
              <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
            {anyError && !anyRunning && (
              <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            )}
            {anyRunning && (
              <svg className="w-4 h-4 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
          </div>
          
          {/* Summary text */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-600">
                {anyRunning ? 'Running tools...' : allCompleted ? 'Completed' : 'Tool execution'}
              </span>
              {!isCurrentTurn && (
                <svg
                  className={`w-3 h-3 text-gray-400 transition-transform ${
                    shouldExpand ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              )}
            </div>
            <div className="text-[11px] text-gray-400 mt-0.5">
              {turn.toolCalls.length} {turn.toolCalls.length === 1 ? 'action' : 'actions'}
            </div>
          </div>
        </button>

        {/* Expanded activity timeline */}
        {shouldExpand && (
          <div className="ml-1 mt-1.5 pl-3 border-l-2 border-dotted border-gray-200 space-y-2">
            {turn.toolCalls.map((call, index) => {
              const isCompleted = call.status === 'completed';
              const isError = call.status === 'error';
              const isRunning = call.status === 'calling';
              const statusMsg = toolStatusMessages.get(call.tool_call_id);
              
              return (
                <div key={call.tool_call_id} className="relative -ml-[9px]">
                  {/* Activity item */}
                  <div className="flex items-start gap-2 text-sm">
                    {/* Icon - positioned on the border line */}
                    <div className="flex-shrink-0 w-4 h-4 flex items-center justify-center bg-white">
                      {isCompleted && (
                        <svg className="w-3.5 h-3.5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                      {isError && (
                        <svg className="w-3.5 h-3.5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      )}
                      {isRunning && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                      )}
                    </div>
                    
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-1.5">
                        <span className="text-xs font-medium text-gray-700">
                          {formatToolName(call.tool_name)}
                        </span>
                        <span className="text-[10px]">{getToolIcon(call.tool_name)}</span>
                      </div>
                      
                      {/* Show detailed status/description - from persisted statusMessage or live map */}
                      {(call.statusMessage || statusMsg) && (
                        <div className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">
                          {call.statusMessage || statusMsg}
                        </div>
                      )}
                      
                      {/* Show error */}
                      {isError && call.error && (
                        <div className="text-[11px] text-red-600 mt-0.5">
                          Error: {call.error}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const getPlaceholder = () => {
    switch (mode.type) {
      case 'create_strategy':
        return "Describe the type of strategy you want to create...";
      case 'execute_strategy':
        return "Ask questions about the execution results...";
      case 'edit_strategy':
        return "What would you like to change?";
      case 'analyze_performance':
        return "Ask about your trading performance...";
      default:
        return "Ask about your portfolio, market trends, or strategies...";
    }
  };

  return (
    <div className="flex h-full">
      {/* Chat History Sidebar */}
      {userId && (
        <ChatHistorySidebar
          userId={userId}
          currentChatId={chatId}
          onSelectChat={handleSelectChat}
          onNewChat={handleNewChat}
          isOpen={isChatHistoryOpen}
          onToggle={() => setIsChatHistoryOpen(!isChatHistoryOpen)}
        />
      )}

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 min-w-0 relative">
        {/* Expand Sidebar Button - shown when sidebar is collapsed */}
        {!isChatHistoryOpen && (
          <button
            onClick={() => setIsChatHistoryOpen(true)}
            className="absolute top-4 left-4 z-10 p-2 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg shadow-sm transition-colors"
            title="Show chat history"
          >
            <svg
              className="w-5 h-5 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        )}

        {/* Chat Mode Banner */}
        <ChatModeBanner />

      {/* Header with Files Button */}
      {messages.length > 0 && (
        <div className="px-6 py-3 border-b border-gray-200 flex items-center justify-end bg-white">
          <button
            onClick={() => setIsFilesModalOpen(true)}
            className="text-sm text-gray-600 hover:text-gray-900 transition-colors flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-100"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            View all files in this chat
          </button>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 chat-scrollbar bg-white">
        {!chatId ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex space-x-2">
              <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce"></div>
              <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        ) : messages.length === 0 && mode.type === 'general' ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="bg-white rounded-full p-6 shadow-lg mb-6">
              <svg
                className="w-16 h-16 text-purple-600"
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
              Welcome to Finch Chat!
            </h2>
            <p className="text-gray-600 max-w-md mb-8">
              Ask me anything about your portfolio, market trends, or trading strategies.
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
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => {
              const messageTime = message.timestamp ? new Date(message.timestamp).getTime() : 0;
              const messageResources = resources.filter(r => {
                const resourceTime = new Date(r.created_at).getTime();
                return Math.abs(resourceTime - messageTime) < 5000;
              });
              
              const turnForThis = toolCallHistory.find(t => t.messageIndex === index);
              
              return (
                <React.Fragment key={index}>
                  <ChatMessage
                    role={message.role}
                    content={message.content}
                    timestamp={message.timestamp}
                    resources={messageResources}
                  />
                  {turnForThis && renderToolActivity(turnForThis.turnId)}
                </React.Fragment>
              );
            })}

            {/* Options Display */}
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
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
            
            {/* Streaming message */}
            {streamingMessage && (
              <div className="mb-4">
                <ChatMessage
                  role="assistant"
                  content={streamingMessage}
                  timestamp={new Date().toISOString()}
                />
              </div>
            )}

            {/* Thinking indicator */}
            {isThinking && !streamingMessage && (
              <div className="flex justify-start mb-3 px-2">
                <div className="flex items-center gap-1.5">
                  <div className="flex space-x-1">
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                  <p className="text-xs text-gray-400">
                    thinking...
                  </p>
                </div>
              </div>
            )}

            {/* Loading dots */}
            {isLoading && currentToolCalls.length === 0 && !streamingMessage && !isThinking && (
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
      <div className="border-t border-gray-200 bg-white">
        <div className="max-w-4xl mx-auto">
          <ChatInput 
            onSendMessage={handleSendMessage} 
            disabled={isLoading || isConnecting || !!pendingOptions}
            placeholder={getPlaceholder()}
          />
        </div>
      </div>

      {/* Resource Viewer Modal */}
      <ResourceViewer
        resource={selectedResource}
        isOpen={!!selectedResource}
        onClose={() => setSelectedResource(null)}
      />

      {/* Files modal */}
      {chatId && (
        <ChatFilesModal
          isOpen={isFilesModalOpen}
          onClose={() => setIsFilesModalOpen(false)}
          chatId={chatId}
          onSelectResource={handleSelectResource}
        />
      )}
      </div>
    </div>
  );
}

