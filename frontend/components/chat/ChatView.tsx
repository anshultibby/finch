'use client';

import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from '../ChatMessage';
import ChatInput from '../ChatInput';
import ResourceViewer from '../ResourceViewer';
import ToolCallGroup from '../ToolCallGroup';
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
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const streamingMessageRef = useRef<string>('');
  const [resources, setResources] = useState<Resource[]>([]);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [pendingOptions, setPendingOptions] = useState<SSEOptionsEvent | null>(null);
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
        // Use new backend endpoint that returns UI-ready data (no parsing needed!)
        const displayData = await chatApi.getChatHistoryForDisplay(chatId);
        
        // Convert to local format
        const userMessages: Message[] = displayData.messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString()
        }));
        
        const toolCallTurns: TurnToolCalls[] = displayData.tool_groups.map((group, idx) => ({
          turnId: `turn-${idx}`,
          toolCalls: group.tools.map(tool => ({
            tool_call_id: tool.tool_call_id,
            tool_name: tool.tool_name,
            status: tool.status,
            statusMessage: tool.description,
          })),
          expanded: false,
          messageIndex: group.message_index,
        }));
          
        setMessages(userMessages);
        setToolCallHistory(toolCallTurns);
        
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
    setStreamingMessage('');
    streamingMessageRef.current = '';
    
    // Initialize turn in history BEFORE tools run
    // Note: messageIndex will be updated as messages are added
    setToolCallHistory((prev) => [
      ...prev,
      {
        turnId,
        toolCalls: [],
        expanded: false,  // Start collapsed, users can click to expand
        messageIndex: -1,  // Will be updated when message is added
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
            statusMessage: event.user_description || event.tool_name, // Use LLM-provided description
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
          if (!toolCallStatus) {
            return; // Tool not found in map
          }
          
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
        },
        
        onAssistantMessageDelta: (event) => {
          streamingMessageRef.current += event.delta;
          setStreamingMessage(streamingMessageRef.current);
        },
        
        onAssistantMessage: (event: SSEAssistantMessageEvent) => {
          needsAuth = event.needs_auth;
          
          // Handle messages from message_notify_user and message_ask_user
          // These are complete messages (not deltas) that should be added immediately
          if (event.is_notification || event.is_question) {
            // Clear any streaming message
            streamingMessageRef.current = '';
            setStreamingMessage('');
            
            // Add the notification/question as a complete message
            const newMessage: Message = {
              role: 'assistant',
              content: event.content,
              timestamp: event.timestamp,
            };
            
            setMessages((prev) => {
              const updatedMessages = [...prev, newMessage];
              
              // Update the tool call turn to point to this new message
              if (turnId && Array.from(toolCallsMap.values()).length > 0) {
                const newMessageIndex = updatedMessages.length - 1;
                setToolCallHistory((prevHistory) =>
                  prevHistory.map((turn) =>
                    turn.turnId === turnId
                      ? { ...turn, messageIndex: newMessageIndex }
                      : turn
                  )
                );
              }
              
              return updatedMessages;
            });
            
            // If it's a question (message_ask_user), wait for user response
            // The frontend will display this as a message and wait for the user to reply
          }
        },
        
        onOptions: (event: SSEOptionsEvent) => {
          setPendingOptions(event);
          streamingMessageRef.current = '';
          setStreamingMessage('');
        },
        
        onDone: async () => {
          saveStreamingMessage();
          
          // Update the turn's messageIndex to point to the LAST message
          // (tool calls should appear with the final assistant message)
          if (turnId && Array.from(toolCallsMap.values()).length > 0) {
            setMessages((currentMessages) => {
              const finalMessageIndex = currentMessages.length - 1;
              setToolCallHistory((prev) =>
                prev.map((turn) =>
                  turn.turnId === turnId
                    ? { ...turn, messageIndex: finalMessageIndex }
                    : turn
                )
                );
              return currentMessages;
            });
          } else if (turnId) {
            // No tool calls were made, remove the empty turn from history
            setToolCallHistory((prev) => prev.filter((turn) => turn.turnId !== turnId));
          }
          
          setIsLoading(false);
          setCurrentTurnId(null);
          // Keep currentToolCalls visible briefly, then clear
          // This gives users time to see the completed state before it moves to history
          setTimeout(() => {
            setCurrentToolCalls([]);
          }, 500);
          
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

  const handleFileClick = (filename: string, chatId: string) => {
    // Find the file resource matching the filename
    const fileResource = resources.find(r => 
      r.resource_type === 'file' && 
      r.data?.filename === filename &&
      r.chat_id === chatId
    );
    
    if (fileResource) {
      setSelectedResource(fileResource);
    } else {
      console.warn(`File resource not found: ${filename} in chat ${chatId}`);
    }
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
              // Pass all resources - ChatMessage will match by filename for files,
              // and by time proximity for plots/charts
              const messageResources = resources.filter(r => {
                // For file resources, include all (ChatMessage matches by filename)
                if (r.resource_type === 'file') {
                  return true;
                }
                // For other resources (plots, charts), use time-based matching
                const resourceTime = new Date(r.created_at).getTime();
                return Math.abs(resourceTime - messageTime) < 5000;
              });
              
              const turnForThis = toolCallHistory.find(t => t.messageIndex === index);
              const toolCallsForMessage = turnForThis ? turnForThis.toolCalls : undefined;
              
              return (
                <ChatMessage
                  key={index}
                  role={message.role}
                  content={message.content}
                  timestamp={message.timestamp}
                  resources={messageResources}
                  toolCalls={toolCallsForMessage}
                  onFileClick={handleFileClick}
                  chatId={chatId || undefined}
                />
              );
            })}

            {/* Current Tool Calls - shown during streaming */}
            {currentToolCalls.length > 0 && (
              <div className="mb-4">
                <ToolCallGroup 
                  toolCalls={currentToolCalls}
                  timestamp={new Date().toISOString()}
                />
              </div>
            )}

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
                  onFileClick={handleFileClick}
                  chatId={chatId || undefined}
                />
              </div>
            )}

            {/* Loading dots */}
            {isLoading && currentToolCalls.length === 0 && !streamingMessage && (
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

