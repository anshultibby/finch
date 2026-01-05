'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatMessage from '../ChatMessage';
import ChatInput from '../ChatInput';
import ChatModeBanner from './ChatModeBanner';
import ChatHistorySidebar, { ChatHistorySidebarRef } from './ChatHistorySidebar';
import ChatFilesModal from './ChatFilesModal';
import NewChatWelcome from './NewChatWelcome';
import ResourceViewer from '../ResourceViewer';
import ComputerPanel from '../ComputerPanel';
import { FileItem } from '../FileTree';
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
  SSEToolCallStreamingEvent,
  SSEOptionsEvent,
  SSEFileContentEvent,
  OptionButton,
  ImageAttachment,
  FileContent
} from '@/lib/api';

// Helper to determine file type from filename
const getFileType = (filename: string): string => {
  if (filename.endsWith('.py')) return 'python';
  if (filename.endsWith('.md')) return 'markdown';
  if (filename.endsWith('.csv')) return 'csv';
  if (filename.endsWith('.json')) return 'json';
  if (filename.endsWith('.html')) return 'html';
  if (filename.endsWith('.js')) return 'javascript';
  if (filename.endsWith('.ts') || filename.endsWith('.tsx')) return 'typescript';
  if (filename.endsWith('.jsx')) return 'javascript';
  return 'text';
};

// Per-chat state stored in refs (persists across chat switches)
interface ChatStreamState {
  messages: Message[];
  streamingText: string;
  streamingTools: ToolCallStatus[];
  isLoading: boolean;
  error: string | null;
  pendingOptions: SSEOptionsEvent | null;
  resources: Resource[];
  stream: { close: () => void } | null;
  chatFiles: FileItem[]; // Cached file list for file explorer
  toolInsertionCounter: number; // Counter for assigning stable insertion order to tools
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
  const [isResourcesOpen, setIsResourcesOpen] = useState(false);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
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


  // Update selected tool when streaming tools change
  // Close panel when streaming ends (tool no longer in streamingTools)
  useEffect(() => {
    if (selectedTool) {
      const updated = streamingTools.find(t => t.tool_call_id === selectedTool.tool_call_id);
      
      if (updated) {
        setSelectedTool(updated);
      } else if (streamingTools.length === 0) {
        // Close panel when streaming ends
        setSelectedTool(null);
      }
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
      
      // If we already have messages loaded and no active stream, use cached state
      if (state.messages.length > 0) {
        syncDisplayToChat(currentChatId);
        return;
      }
      
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
        onMessageDelta: (event) => {
          const s = getChatState(targetChatId);
          
          // If text is starting and there are tools, save tools to messages first
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
          
          updateChatState(targetChatId, {
            streamingText: s.streamingText + event.delta,
          });
        },
        
        onMessageEnd: (event) => {
          const s = getChatState(targetChatId);
          
          if (event.content) {
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
        },
        
        onToolCallStart: (event: SSEToolCallStartEvent) => {
          const s = getChatState(targetChatId);
          
          // If there's streaming text and this is a NEW tool, save the text to messages first
          // but keep all tools together in streamingTools (don't split tool groups)
          const existingToolIndex = s.streamingTools.findIndex(t => t.tool_call_id === event.tool_call_id);
          if (existingToolIndex < 0 && s.streamingText.trim()) {
            // Save only the text to messages, keep tools in streamingTools
            updateChatState(targetChatId, {
              messages: [...s.messages, {
                role: 'assistant',
                content: s.streamingText,
                timestamp: new Date().toISOString(),
              }],
              streamingText: '',
            });
          }
          
          // Create or update tool - addOrUpdateTool handles both cases and maintains order
          const newTool: ToolCallStatus = {
            tool_call_id: event.tool_call_id,
            tool_name: event.tool_name,
            status: 'calling',
            statusMessage: event.user_description || event.tool_name,
            arguments: event.arguments,
            agent_id: event.agent_id,
            parent_agent_id: event.parent_agent_id,
          };
          
          updateChatState(targetChatId, {
            streamingTools: addOrUpdateTool(targetChatId, newTool),
          });
        },
        
        onToolCallComplete: (event: SSEToolCallCompleteEvent) => {
          const s = getChatState(targetChatId);
          
          // Find existing tool - we'll preserve all its fields
          const existingTool = s.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
          const hasStreamedOutput = existingTool?.code_output && 
            (existingTool.code_output.stdout || existingTool.code_output.stderr);
          
          // Spread existing tool first to preserve all fields (arguments, statusMessage, etc.)
          // Then override with completion data from the event
          const completedTool: ToolCallStatus = {
            ...existingTool,  // Preserve everything from tool_call_start
            tool_call_id: event.tool_call_id,
            tool_name: event.tool_name,
            status: event.status,
            error: event.error,
            code_output: hasStreamedOutput ? existingTool!.code_output : event.code_output,
            search_results: event.search_results,
            agent_id: event.agent_id,
            parent_agent_id: event.parent_agent_id,
          };
          
          updateChatState(targetChatId, {
            streamingTools: addOrUpdateTool(targetChatId, completedTool),
          });
        },
        
        onCodeOutput: (event) => {
          const s = getChatState(targetChatId);
          
          // Find the latest execute_code tool that's still calling
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
          
          // Find tool by ID in flat list
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
        
        // Handle streaming file content during LLM generation (before tool_call_start)
        onToolCallStreaming: (event: SSEToolCallStreamingEvent) => {
          if (!event.file_content_delta) return;
          
          const s = getChatState(targetChatId);
          
          // Check for existing tool in flat list
          const existingTool = s.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
          const currentContent = existingTool?.file_content?.content || '';
          
          // Create or update tool with file content
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
            // Preserve existing fields or set defaults (including _insertionOrder for stable ordering)
            ...(existingTool && {
              arguments: existingTool.arguments,
              agent_id: existingTool.agent_id,
              parent_agent_id: existingTool.parent_agent_id,
              _insertionOrder: existingTool._insertionOrder,
            }),
          };
          
          // If there's streaming text and this is a NEW tool, save the text to messages first
          // but keep all tools together in streamingTools (don't split tool groups)
          if (!existingTool && s.streamingText.trim()) {
            updateChatState(targetChatId, {
              messages: [...s.messages, {
                role: 'assistant',
                content: s.streamingText,
                timestamp: new Date().toISOString(),
              }],
              streamingText: '',
            });
          }
          
          updateChatState(targetChatId, {
            streamingTools: addOrUpdateTool(targetChatId, toolWithContent),
          });
        },
        
        onToolsEnd: () => {
          // Don't save tools here - wait for onDone to ensure all tools are collected
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
              fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/chat-files/${targetChatId}`)
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
      has_search_results: !!tool.search_results
    });
    
    const isCodeTool = tool.tool_name === 'execute_code' || tool.tool_name === 'run_python';
    const isFileTool = ['write_chat_file', 'read_chat_file', 'replace_in_chat_file'].includes(tool.tool_name);
    const isSearchTool = tool.tool_name === 'web_search' || tool.tool_name === 'news_search';
    
    if (selectedTool?.tool_call_id === tool.tool_call_id) {
      setSelectedTool(null);
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
          const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          const response = await fetch(`${API_BASE_URL}/api/chat-files/${currentChatId}/download/${encodeURIComponent(filename)}`);
          
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
            ? 'mr-[650px]'  // File view with tree
            : 'mr-[520px]'  // Terminal/search
          : ''
      }`}>
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

        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className={`py-4 ${showComputerPanel ? 'px-6' : 'max-w-5xl mx-auto w-full px-6'}`}>
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
                {messages.map((msg, i) => (
                  <ChatMessage
                    key={i}
                    role={msg.role}
                    content={msg.content}
                    toolCalls={msg.toolCalls}
                    chatId={currentChatId || undefined}
                    onSelectTool={handleSelectTool}
                    resources={resources}
                    onFileClick={(resource) => setSelectedResource(resource)}
                  />
                ))}

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
            </>
          )}
          </div>
        </div>

        {error && (
          <div className={`py-3 bg-red-50 border-t border-red-200 ${showComputerPanel ? 'px-6' : 'max-w-5xl mx-auto w-full px-6'}`}>
            <p className="text-sm text-red-600">{error}</p>
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
            ? 'w-[650px]'  // File view with tree
            : 'w-[520px]'  // Terminal/search
        }`}>
          <ComputerPanel
            mode={
              selectedTool.search_results ? 'search' : 
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
                const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const response = await fetch(`${API_BASE_URL}/api/chat-files/${currentChatId}/download/${encodeURIComponent(filename)}`);
                
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
            isStreaming={selectedTool.status === 'calling'}
            onClose={() => setSelectedTool(null)}
          />
        </div>
      )}
      
      {currentChatId && (
        <ChatFilesModal
          isOpen={isResourcesOpen}
          onClose={() => setIsResourcesOpen(false)}
          chatId={currentChatId}
          onSelectResource={(resource) => {
            setSelectedResource(resource);
            setIsResourcesOpen(false);
          }}
        />
      )}
      
      <ResourceViewer
        resource={selectedResource}
        isOpen={!!selectedResource}
        onClose={() => setSelectedResource(null)}
      />
    </div>
  );
}
