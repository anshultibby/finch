'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ChatModeBanner from './ChatModeBanner';
import ChatHistorySidebar, { ChatHistorySidebarRef } from './ChatHistorySidebar';
import NewChatWelcome from './NewChatWelcome';
import ChatDebugPanel from './ChatDebugPanel';
import ResourceViewer from '../ResourceViewer';
import ComputerPanel from '../ComputerPanel';
import { FileItem } from '../FileTree';
import { useAuth } from '@/contexts/AuthContext';
import { useChatMode } from '@/contexts/ChatModeContext';
import { chatApi, snaptradeApi, resourcesApi } from '@/lib/api';
import { getFileType, getApiBaseUrl } from '@/lib/utils';
import type {
  Message,
  ToolCallStatus,
  Resource,
  SSEToolCallStartEvent,
  SSEToolCallCompleteEvent,
  SSEToolCallStreamingEvent,
  SSEOptionsEvent,
  SSEFileContentEvent,
  OptionButton,
  ImageAttachment,
} from '@/lib/types';

// Helper to convert internal/technical errors to user-friendly messages
function formatErrorForUser(error: string): string {
  // JSON parsing errors (internal backend errors)
  if (error.includes('Expecting') && error.includes('delimiter') || 
      error.includes('JSONDecodeError') ||
      error.match(/line \d+ column \d+/)) {
    return 'Something went wrong processing the response. Please try again.';
  }
  
  // Python tracebacks
  if (error.includes('Traceback') || error.includes('File "')) {
    return 'An internal error occurred. Please try again.';
  }
  
  // Generic internal errors
  if (error.includes('Internal Server Error') || error.includes('500')) {
    return 'Server error. Please try again in a moment.';
  }
  
  // Connection errors
  if (error.includes('fetch') || error.includes('network') || error.includes('ECONNREFUSED')) {
    return 'Connection error. Please check your internet connection.';
  }
  
  // If it's already user-friendly, return as-is
  return error;
}

// Per-chat state stored in refs (persists across chat switches)
interface ChatStreamState {
  messages: Message[];
  streamingText: string;
  streamingTools: ToolCallStatus[];
  isLoading: boolean;
  error: string | null;
  pendingOptions: SSEOptionsEvent | null;
  resources: Resource[];
  stream: { close: () => void; reconnect: () => void } | null;
  chatFiles: FileItem[]; // Cached file list for file explorer
  toolInsertionCounter: number; // Counter for assigning stable insertion order to tools
  wasStreamingBeforeHidden: boolean; // Track if stream was active when tab was hidden
}

export default function ChatView() {
  const { user } = useAuth();
  const { mode } = useChatMode();
  
  // Current chat being viewed
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [isNewChat, setIsNewChat] = useState(false);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  
  // Display state (reflects the currently viewed chat)
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState('');
  const [streamingTools, setStreamingTools] = useState<ToolCallStatus[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingOptions, setPendingOptions] = useState<SSEOptionsEvent | null>(null);
  const [resources, setResources] = useState<Resource[]>([]);
  const [chatFiles, setChatFiles] = useState<FileItem[]>([]);
  
  // Per-chat state storage (keyed by chatId)
  const chatStatesRef = useRef<Map<string, ChatStreamState>>(new Map());
  
  // Computer panel state
  const [selectedTool, setSelectedTool] = useState<ToolCallStatus | null>(null);
  
  
  // UI state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [isPortfolioConnected, setIsPortfolioConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const skipNextHistoryLoad = useRef(false);
  const currentChatIdRef = useRef<string | null>(null);
  const chatHistorySidebarRef = useRef<ChatHistorySidebarRef>(null);

  const userId = user?.id || null;
  
  // Keep ref in sync with state
  currentChatIdRef.current = currentChatId;

  // Get or create chat state
  const getChatState = useCallback((chatId: string): ChatStreamState => {
    if (!chatStatesRef.current.has(chatId)) {
      chatStatesRef.current.set(chatId, {
        messages: [],
        streamingText: '',
        streamingTools: [],
        isLoading: false,
        error: null,
        pendingOptions: null,
        resources: [],
        stream: null,
        chatFiles: [],
        toolInsertionCounter: 0,
        wasStreamingBeforeHidden: false,
      });
    }
    return chatStatesRef.current.get(chatId)!;
  }, []);

  // Update chat state and sync to display if it's the current chat
  // Uses ref instead of state to avoid stale closure issues during streaming
  const updateChatState = useCallback((chatId: string, updates: Partial<ChatStreamState>) => {
    const state = getChatState(chatId);
    Object.assign(state, updates);
    
    // If this is the currently viewed chat, update display state
    // Use ref to get the latest value (avoids stale closure from React state)
    if (chatId === currentChatIdRef.current) {
      if ('messages' in updates) setMessages(state.messages);
      if ('streamingText' in updates) setStreamingText(state.streamingText);
      if ('streamingTools' in updates) setStreamingTools(state.streamingTools);
      if ('isLoading' in updates) setIsLoading(state.isLoading);
      if ('error' in updates) setError(state.error);
      if ('pendingOptions' in updates) setPendingOptions(state.pendingOptions);
      if ('resources' in updates) setResources(state.resources);
      if ('chatFiles' in updates) setChatFiles(state.chatFiles);
    }
  }, [getChatState]);

  // Helper to add or update a tool while maintaining stable insertion order
  // Each tool gets a unique _insertionOrder when first seen, which never changes
  // Tools are always sorted by _insertionOrder for display, ensuring stable rendering
  const addOrUpdateTool = useCallback((chatId: string, newTool: ToolCallStatus): ToolCallStatus[] => {
    const state = getChatState(chatId);
    const existingTool = state.streamingTools.find(t => t.tool_call_id === newTool.tool_call_id);
    
    if (existingTool) {
      // Update existing tool - preserve its original insertion order
      return state.streamingTools.map(t => 
        t.tool_call_id === newTool.tool_call_id 
          ? { ...t, ...newTool, _insertionOrder: existingTool._insertionOrder } 
          : t
      );
    } else {
      // New tool - assign next insertion order and append
      const insertionOrder = state.toolInsertionCounter++;
      return [...state.streamingTools, { ...newTool, _insertionOrder: insertionOrder }];
    }
  }, [getChatState]);

  // Sync display state when switching chats
  const syncDisplayToChat = useCallback((chatId: string | null) => {
    if (!chatId) {
      setMessages([]);
      setStreamingText('');
      setStreamingTools([]);
      setIsLoading(false);
      setError(null);
      setPendingOptions(null);
      setResources([]);
      setChatFiles([]);
      return;
    }
    
    const state = getChatState(chatId);
    setMessages(state.messages);
    setStreamingText(state.streamingText);
    setStreamingTools(state.streamingTools);
    setIsLoading(state.isLoading);
    setError(state.error);
    setPendingOptions(state.pendingOptions);
    setResources(state.resources);
    setChatFiles(state.chatFiles);
  }, [getChatState]);

  // Handle visibility changes - smart reconnection when returning
  useEffect(() => {
    const handleVisibilityChange = async () => {
      if (document.hidden) {
        // Tab is being hidden - mark active streams but DON'T close them yet
        // This allows the stream to continue in the background
        chatStatesRef.current.forEach((state, chatId) => {
          if (state.stream && state.isLoading) {
            console.log(`Marking stream for chat ${chatId} as hidden`);
            state.wasStreamingBeforeHidden = true;
          }
        });
      } else if (currentChatId) {
        // Tab became visible - implement smart reconnection
        const state = getChatState(currentChatId);
        
        // If stream was active before hiding, attempt reconnection
        if (state.wasStreamingBeforeHidden) {
          console.log(`Tab visible - checking if chat ${currentChatId} is still processing`);
          
          try {
            // Check if backend is still processing this chat
            const status = await chatApi.checkChatStatus(currentChatId);
            
            if (status.is_processing) {
              console.log('Backend still processing - attempting to reconnect stream...');
              
              // Try to reconnect the existing stream
              if (state.stream) {
                state.stream.reconnect();
              } else {
                // Stream was lost - keep existing messages in memory, only update resources
                console.log('Stream lost - keeping in-memory messages, refreshing resources');
                
                const [chatResources, chatFilesResponse] = await Promise.all([
                  resourcesApi.getChatResources(currentChatId),
                  fetch(`${getApiBaseUrl()}/api/chat-files/${currentChatId}`)
                    .then(r => r.ok ? r.json() : [])
                    .catch(() => [])
                ]);
                
                // CRITICAL FIX: Keep existing messages! Only update resources and state flags
                // The in-memory messages are the source of truth - they have everything that was streamed
                // The database might not have finished saving yet, so don't reload from it
                updateChatState(currentChatId, {
                  // messages: UNCHANGED - keep what we have in memory!
                  streamingText: '',
                  streamingTools: [],
                  isLoading: true, // Still processing
                  resources: chatResources,
                  chatFiles: chatFilesResponse,
                  wasStreamingBeforeHidden: false,
                });
                
                // Poll for completion
                const pollInterval = setInterval(async () => {
                  const currentStatus = await chatApi.checkChatStatus(currentChatId);
                  if (!currentStatus.is_processing) {
                    clearInterval(pollInterval);
                    // Processing complete - refresh resources but KEEP existing messages
                    const [finalResources, finalFiles] = await Promise.all([
                      resourcesApi.getChatResources(currentChatId),
                      fetch(`${getApiBaseUrl()}/api/chat-files/${currentChatId}`)
                        .then(r => r.ok ? r.json() : [])
                        .catch(() => [])
                    ]);
                    updateChatState(currentChatId, {
                      // messages: UNCHANGED - trust the in-memory state!
                      isLoading: false,
                      resources: finalResources,
                      chatFiles: finalFiles,
                    });
                    clearInterval(pollInterval);
                  }
                }, 2000);
              }
            } else {
              // Backend no longer processing - refresh resources but KEEP existing messages
              console.log('Backend not processing - keeping in-memory messages');
              
              const [chatResources, chatFilesResponse] = await Promise.all([
                resourcesApi.getChatResources(currentChatId),
                fetch(`${getApiBaseUrl()}/api/chat-files/${currentChatId}`)
                  .then(r => r.ok ? r.json() : [])
                  .catch(() => [])
              ]);
              
              // CRITICAL FIX: Keep existing messages! They are the source of truth
              updateChatState(currentChatId, {
                // messages: UNCHANGED
                streamingText: '',
                streamingTools: [],
                isLoading: false,
                stream: null,
                resources: chatResources,
                chatFiles: chatFilesResponse,
                wasStreamingBeforeHidden: false,
              });
            }
          } catch (err) {
            console.error('Error during reconnection:', err);
            // Fall back to just syncing display state - DON'T reload from database
            setMessages([...state.messages]);
            setStreamingText(state.streamingText);
            setStreamingTools([...state.streamingTools]);
            setIsLoading(false);
            setError('Connection lost. Please refresh the page if messages are missing.');
            state.wasStreamingBeforeHidden = false;
          }
        } else {
          // No active stream before hiding - just sync display state
          setMessages([...state.messages]);
          setStreamingText(state.streamingText);
          setStreamingTools([...state.streamingTools]);
          setIsLoading(state.isLoading);
          setError(state.error);
          setPendingOptions(state.pendingOptions);
          setResources([...state.resources]);
          setChatFiles([...state.chatFiles]);
        }
      }
    };

    const handleBeforeUnload = () => {
      // Page is being unloaded - close all active streams
      chatStatesRef.current.forEach((state) => {
        if (state.stream) {
          state.stream.close();
        }
      });
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [currentChatId, getChatState, updateChatState]);


  // Update selected tool when streaming tools change
  // Keep panel open - only update content if the same tool is being updated
  useEffect(() => {
    if (selectedTool) {
      const updated = streamingTools.find(t => t.tool_call_id === selectedTool.tool_call_id);
      
      if (updated) {
        // Update the content of the currently viewed tool
        setSelectedTool(updated);
      }
      // Don't close the panel when streaming ends - let user close it manually
    }
  }, [streamingTools, selectedTool?.tool_call_id]);

  // Initialize chat
  useEffect(() => {
    const initializeChat = async () => {
      if (!userId) return;
      
      try {
        const response = await chatApi.getUserChats(userId);
        if (response.chats && response.chats.length > 0) {
          setCurrentChatId(response.chats[0].chat_id);
          setIsNewChat(false);
        } else {
          setCurrentChatId(null);
          setIsNewChat(true);
        }
      } catch (err) {
        console.error('Error initializing chat:', err);
        setCurrentChatId(null);
        setIsNewChat(true);
      }
    };
    
    initializeChat();
  }, [userId]);

  // Load chat history when switching to a chat
  useEffect(() => {
    const loadChatData = async () => {
      if (!currentChatId) return;
      
      if (skipNextHistoryLoad.current) {
        skipNextHistoryLoad.current = false;
        return;
      }
      
      const state = getChatState(currentChatId);
      
      // If this chat is currently streaming, just sync the display
      if (state.isLoading || state.stream) {
        syncDisplayToChat(currentChatId);
        return;
      }
      
      // CRITICAL FIX: If we already have messages loaded and no active stream, use cached state
      // NEVER reload from database when we have messages in memory - this prevents message loss
      // The in-memory state is the source of truth until we explicitly clear it (e.g., switching chats)
      if (state.messages.length > 0) {
        syncDisplayToChat(currentChatId);
        return;
      }
      
      // Only load from database if we have NO messages at all
      try {
        const displayData = await chatApi.getChatHistoryForDisplay(currentChatId);
        const loadedMessages: Message[] = displayData.messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
          toolCalls: msg.tool_calls
        }));
        
        const chatResources = await resourcesApi.getChatResources(currentChatId);
        
        updateChatState(currentChatId, {
          messages: loadedMessages,
          resources: chatResources,
        });
      } catch (err) {
        console.error('Error loading chat data:', err);
      }
    };
    
    loadChatData();
  }, [currentChatId, getChatState, syncDisplayToChat, updateChatState]);

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

  // Stop a specific chat's stream
  const stopChatStream = useCallback((chatId: string, savePartialResponse: boolean = false) => {
    const state = getChatState(chatId);
    
    if (state.stream) {
      state.stream.close();
    }
    
    if (savePartialResponse) {
      const newMessages = [...state.messages];
      
      if (state.streamingTools.length > 0) {
        newMessages.push({
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          toolCalls: state.streamingTools.map(t => ({ 
            ...t, 
            status: t.status === 'calling' ? 'completed' : t.status 
          })),
        });
      }
      
      if (state.streamingText) {
        newMessages.push({
          role: 'assistant',
          content: state.streamingText + ' [interrupted]',
          timestamp: new Date().toISOString(),
        });
      }
      
      updateChatState(chatId, {
        messages: newMessages,
        streamingText: '',
        streamingTools: [],
        isLoading: false,
        stream: null,
      });
    } else {
      updateChatState(chatId, {
        streamingText: '',
        streamingTools: [],
        isLoading: false,
        stream: null,
      });
    }
  }, [getChatState, updateChatState]);

  const handleSendMessage = async (content: string, images?: ImageAttachment[]) => {
    if ((!content.trim() && (!images || images.length === 0)) || !userId) return;
    
    const trimmedContent = content.trim();
    const displayContent = trimmedContent + (images && images.length > 0 ? ` [${images.length} image${images.length > 1 ? 's' : ''} attached]` : '');
    const attachedImages = images;

    // Determine target chat ID - generate immediately if new chat
    let targetChatId: string;
    
    if (isNewChat || !currentChatId) {
      // Generate UUID client-side for immediate use
      targetChatId = crypto.randomUUID();
      skipNextHistoryLoad.current = true;
      currentChatIdRef.current = targetChatId;
      setCurrentChatId(targetChatId);
      setIsNewChat(false);
      
      // Initialize state for new chat
      getChatState(targetChatId);
    } else {
      targetChatId = currentChatId;
      
      // If currently streaming in this chat, interrupt it
      if (getChatState(targetChatId).isLoading) {
        stopChatStream(targetChatId, true);
      }
    }

    const userMessage: Message = {
      role: 'user',
      content: displayContent,
      timestamp: new Date().toISOString(),
    };

    // Update ref state
    const state = getChatState(targetChatId);
    state.messages = [...state.messages, userMessage];
    state.isLoading = true;
    state.toolInsertionCounter = 0; // Reset counter for new message stream

    // Show user message and loading state IMMEDIATELY
    setMessages([...state.messages]);
    setStreamingText('');
    setStreamingTools([]);
    setIsLoading(true);
    setError(null);

    // Track if this is the first message (for title generation)
    const isFirstMessage = state.messages.length === 1;

    // Helper to save accumulated tools to messages, sorted by insertion order
    const saveAccumulatedTools = (chatId: string) => {
      const s = getChatState(chatId);
      if (s.streamingTools.length > 0) {
        const sortedTools = [...s.streamingTools].sort((a, b) => 
          (a._insertionOrder ?? 0) - (b._insertionOrder ?? 0)
        );
        updateChatState(chatId, {
          messages: [...s.messages, {
            role: 'assistant',
            content: '',
            timestamp: new Date().toISOString(),
            toolCalls: sortedTools,
          }],
          streamingTools: [],
        });
      }
    };

    // Generate title for first message (fire and forget - backend creates chat on stream request)
    if (isFirstMessage) {
      setIsCreatingChat(true);
      // Small delay to ensure stream request reaches backend first and creates the chat
      setTimeout(() => {
        chatApi.generateTitle(targetChatId, trimmedContent)
          .then((response) => {
            setIsCreatingChat(false);
            // Update sidebar directly with the new title instead of full refresh
            chatHistorySidebarRef.current?.updateChatTitle(targetChatId, response.title, response.icon);
          })
          .catch(err => {
            console.error('Error generating chat title:', err);
            setIsCreatingChat(false);
            // On error, still refresh to show the chat (with default title)
            setChatHistoryRefresh(prev => prev + 1);
          });
      }, 100);
    }

    try {
      const stream = chatApi.sendMessageStream(trimmedContent, userId, targetChatId, {
        // ═══════════════════════════════════════════════════════════════════════════
        // MESSAGE STREAMING DESIGN (Foolproof Architecture)
        // ═══════════════════════════════════════════════════════════════════════════
        // 
        // PRINCIPLE: Once text is shown to the user, it must NEVER disappear.
        // Text can be saved by message_end OR by tool handlers (whichever comes first).
        //
        // Event Flow:
        // 1. message_delta → accumulate to streamingText (display only)
        // 2. tool_call_start/streaming → if streamingText exists, SAVE it first, then add tool
        // 3. tool_call_complete → update tool status
        // 4. message_end → SAVE text if not already saved, clear streamingText
        // 5. tools_end → (no-op, tools saved on done)
        // 6. done → save any remaining tools, cleanup
        //
        // Key Invariants:
        // - Text shown to user is IMMEDIATELY saved when a tool starts (prevents visual loss)
        // - message_end checks if text was already saved to avoid duplicates
        // - streamingText is always cleared after text is saved
        // ═══════════════════════════════════════════════════════════════════════════
        
        onMessageDelta: (event) => {
          const s = getChatState(targetChatId);
          
          // If text is starting and there are accumulated tools, save tools to messages first
          // This locks in the tools' position above the incoming text
          if (!s.streamingText && s.streamingTools.length > 0) {
            const sortedTools = [...s.streamingTools].sort((a, b) => 
              (a._insertionOrder ?? 0) - (b._insertionOrder ?? 0)
            );
            updateChatState(targetChatId, {
              messages: [...s.messages, {
                role: 'assistant',
                content: '',
                timestamp: new Date().toISOString(),
                toolCalls: sortedTools,
              }],
              streamingTools: [],
              streamingText: event.delta,
            });
            return;
          }
          
          // Simply accumulate text for display - message_end will save it
          updateChatState(targetChatId, {
            streamingText: s.streamingText + event.delta,
          });
        },
        
        onMessageEnd: (event) => {
          // ═══════════════════════════════════════════════════════════════════════
          // message_end is the AUTHORITATIVE signal for saving text to messages
          // However, tool handlers may have already saved the text (to prevent visual loss)
          // So we check if the text was already saved to avoid duplicates
          // ═══════════════════════════════════════════════════════════════════════
          const s = getChatState(targetChatId);
          const hasToolCalls = event.tool_calls && event.tool_calls.length > 0;
          
          // Check if this text was already saved by a tool handler
          const textAlreadySaved = event.content?.trim() && s.messages.some(msg => 
            msg.role === 'assistant' && msg.content.trim() === event.content?.trim()
          );
          
          if (textAlreadySaved) {
            // Text was already saved by tool handler, just clear the display buffer
            updateChatState(targetChatId, { streamingText: '' });
            return;
          }
          
          if (hasToolCalls) {
            // Text followed by tools: save text now, tools will be added via tool_call_start
            // The text in event.content is what we streamed - save it as a message
            if (event.content?.trim()) {
              updateChatState(targetChatId, {
                messages: [...s.messages, {
                  role: 'assistant',
                  content: event.content,
                  timestamp: event.timestamp,
                }],
                streamingText: '',  // Clear display buffer
              });
            } else {
              // No text content, just clear the buffer
              updateChatState(targetChatId, { streamingText: '' });
            }
          } else {
            // Final text response (no tools following): save text
            if (event.content?.trim()) {
              updateChatState(targetChatId, {
                messages: [...s.messages, {
                  role: 'assistant',
                  content: event.content,
                  timestamp: event.timestamp,
                }],
                streamingText: '',
              });
            } else {
              updateChatState(targetChatId, { streamingText: '' });
            }
          }
        },
        
        onToolCallStart: (event: SSEToolCallStartEvent) => {
          const s = getChatState(targetChatId);
          const isNewTool = !s.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
          
          // Create or update tool
          const newTool: ToolCallStatus = {
            tool_call_id: event.tool_call_id,
            tool_name: event.tool_name,
            status: 'calling',
            statusMessage: event.user_description || event.tool_name,
            arguments: event.arguments,
            agent_id: event.agent_id,
            parent_agent_id: event.parent_agent_id,
          };
          
          // If there's pending streaming text and this is a new tool, save text to messages first
          // This ensures text that was shown to the user is never lost/hidden
          // (message_end may have already saved it, but we need to handle race conditions)
          if (isNewTool && s.streamingText.trim()) {
            // Check if message_end already saved this text (look for a message with matching content)
            const textAlreadySaved = s.messages.some(msg => 
              msg.role === 'assistant' && msg.content === s.streamingText.trim()
            );
            
            if (!textAlreadySaved) {
              // Save the text now to prevent it from disappearing
              updateChatState(targetChatId, {
                messages: [...s.messages, {
                  role: 'assistant',
                  content: s.streamingText,
                  timestamp: new Date().toISOString(),
                }],
                streamingText: '',
                streamingTools: addOrUpdateTool(targetChatId, newTool),
              });
              return;
            } else {
              // Text was already saved by message_end, just clear the display buffer
              updateChatState(targetChatId, {
                streamingText: '',
                streamingTools: addOrUpdateTool(targetChatId, newTool),
              });
              return;
            }
          }
          
          updateChatState(targetChatId, {
            streamingTools: addOrUpdateTool(targetChatId, newTool),
          });
        },
        
        onToolCallComplete: (event: SSEToolCallCompleteEvent) => {
          const s = getChatState(targetChatId);
          const existingTool = s.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
          
          // Also check if tool was already saved to messages (happens when text starts streaming)
          // This is important for long-running tools like delegate_execution
          const toolInMessages = !existingTool && s.messages.some(msg => 
            msg.toolCalls?.some(t => t.tool_call_id === event.tool_call_id)
          );
          
          if (toolInMessages) {
            // Update the tool status in messages
            const updatedMessages = s.messages.map(msg => {
              if (!msg.toolCalls) return msg;
              const hasThisTool = msg.toolCalls.some(t => t.tool_call_id === event.tool_call_id);
              if (!hasThisTool) return msg;
              
              return {
                ...msg,
                toolCalls: msg.toolCalls.map(t => {
                  if (t.tool_call_id !== event.tool_call_id) return t;
                  return {
                    ...t,
                    status: event.status,
                    error: event.error,
                    result_summary: event.result_summary || t.result_summary,
                    code_output: event.code_output || t.code_output,
                    search_results: event.search_results || t.search_results,
                    scraped_content: event.scraped_content || t.scraped_content,
                    agent_id: event.agent_id,
                    parent_agent_id: event.parent_agent_id,
                  };
                })
              };
            });
            
            updateChatState(targetChatId, { messages: updatedMessages });
            return;
          }
          
          // Preserve streamed output if we have it
          const hasStreamedOutput = existingTool?.code_output && 
            (existingTool.code_output.stdout || existingTool.code_output.stderr);
          
          const completedTool: ToolCallStatus = {
            ...existingTool,
            tool_call_id: event.tool_call_id,
            tool_name: event.tool_name,
            status: event.status,
            error: event.error,
            result_summary: event.result_summary,
            code_output: hasStreamedOutput ? existingTool!.code_output : event.code_output,
            search_results: event.search_results,
            scraped_content: event.scraped_content,
            agent_id: event.agent_id,
            parent_agent_id: event.parent_agent_id,
          };
          
          updateChatState(targetChatId, {
            streamingTools: addOrUpdateTool(targetChatId, completedTool),
          });
        },
        
        onCodeOutput: (event) => {
          const s = getChatState(targetChatId);
          const executeCodeTools = s.streamingTools.filter(
            t => t.tool_name === 'execute_code' && t.status === 'calling'
          );
          if (executeCodeTools.length === 0) return;
          
          const latestTool = executeCodeTools[executeCodeTools.length - 1];
          const currentOutput = latestTool.code_output || { stdout: '', stderr: '' };
          
          updateChatState(targetChatId, {
            streamingTools: s.streamingTools.map(t => 
              t.tool_call_id === latestTool.tool_call_id
                ? {
                    ...t,
                    code_output: {
                      stdout: event.stream === 'stdout' 
                        ? (currentOutput.stdout || '') + event.content + '\n'
                        : currentOutput.stdout,
                      stderr: event.stream === 'stderr'
                        ? (currentOutput.stderr || '') + event.content + '\n'
                        : currentOutput.stderr
                    }
                  }
                : t
            ),
          });
        },
        
        onFileContent: (event: SSEFileContentEvent) => {
          const s = getChatState(targetChatId);
          const tool = s.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
          if (!tool) return;
          
          const currentContent = tool.file_content?.content || '';
          const newContent = event.is_complete 
            ? currentContent
            : (event.content ? currentContent + event.content : currentContent);
          
          updateChatState(targetChatId, {
            streamingTools: s.streamingTools.map(t => 
              t.tool_call_id === event.tool_call_id
                ? {
                    ...t,
                    file_content: {
                      filename: event.filename,
                      content: newContent,
                      file_type: event.file_type,
                      is_complete: event.is_complete
                    }
                  }
                : t
            ),
          });
        },
        
        onToolCallStreaming: (event: SSEToolCallStreamingEvent) => {
          // Handle streaming file content during LLM generation (before tool_call_start)
          if (!event.file_content_delta) return;
          
          const s = getChatState(targetChatId);
          const existingTool = s.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
          const currentContent = existingTool?.file_content?.content || '';
          
          const toolWithContent: ToolCallStatus = {
            tool_call_id: event.tool_call_id,
            tool_name: event.tool_name,
            status: 'calling',
            statusMessage: existingTool?.statusMessage || `Writing ${event.filename || 'file'}...`,
            file_content: {
              filename: event.filename || existingTool?.file_content?.filename || 'unknown',
              content: currentContent + event.file_content_delta,
              file_type: getFileType(event.filename || ''),
              is_complete: false
            },
            ...(existingTool && {
              arguments: existingTool.arguments,
              agent_id: existingTool.agent_id,
              parent_agent_id: existingTool.parent_agent_id,
              _insertionOrder: existingTool._insertionOrder,
            }),
          };
          
          // If there's pending streaming text and this is a new tool, save text to messages first
          // This ensures text that was shown to the user is never lost/hidden
          if (!existingTool && s.streamingText.trim()) {
            // Check if message_end already saved this text
            const textAlreadySaved = s.messages.some(msg => 
              msg.role === 'assistant' && msg.content === s.streamingText.trim()
            );
            
            if (!textAlreadySaved) {
              // Save the text now to prevent it from disappearing
              updateChatState(targetChatId, {
                messages: [...s.messages, {
                  role: 'assistant',
                  content: s.streamingText,
                  timestamp: new Date().toISOString(),
                }],
                streamingText: '',
                streamingTools: addOrUpdateTool(targetChatId, toolWithContent),
              });
              return;
            } else {
              // Text was already saved, just clear the display buffer
              updateChatState(targetChatId, {
                streamingText: '',
                streamingTools: addOrUpdateTool(targetChatId, toolWithContent),
              });
              return;
            }
          }
          
          updateChatState(targetChatId, {
            streamingTools: addOrUpdateTool(targetChatId, toolWithContent),
          });
        },
        
        onToolsEnd: () => {
          // No-op: tools are saved on done to ensure all are collected
        },
        
        onOptions: (event: SSEOptionsEvent) => {
          updateChatState(targetChatId, { pendingOptions: event });
        },
        
        onDelegationStart: () => {},
        
        onDelegationEnd: () => {},
        
        onDone: async () => {
          saveAccumulatedTools(targetChatId);
          
          try {
            // Fetch resources and chat files in parallel
            const [chatResources, chatFilesResponse] = await Promise.all([
              resourcesApi.getChatResources(targetChatId),
              fetch(`${getApiBaseUrl()}/api/chat-files/${targetChatId}`)
                .then(r => r.ok ? r.json() : [])
                .catch(() => [])
            ]);
            
            updateChatState(targetChatId, {
              isLoading: false,
              stream: null,
              resources: chatResources,
              chatFiles: chatFilesResponse,
            });
          } catch (err) {
            console.error('Error reloading resources:', err);
            updateChatState(targetChatId, {
              isLoading: false,
              stream: null,
            });
          }
          
          setChatHistoryRefresh(prev => prev + 1);
        },
        
        onError: (event) => {
          console.error('SSE error:', event.error);
          updateChatState(targetChatId, {
            error: event.error,
            isLoading: false,
            stream: null,
          });
        },
      }, attachedImages);
      
      // Store stream reference
      updateChatState(targetChatId, { stream });
    } catch (err) {
      // Network error - message wasn't sent to backend
      // Remove optimistically added user message and show error
      const state = getChatState(targetChatId);
      const messagesWithoutLast = state.messages.slice(0, -1);
      updateChatState(targetChatId, {
        messages: messagesWithoutLast,
        error: 'Failed to send message',
        isLoading: false,
        stream: null,
      });
      setMessages(messagesWithoutLast);
      setIsLoading(false);
      setError('Failed to send message');
    }
  };

  const handleStopStream = () => {
    if (currentChatId) {
      stopChatStream(currentChatId, true);
    }
  };

  const handleExportPdf = async () => {
    if (!currentChatId || isExporting || messages.length === 0) return;
    
    setIsExporting(true);
    try {
      // Create a new window with formatted content for printing
      const printWindow = window.open('', '_blank');
      if (!printWindow) {
        throw new Error('Could not open print window. Please allow popups.');
      }
      
      const htmlContent = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>Chat Export</title>
          <style>
            @media print {
              body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            }
            body {
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
              line-height: 1.6;
              color: #1f2937;
              max-width: 800px;
              margin: 0 auto;
              padding: 40px;
              background: white;
            }
            .header {
              text-align: center;
              margin-bottom: 30px;
              padding-bottom: 20px;
              border-bottom: 2px solid #e5e7eb;
            }
            .header h1 {
              font-size: 24px;
              color: #111827;
              margin: 0 0 8px 0;
            }
            .header .date {
              font-size: 14px;
              color: #6b7280;
            }
            .message {
              margin-bottom: 24px;
            }
            .message-label {
              font-size: 12px;
              font-weight: 600;
              margin-bottom: 6px;
            }
            .message-label.user { color: #7c3aed; }
            .message-label.assistant { color: #059669; }
            .message-content {
              font-size: 14px;
              line-height: 1.7;
            }
            .message-content.user {
              background: #f3f4f6;
              padding: 12px 16px;
              border-radius: 8px;
            }
            .message-content p { margin: 0 0 12px 0; }
            .message-content p:last-child { margin-bottom: 0; }
            .file-ref {
              color: #2563eb;
              background: #eff6ff;
              padding: 2px 6px;
              border-radius: 4px;
              font-size: 13px;
            }
            .tool-call {
              display: inline-block;
              background: #ecfdf5;
              color: #166534;
              padding: 4px 10px;
              border-radius: 6px;
              font-size: 12px;
              margin: 2px 4px 2px 0;
            }
            .footer {
              margin-top: 40px;
              padding-top: 20px;
              border-top: 1px solid #e5e7eb;
              text-align: center;
              font-size: 12px;
              color: #9ca3af;
            }
            code {
              background: #f3f4f6;
              padding: 2px 6px;
              border-radius: 4px;
              font-family: 'SF Mono', Monaco, monospace;
              font-size: 13px;
            }
            pre {
              background: #1f2937;
              color: #e5e7eb;
              padding: 16px;
              border-radius: 8px;
              overflow-x: auto;
              font-size: 13px;
            }
            pre code {
              background: none;
              padding: 0;
              color: inherit;
            }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>Chat Export</h1>
            <div class="date">${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
          </div>
          
          ${messages.map(msg => {
            // Process content - handle markdown-like formatting
            let content = msg.content
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/\[file:([^\]]+)\]/g, '<span class="file-ref">📎 $1</span>')
              .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
              .replace(/`([^`]+)`/g, '<code>$1</code>')
              .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
              .replace(/\n\n/g, '</p><p>')
              .replace(/\n/g, '<br/>');
            
            if (!content.startsWith('<p>') && !content.startsWith('<pre>')) {
              content = '<p>' + content + '</p>';
            }
            
            // Tool calls
            const toolCallsHtml = msg.toolCalls?.map(tc => 
              `<span class="tool-call">🔧 ${tc.statusMessage || tc.tool_name}</span>`
            ).join('') || '';
            
            return `
              <div class="message">
                <div class="message-label ${msg.role}">${msg.role === 'user' ? 'You' : 'Assistant'}</div>
                ${toolCallsHtml ? `<div style="margin-bottom: 8px;">${toolCallsHtml}</div>` : ''}
                <div class="message-content ${msg.role}">${content}</div>
              </div>
            `;
          }).join('')}
          
          <div class="footer">
            Exported from Finch • ${new Date().toLocaleDateString()}
          </div>
          
          <script>
            window.onload = function() {
              window.print();
            }
          </script>
        </body>
        </html>
      `;
      
      printWindow.document.write(htmlContent);
      printWindow.document.close();
      
    } catch (err) {
      console.error('Error exporting chat:', err);
      setError('Failed to export chat as PDF');
    } finally {
      setIsExporting(false);
    }
  };

  const handleOptionSelect = async (option: OptionButton) => {
    if (currentChatId) {
      updateChatState(currentChatId, { pendingOptions: null });
    }
    await handleSendMessage(option.value);
  };

  const handleSelectChat = async (selectedChatId: string) => {
    if (selectedChatId === currentChatId) return;
    
    setCurrentChatId(selectedChatId);
    setIsNewChat(false);
    setSelectedTool(null);
    
    // Sync display to the selected chat's state
    syncDisplayToChat(selectedChatId);
  };

  const handleNewChat = async () => {
    if (!userId) return;
    
    setCurrentChatId(null);
    setIsNewChat(true);
    setSelectedTool(null);
    
    // Clear display state for new chat
    syncDisplayToChat(null);
  };

  const handleSelectTool = async (tool: ToolCallStatus) => {
    console.log('🖱️ handleSelectTool called:', {
      tool_name: tool.tool_name,
      arguments: tool.arguments,
      resources_count: resources.length,
      has_file_content: !!tool.file_content,
      has_code_output: !!tool.code_output,
      has_search_results: !!tool.search_results,
      has_scraped_content: !!tool.scraped_content
    });
    
    const isCodeTool = tool.tool_name === 'execute_code' || tool.tool_name === 'run_python';
    const isFileTool = ['write_chat_file', 'read_chat_file', 'replace_in_chat_file'].includes(tool.tool_name);
    const isSearchTool = tool.tool_name === 'web_search' || tool.tool_name === 'news_search';
    const isScrapeTool = tool.tool_name === 'scrape_url';
    
    // If clicking on the same tool, don't toggle - just keep it open
    // User can close via the X button on the panel
    if (selectedTool?.tool_call_id === tool.tool_call_id) {
      return;
    }
    
    // Handle scrape tool
    if (isScrapeTool) {
      // If already has scraped content, just show it
      if (tool.scraped_content) {
        setSelectedTool(tool);
        return;
      }
      
      // Create placeholder while scraping or if no content
      const url = tool.arguments?.url || 'Unknown URL';
      const toolWithPlaceholder: ToolCallStatus = {
        ...tool,
        scraped_content: {
          url,
          title: '',
          content: '',
          is_complete: tool.status === 'completed'
        }
      };
      setSelectedTool(toolWithPlaceholder);
      return;
    }
    
    // Handle search tools
    if (isSearchTool) {
      // If already has search results, just show them
      if (tool.search_results) {
        setSelectedTool(tool);
        return;
      }
      
      // Create placeholder while searching or if no results
      const query = tool.arguments?.query || 'Unknown query';
      const toolWithPlaceholder: ToolCallStatus = {
        ...tool,
        search_results: {
          query,
          results: [],
          is_complete: tool.status === 'completed'
        }
      };
      setSelectedTool(toolWithPlaceholder);
      return;
    }
    
    if (isFileTool) {
      if (tool.file_content) {
        setSelectedTool(tool);
        return;
      }
      
      const filename = tool.arguments?.filename || tool.arguments?.params?.filename;
      console.log('📁 File tool clicked, looking for filename:', filename);
      
      if (filename && currentChatId) {
        try {
          const response = await fetch(`${getApiBaseUrl()}/api/chat-files/${currentChatId}/download/${encodeURIComponent(filename)}`);
          
          if (response.ok) {
            const fileType = filename.split('.').pop()?.toLowerCase() || 'text';
            const isImageFile = /\.(png|jpg|jpeg|gif|webp)$/i.test(filename);
            
            let content: string;
            if (isImageFile) {
              // For binary images, fetch as blob and convert to base64
              const blob = await response.blob();
              content = await new Promise<string>((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => {
                  const base64 = reader.result as string;
                  // Extract just the base64 data (remove data URL prefix)
                  const base64Data = base64.split(',')[1] || base64;
                  resolve(base64Data);
                };
                reader.onerror = reject;
                reader.readAsDataURL(blob);
              });
            } else {
              content = await response.text();
            }
            
            const toolWithContent: ToolCallStatus = {
              ...tool,
              file_content: {
                filename,
                content,
                file_type: fileType,
                is_complete: true
              }
            };
            setSelectedTool(toolWithContent);
          } else {
            const toolWithError: ToolCallStatus = {
              ...tool,
              file_content: {
                filename,
                content: `File "${filename}" not found or could not be loaded.`,
                file_type: 'text',
                is_complete: true
              }
            };
            setSelectedTool(toolWithError);
          }
        } catch (err) {
          console.error('Error fetching file:', err);
          const toolWithError: ToolCallStatus = {
            ...tool,
            file_content: {
              filename: filename || 'unknown',
              content: `Error loading file: ${err}`,
              file_type: 'text',
              is_complete: true
            }
          };
          setSelectedTool(toolWithError);
        }
      } else {
        const toolWithError: ToolCallStatus = {
          ...tool,
          file_content: {
            filename: 'unknown',
            content: 'Could not determine filename from tool call.',
            file_type: 'text',
            is_complete: true
          }
        };
        setSelectedTool(toolWithError);
      }
    } else if (isCodeTool) {
      const hasOutput = tool.code_output?.stdout || tool.code_output?.stderr || tool.error || tool.result_summary;
      if (hasOutput) {
        setSelectedTool(tool);
      } else {
        // No output - could be from an old session before we started persisting output,
        // or the code simply didn't produce any output
        const toolWithPlaceholder: ToolCallStatus = {
          ...tool,
          code_output: {
            stdout: '(No output recorded)',
            stderr: ''
          }
        };
        setSelectedTool(toolWithPlaceholder);
      }
    } else if (tool.tool_name === 'delegate_execution') {
      // Task Executor - show the result summary
      const summary = tool.result_summary || tool.statusMessage || 'Task execution in progress...';
      const toolWithOutput: ToolCallStatus = {
        ...tool,
        code_output: {
          stdout: summary,
          stderr: tool.error || ''
        }
      };
      setSelectedTool(toolWithOutput);
    } else {
      // Generic tool - show result_summary if available
      if (tool.result_summary || tool.error) {
        const toolWithOutput: ToolCallStatus = {
          ...tool,
          code_output: {
            stdout: tool.result_summary || '',
            stderr: tool.error || ''
          }
        };
        setSelectedTool(toolWithOutput);
      }
    }
  };

  const getPlaceholder = () => {
    if (mode.type === 'general') return 'Ask me anything about investing...';
    return `Ask about ${mode.type}...`;
  };

  // Handle when FileTree loads files - cache them at chat level
  const handleFilesLoaded = useCallback((files: FileItem[]) => {
    if (currentChatId) {
      updateChatState(currentChatId, { chatFiles: files });
    }
  }, [currentChatId, updateChatState]);

  if (!userId) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-500">Please sign in to use the chat.</p>
      </div>
    );
  }

  const showComputerPanel = selectedTool !== null;

  return (
    <div className="flex h-full bg-white">
      <ChatHistorySidebar
        ref={chatHistorySidebarRef}
        userId={userId}
        currentChatId={currentChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        isCollapsed={isSidebarCollapsed}
        onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        refreshTrigger={chatHistoryRefresh}
        isCreatingChat={isCreatingChat}
      />

      <div className={`flex-1 flex flex-col relative min-w-0 overflow-hidden transition-all duration-300 ${
        showComputerPanel 
          ? selectedTool?.file_content 
            ? 'mr-0 md:mr-[650px]'  // File view with tree - hide on mobile
            : 'mr-0 md:mr-[520px]'  // Terminal/search - hide on mobile
          : ''
      }`}>
        <ChatModeBanner />

        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className={`py-3 sm:py-4 ${showComputerPanel ? 'px-3 sm:px-6' : 'max-w-5xl mx-auto w-full px-3 sm:px-6'}`}>
            {!currentChatId && !isNewChat && !isLoading && messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex space-x-2">
                  <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" />
                  <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
              </div>
            ) : messages.length === 0 && !isLoading ? (
              <NewChatWelcome 
                onSendMessage={handleSendMessage}
                disabled={isLoading || isConnecting}
              />
            ) : (
              <>
                {messages.map((msg, i) => {
                  // Find the last assistant message index
                  const lastAssistantIdx = messages.reduce((lastIdx, m, idx) => 
                    m.role === 'assistant' ? idx : lastIdx, -1
                  );
                  const isLastAssistant = msg.role === 'assistant' && i === lastAssistantIdx && !isLoading && !streamingText && streamingTools.length === 0;
                  
                  // Actions for the last assistant message
                  const messageActions = isLastAssistant && currentChatId ? [
                    {
                      icon: (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      ),
                      label: 'Copy',
                      onClick: () => navigator.clipboard.writeText(msg.content),
                    },
                    {
                      icon: (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                      ),
                      label: 'Download PDF',
                      onClick: handleExportPdf,
                      disabled: isExporting,
                      loading: isExporting,
                    },
                  ] : undefined;
                  
                  return (
                    <ChatMessage
                      key={i}
                      role={msg.role}
                      content={msg.content}
                      toolCalls={msg.toolCalls}
                      chatId={currentChatId || undefined}
                      onSelectTool={handleSelectTool}
                      resources={resources}
                      onFileClick={(resource) => setSelectedResource(resource)}
                      actions={messageActions}
                      isLastAssistantMessage={isLastAssistant}
                    />
                  );
                })}

                {streamingTools.length > 0 && (
                  <ChatMessage 
                    role="assistant" 
                    content="" 
                    toolCalls={streamingTools} 
                    chatId={currentChatId || undefined}
                    onSelectTool={handleSelectTool}
                    resources={resources}
                    onFileClick={(resource) => setSelectedResource(resource)}
                  />
                )}

                {streamingText && (
                  <ChatMessage 
                    role="assistant" 
                    content={streamingText} 
                    chatId={currentChatId || undefined}
                    resources={resources}
                    onFileClick={(resource) => setSelectedResource(resource)}
                  />
                )}

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
              
              {/* Extra space at end of chat for better readability */}
              <div className="h-32" />
            </>
          )}
          </div>
        </div>

        {error && (
          <div className={`py-3 bg-red-50 border-t border-red-200 ${showComputerPanel ? 'px-3 sm:px-6' : 'max-w-5xl mx-auto w-full px-3 sm:px-6'}`}>
            <p className="text-xs sm:text-sm text-red-600">{formatErrorForUser(error)}</p>
          </div>
        )}

        {messages.length > 0 && (
          <div className="border-t border-gray-200 bg-white">
            <div className="max-w-4xl mx-auto">
              <ChatInput 
                onSendMessage={handleSendMessage}
                onStop={handleStopStream}
                disabled={isConnecting || !!pendingOptions}
                isStreaming={isLoading}
                placeholder={getPlaceholder()}
              />
            </div>
          </div>
        )}
      </div>

      {showComputerPanel && selectedTool && (
        <div className={`fixed right-0 top-0 h-full z-40 ${
          selectedTool.file_content 
            ? 'w-full md:w-[650px]'  // File view with tree - full width on mobile
            : 'w-full md:w-[520px]'  // Terminal/search/scrape - full width on mobile
        }`}>
          <ComputerPanel
            mode={
              selectedTool.search_results ? 'search' :
              selectedTool.scraped_content ? 'scrape' :
              selectedTool.file_content ? 'file' : 
              'terminal'
            }
            command={selectedTool.tool_name.replace(/_/g, ' ')}
            output={
              selectedTool.code_output?.stdout || 
              selectedTool.code_output?.stderr ||
              selectedTool.result_summary ||
              selectedTool.error ||
              ''
            }
            isError={selectedTool.status === 'error' || !!selectedTool.error || !!selectedTool.code_output?.stderr}
            filename={selectedTool.file_content?.filename}
            fileContent={selectedTool.file_content?.content}
            fileType={selectedTool.file_content?.file_type}
            chatId={currentChatId || undefined}
            cachedFiles={chatFiles}
            onFilesLoaded={handleFilesLoaded}
            isEditOperation={selectedTool.tool_name === 'replace_in_chat_file'}
            oldStr={selectedTool.arguments?.old_str}
            newStr={selectedTool.arguments?.new_str}
            onFileSelect={async (filename) => {
              // Load the selected file content
              if (!currentChatId) return;
              try {
                const response = await fetch(`${getApiBaseUrl()}/api/chat-files/${currentChatId}/download/${encodeURIComponent(filename)}`);
                
                if (response.ok) {
                  const fileType = filename.split('.').pop()?.toLowerCase() || 'text';
                  const isImageFile = /\.(png|jpg|jpeg|gif|webp)$/i.test(filename);
                  
                  let content: string;
                  if (isImageFile) {
                    const blob = await response.blob();
                    content = await new Promise<string>((resolve, reject) => {
                      const reader = new FileReader();
                      reader.onloadend = () => {
                        const base64 = reader.result as string;
                        const base64Data = base64.split(',')[1] || base64;
                        resolve(base64Data);
                      };
                      reader.onerror = reject;
                      reader.readAsDataURL(blob);
                    });
                  } else {
                    content = await response.text();
                  }
                  
                  // Update selectedTool with new file content
                  setSelectedTool({
                    ...selectedTool,
                    file_content: {
                      filename,
                      content,
                      file_type: fileType,
                      is_complete: true
                    }
                  });
                }
              } catch (err) {
                console.error('Error loading file:', err);
              }
            }}
            searchResults={selectedTool.search_results}
            scrapedContent={selectedTool.scraped_content}
            isStreaming={selectedTool.status === 'calling'}
            onClose={() => setSelectedTool(null)}
          />
        </div>
      )}
      
      <ResourceViewer
        resource={selectedResource}
        isOpen={!!selectedResource}
        onClose={() => setSelectedResource(null)}
      />

      {/* Debug panel - only visible when NEXT_PUBLIC_DEBUG_MODE=true */}
      <ChatDebugPanel
        messages={messages}
        streamingText={streamingText}
        streamingTools={streamingTools}
        isLoading={isLoading}
        chatId={currentChatId}
      />
    </div>
  );
}
