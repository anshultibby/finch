'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import ChatMessage from '../ChatMessage';
import ChatInput from '../ChatInput';
import ChatModeBanner from './ChatModeBanner';
import ChatHistorySidebar from './ChatHistorySidebar';
import ChatFilesModal from './ChatFilesModal';
import ResourceViewer from '../ResourceViewer';
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
  SSEOptionsEvent,
  OptionButton
} from '@/lib/api';

export default function ChatView() {
  const { user } = useAuth();
  const { mode } = useChatMode();
  
  // Core state
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatId, setChatId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Streaming state - use refs as source of truth to avoid React batching issues
  const [streamingText, setStreamingText] = useState('');
  const [streamingTools, setStreamingTools] = useState<ToolCallStatus[]>([]);
  const streamingTextRef = useRef('');
  const streamingToolsRef = useRef<ToolCallStatus[]>([]);
  
  // Other state
  const [resources, setResources] = useState<Resource[]>([]);
  const [pendingOptions, setPendingOptions] = useState<SSEOptionsEvent | null>(null);
  const [isChatHistoryOpen, setIsChatHistoryOpen] = useState(true);
  const [isResourcesOpen, setIsResourcesOpen] = useState(false);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [isPortfolioConnected, setIsPortfolioConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionUrl, setConnectionUrl] = useState<string | null>(null);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const userId = user?.id || null;

  // Merge consecutive tool-only messages for cleaner display
  const displayMessages = useMemo(() => {
    const result: Message[] = [];
    
    for (const msg of messages) {
      const isToolOnly = msg.role === 'assistant' && !msg.content && msg.toolCalls && msg.toolCalls.length > 0;
      const lastMsg = result[result.length - 1];
      const lastIsToolOnly = lastMsg && lastMsg.role === 'assistant' && !lastMsg.content && lastMsg.toolCalls && lastMsg.toolCalls.length > 0;
      
      // Merge consecutive tool-only messages
      if (isToolOnly && lastIsToolOnly && lastMsg.toolCalls) {
        lastMsg.toolCalls = [...lastMsg.toolCalls, ...msg.toolCalls!];
      } else {
        result.push({ ...msg });
      }
    }
    
    return result;
  }, [messages]);

  // Initialize chat
  useEffect(() => {
    const initializeChat = async () => {
      if (!userId) return;
      
      try {
        const response = await chatApi.getUserChats(userId);
        if (response.chats && response.chats.length > 0) {
          setChatId(response.chats[0].chat_id);
        } else {
          const newChatId = await chatApi.createChat(userId);
          setChatId(newChatId);
        }
      } catch (err) {
        console.error('Error initializing chat:', err);
        const newChatId = await chatApi.createChat(userId);
        setChatId(newChatId);
      }
    };
    
    initializeChat();
  }, [userId]);

  // Load chat history
  useEffect(() => {
    const loadChatData = async () => {
      if (!chatId) return;
      
      try {
        const displayData = await chatApi.getChatHistoryForDisplay(chatId);
        console.log('📥 Loaded chat history:', displayData);
        const loadedMessages: Message[] = displayData.messages.map((msg: any) => {
          if (msg.tool_calls) {
            console.log('🔧 Message with tool calls:', msg.tool_calls);
          }
          return {
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp || new Date().toISOString(),
            toolCalls: msg.tool_calls
          };
        });
        setMessages(loadedMessages);
        
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
    const checkConnection = async () => {
      if (!userId) return;
      try {
        const status = await snaptradeApi.checkStatus(userId);
        setIsPortfolioConnected(status.is_connected);
      } catch (err) {
        setIsPortfolioConnected(false);
      }
    };
    checkConnection();
  }, [userId]);

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || !userId || !chatId) return;

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    
    // Clear streaming state
    streamingTextRef.current = '';
    streamingToolsRef.current = [];
    setStreamingText('');
    setStreamingTools([]);

    // Helper to save accumulated tools (reads and clears ref synchronously)
    const saveAccumulatedTools = () => {
      const tools = streamingToolsRef.current;
      if (tools.length > 0) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          toolCalls: [...tools],
        }]);
        streamingToolsRef.current = [];
        setStreamingTools([]);
      }
    };

    try {
      chatApi.sendMessageStream(content, userId, chatId, {
        // TEXT STREAMING
        onMessageDelta: (event) => {
          streamingTextRef.current += event.delta;
          setStreamingText(streamingTextRef.current);
        },
        
        // TEXT COMPLETE - save text immediately (text comes before tools)
        onMessageEnd: (event) => {
          if (event.content) {
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: event.content,
              timestamp: event.timestamp,
            }]);
          }
          streamingTextRef.current = '';
          setStreamingText('');
        },
        
        // TOOL START - accumulate in ref
        onToolCallStart: (event: SSEToolCallStartEvent) => {
          // Check for duplicates in ref
          if (streamingToolsRef.current.some(t => t.tool_call_id === event.tool_call_id)) {
            return;
          }
          const newTool: ToolCallStatus = {
            tool_call_id: event.tool_call_id,
            tool_name: event.tool_name,
            status: 'calling',
            statusMessage: event.user_description || event.tool_name,
          };
          streamingToolsRef.current = [...streamingToolsRef.current, newTool];
          setStreamingTools([...streamingToolsRef.current]);
        },
        
        // TOOL COMPLETE - update in ref
        onToolCallComplete: (event: SSEToolCallCompleteEvent) => {
          streamingToolsRef.current = streamingToolsRef.current.map(t =>
            t.tool_call_id === event.tool_call_id
              ? { ...t, status: event.status, error: event.error }
              : t
          );
          setStreamingTools([...streamingToolsRef.current]);
        },
        
        // TOOLS END - save accumulated tools
        onToolsEnd: () => {
          saveAccumulatedTools();
        },
        
        onOptions: (event: SSEOptionsEvent) => {
          setPendingOptions(event);
        },
        
        onDone: async () => {
          setIsLoading(false);
          
          // Save any remaining accumulated tools
          saveAccumulatedTools();
          
          // Reload resources
          try {
            const chatResources = await resourcesApi.getChatResources(chatId!);
            setResources(chatResources);
          } catch (err) {
            console.error('Error reloading resources:', err);
          }
          
          // Trigger chat history sidebar to refresh
          setChatHistoryRefresh(prev => prev + 1);
        },
        
        onError: (event) => {
          console.error('SSE error:', event.error);
          setError(event.error);
          setIsLoading(false);
        },
      });
    } catch (err) {
      setError('Failed to send message');
      setIsLoading(false);
    }
  };

  const handleOptionSelect = async (option: OptionButton) => {
    setPendingOptions(null);
    await handleSendMessage(option.value);
  };

  const handleSelectChat = async (selectedChatId: string) => {
    setChatId(selectedChatId);
    setMessages([]);
    setStreamingText('');
    setStreamingTools([]);
  };

  const handleNewChat = async () => {
    if (!userId) return;
    try {
      const newChatId = await chatApi.createChat(userId);
      setChatId(newChatId);
      setMessages([]);
      setStreamingText('');
      setStreamingTools([]);
      // Trigger chat history sidebar to refresh
      setChatHistoryRefresh(prev => prev + 1);
    } catch (err) {
      console.error('Error creating new chat:', err);
    }
  };

  const getPlaceholder = () => {
    if (mode.type === 'general') return 'Ask me anything about investing...';
    return `Ask about ${mode.type}...`;
  };

  if (!userId) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-500">Please sign in to use the chat.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-white">
      {/* Sidebar */}
      <ChatHistorySidebar
        userId={userId}
        currentChatId={chatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        isOpen={isChatHistoryOpen}
        onToggle={() => setIsChatHistoryOpen(!isChatHistoryOpen)}
        refreshTrigger={chatHistoryRefresh}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative min-w-0 overflow-hidden">
        {/* Minimal floating controls */}
        {!isChatHistoryOpen && (
          <button
            onClick={() => setIsChatHistoryOpen(true)}
            className="absolute top-3 left-3 z-10 p-1.5 bg-white/90 hover:bg-white border border-gray-200 rounded-md shadow-sm backdrop-blur-sm transition-all"
            title="Show chat history"
          >
            <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        )}
        
        {/* Files & Charts button - always visible */}
        <button
          onClick={() => setIsResourcesOpen(true)}
          className="absolute top-3 right-3 z-10 flex items-center gap-1.5 px-2.5 py-1.5 bg-white/90 hover:bg-white border border-gray-200 rounded-md shadow-sm backdrop-blur-sm transition-all text-xs font-medium text-gray-700 hover:border-blue-400"
          title={resources.length > 0 ? `View ${resources.length} files & charts` : 'Files & Charts'}
        >
          <span>📦</span>
          {resources.length > 0 && (
            <span className="font-semibold text-blue-600">{resources.length}</span>
          )}
        </button>

        <ChatModeBanner />

        {/* Messages - min-h-0 fixes flex scroll issue */}
        <div className="flex-1 min-h-0 overflow-y-auto px-6 py-4">
          {!chatId ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex space-x-2">
                <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" />
                <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          ) : messages.length === 0 && !isLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">Welcome to Finch!</h2>
              <p className="text-gray-600 mb-8">Ask me anything about investing.</p>
              <button
                onClick={() => handleSendMessage("review my portfolio")}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Review my portfolio
              </button>
            </div>
          ) : (
            <>
              {/* SAVED MESSAGES (with consecutive tools merged) */}
              {displayMessages.map((msg, i) => (
                <ChatMessage
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  toolCalls={msg.toolCalls}
                  chatId={chatId || undefined}
                />
              ))}

              {/* STREAMING TOOLS (live preview) - render BEFORE text since tools run first */}
              {streamingTools.length > 0 && (
                <ChatMessage role="assistant" content="" toolCalls={streamingTools} chatId={chatId || undefined} />
              )}

              {/* STREAMING TEXT (live preview) - appears below tools */}
              {streamingText && (
                <ChatMessage role="assistant" content={streamingText} chatId={chatId || undefined} />
              )}

              {/* OPTIONS */}
              {pendingOptions && (
                <div className="flex justify-start mb-4">
                  <div className="max-w-[80%] px-3 py-2">
                    <p className="text-gray-900 font-medium mb-3">{pendingOptions.question}</p>
                    <div className="flex flex-wrap gap-2">
                      {pendingOptions.options.map(opt => (
                        <button
                          key={opt.id}
                          onClick={() => handleOptionSelect(opt)}
                          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* LOADING */}
              {isLoading && !streamingText && streamingTools.length === 0 && (
                <div className="flex justify-start mb-4 px-3">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Error */}
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
      </div>
      
      {/* Files Modal with Categories */}
      {chatId && (
        <ChatFilesModal
          isOpen={isResourcesOpen}
          onClose={() => setIsResourcesOpen(false)}
          chatId={chatId}
          onSelectResource={(resource) => {
            setSelectedResource(resource);
            setIsResourcesOpen(false);
          }}
        />
      )}
      
      {/* Resource Viewer Modal */}
      <ResourceViewer
        resource={selectedResource}
        isOpen={!!selectedResource}
        onClose={() => setSelectedResource(null)}
      />
    </div>
  );
}
