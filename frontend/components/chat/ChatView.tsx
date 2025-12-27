'use client';

import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from '../ChatMessage';
import ChatInput from '../ChatInput';
import ChatModeBanner from './ChatModeBanner';
import ChatHistorySidebar from './ChatHistorySidebar';
import ChatFilesModal from './ChatFilesModal';
import NewChatWelcome from './NewChatWelcome';
import ResourceViewer from '../ResourceViewer';
import ComputerPanel from '../ComputerPanel';
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
  SSEFileContentEvent,
  OptionButton,
  ImageAttachment,
  FileContent
} from '@/lib/api';

export default function ChatView() {
  const { user } = useAuth();
  const { mode } = useChatMode();
  
  // Core state
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatId, setChatId] = useState<string | null>(null);
  const [isNewChat, setIsNewChat] = useState(false); // True when in new chat mode (not yet in DB)
  const [isCreatingChat, setIsCreatingChat] = useState(false); // True while creating chat + generating title
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Streaming state
  const [streamingText, setStreamingText] = useState('');
  const [streamingTools, setStreamingTools] = useState<ToolCallStatus[]>([]);
  const streamingTextRef = useRef('');
  const streamingToolsRef = useRef<ToolCallStatus[]>([]);
  const activeStreamRef = useRef<{ close: () => void } | null>(null);
  const activeStreamChatIdRef = useRef<string | null>(null); // Track which chat the stream belongs to
  
  // Computer panel state (unified for both terminal and file viewing)
  const [selectedTool, setSelectedTool] = useState<ToolCallStatus | null>(null);
  
  // Other state
  const [resources, setResources] = useState<Resource[]>([]);
  const [pendingOptions, setPendingOptions] = useState<SSEOptionsEvent | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isResourcesOpen, setIsResourcesOpen] = useState(false);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [isPortfolioConnected, setIsPortfolioConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const userId = user?.id || null;

  // Auto-select streaming tool with output (code or file)
  useEffect(() => {
    // Check for streaming code tool with output
    const streamingCodeTool = streamingTools.find(
      t => t.status === 'calling' && 
      (t.tool_name === 'execute_code' || t.tool_name === 'run_python') &&
      t.code_output?.stdout
    );
    
    if (streamingCodeTool) {
      setSelectedTool(streamingCodeTool);
      return;
    }
    
    // Check for streaming file tool with content (write or edit)
    const streamingFileTool = streamingTools.find(
      t => t.status === 'calling' && 
      (t.tool_name === 'write_chat_file' || t.tool_name === 'replace_in_chat_file') &&
      t.file_content
    );
    
    if (streamingFileTool) {
      setSelectedTool(streamingFileTool);
    }
  }, [streamingTools]);

  // Update selected tool when streaming tools change (for live output)
  useEffect(() => {
    if (selectedTool) {
      const updated = streamingTools.find(t => t.tool_call_id === selectedTool.tool_call_id);
      if (updated) {
        setSelectedTool(updated);
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
          // Load the most recent chat
          setChatId(response.chats[0].chat_id);
          setIsNewChat(false);
        } else {
          // No chats exist - start in new chat mode (don't create in DB yet)
          setChatId(null);
          setIsNewChat(true);
        }
      } catch (err) {
        console.error('Error initializing chat:', err);
        // On error, start fresh with new chat mode
        setChatId(null);
        setIsNewChat(true);
      }
    };
    
    initializeChat();
  }, [userId]);

  // Load chat history (only when switching to existing chat, not when creating new)
  const skipNextHistoryLoad = useRef(false);
  
  useEffect(() => {
    const loadChatData = async () => {
      if (!chatId) return;
      
      // Skip loading history if we just created this chat (we're about to send a message)
      if (skipNextHistoryLoad.current) {
        skipNextHistoryLoad.current = false;
        return;
      }
      
      try {
        const displayData = await chatApi.getChatHistoryForDisplay(chatId);
        const loadedMessages: Message[] = displayData.messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
          toolCalls: msg.tool_calls
        }));
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

  // Stop the current stream and save partial state
  const stopCurrentStream = (savePartialResponse: boolean = false) => {
    if (activeStreamRef.current) {
      activeStreamRef.current.close();
      activeStreamRef.current = null;
    }
    
    if (savePartialResponse) {
      // Save any accumulated tools as a partial message
      const tools = streamingToolsRef.current;
      const text = streamingTextRef.current;
      
      if (tools.length > 0) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          toolCalls: tools.map(t => ({ ...t, status: t.status === 'calling' ? 'completed' : t.status })),
        }]);
      }
      
      if (text) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: text + ' [interrupted]',
          timestamp: new Date().toISOString(),
        }]);
      }
    }
    
    // Clear streaming state
    streamingTextRef.current = '';
    streamingToolsRef.current = [];
    setStreamingText('');
    setStreamingTools([]);
    setIsLoading(false);
  };

  const handleSendMessage = async (content: string, images?: ImageAttachment[]) => {
    if ((!content.trim() && (!images || images.length === 0)) || !userId) return;
    
    const trimmedContent = content.trim();
    let activeChatId = chatId;

    // If currently streaming, interrupt it
    if (isLoading && activeStreamRef.current) {
      stopCurrentStream(true);
    }

    // Handle new chat: create chat in DB, generate title, then send message
    if (isNewChat || !chatId) {
      setIsCreatingChat(true);
      try {
        // Create the chat
        const newChatId = await chatApi.createChat(userId);
        activeChatId = newChatId;
        skipNextHistoryLoad.current = true; // Don't reload empty history, we're about to add a message
        setChatId(newChatId);
        setIsNewChat(false);
        
        // Generate title immediately (don't await - let sidebar update when ready)
        chatApi.generateTitle(newChatId, trimmedContent)
          .then(() => {
            setIsCreatingChat(false);
            setChatHistoryRefresh(prev => prev + 1);
          })
          .catch(err => {
            console.error('Error generating chat title:', err);
            setIsCreatingChat(false);
            setChatHistoryRefresh(prev => prev + 1);
          });
      } catch (err) {
        console.error('Error creating chat:', err);
        setIsCreatingChat(false);
        setError('Failed to create chat');
        return;
      }
    }

    if (!activeChatId) return;

    // Show image indicator in user message display
    const displayContent = trimmedContent + (images && images.length > 0 ? ` [${images.length} image${images.length > 1 ? 's' : ''} attached]` : '');

    const userMessage: Message = {
      role: 'user',
      content: displayContent,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    
    streamingTextRef.current = '';
    streamingToolsRef.current = [];
    setStreamingText('');
    setStreamingTools([]);
    
    // Store images for API call
    const attachedImages = images;

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

    // Track which chat this stream belongs to
    activeStreamChatIdRef.current = activeChatId;
    
    // Helper to check if we're still viewing this chat
    const isCurrentChat = () => activeStreamChatIdRef.current === activeChatId;
    
    try {
      const stream = chatApi.sendMessageStream(trimmedContent, userId, activeChatId, {
        onMessageDelta: (event) => {
          streamingTextRef.current += event.delta;
          if (isCurrentChat()) {
            setStreamingText(streamingTextRef.current);
          }
        },
        
        onMessageEnd: (event) => {
          if (event.content && isCurrentChat()) {
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: event.content,
              timestamp: event.timestamp,
            }]);
          }
          streamingTextRef.current = '';
          if (isCurrentChat()) {
            setStreamingText('');
          }
        },
        
        onToolCallStart: (event: SSEToolCallStartEvent) => {
          if (streamingToolsRef.current.some(t => t.tool_call_id === event.tool_call_id)) {
            return;
          }
          const newTool: ToolCallStatus = {
            tool_call_id: event.tool_call_id,
            tool_name: event.tool_name,
            status: 'calling',
            statusMessage: event.user_description || event.tool_name,
            arguments: event.arguments,
          };
          streamingToolsRef.current = [...streamingToolsRef.current, newTool];
          if (isCurrentChat()) {
            setStreamingTools([...streamingToolsRef.current]);
          }
        },
        
        onToolCallComplete: (event: SSEToolCallCompleteEvent) => {
          streamingToolsRef.current = streamingToolsRef.current.map(t => {
            if (t.tool_call_id === event.tool_call_id) {
              const hasStreamedOutput = t.code_output && (t.code_output.stdout || t.code_output.stderr);
              return { 
                ...t, 
                status: event.status, 
                error: event.error, 
                code_output: hasStreamedOutput ? t.code_output : event.code_output 
              };
            }
            return t;
          });
          if (isCurrentChat()) {
            setStreamingTools([...streamingToolsRef.current]);
          }
        },
        
        onCodeOutput: (event) => {
          const executeCodeTools = streamingToolsRef.current.filter(t => t.tool_name === 'execute_code');
          if (executeCodeTools.length > 0) {
            const latestTool = executeCodeTools[executeCodeTools.length - 1];
            streamingToolsRef.current = streamingToolsRef.current.map(t => {
              if (t.tool_call_id === latestTool.tool_call_id) {
                const currentOutput = t.code_output || { stdout: '', stderr: '' };
                return {
                  ...t,
                  code_output: {
                    stdout: event.stream === 'stdout' 
                      ? (currentOutput.stdout || '') + event.content + '\n'
                      : currentOutput.stdout,
                    stderr: event.stream === 'stderr'
                      ? (currentOutput.stderr || '') + event.content + '\n'
                      : currentOutput.stderr
                  }
                };
              }
              return t;
            });
            if (isCurrentChat()) {
              setStreamingTools([...streamingToolsRef.current]);
            }
          }
        },
        
        onFileContent: (event: SSEFileContentEvent) => {
          // Find the tool by tool_call_id and update its file_content
          streamingToolsRef.current = streamingToolsRef.current.map(t => {
            if (t.tool_call_id === event.tool_call_id) {
              // If is_complete, keep existing content; otherwise append new content
              const currentContent = t.file_content?.content || '';
              const newContent = event.is_complete 
                ? currentContent  // Keep existing on completion signal
                : (event.content ? currentContent + event.content : currentContent);
              
              return {
                ...t,
                file_content: {
                  filename: event.filename,
                  content: newContent,
                  file_type: event.file_type,
                  is_complete: event.is_complete
                }
              };
            }
            return t;
          });
          if (isCurrentChat()) {
            setStreamingTools([...streamingToolsRef.current]);
          }
        },
        
        onToolsEnd: () => {
          if (isCurrentChat()) {
            saveAccumulatedTools();
          }
        },
        
        onOptions: (event: SSEOptionsEvent) => {
          if (isCurrentChat()) {
            setPendingOptions(event);
          }
        },
        
        onDone: async () => {
          const wasCurrentChat = isCurrentChat();
          activeStreamRef.current = null;
          activeStreamChatIdRef.current = null;
          
          if (wasCurrentChat) {
            setIsLoading(false);
            saveAccumulatedTools();
            
            try {
              const chatResources = await resourcesApi.getChatResources(activeChatId);
              setResources(chatResources);
            } catch (err) {
              console.error('Error reloading resources:', err);
            }
          }
          
          // Always refresh sidebar to show updated chat
          setChatHistoryRefresh(prev => prev + 1);
        },
        
        onError: (event) => {
          console.error('SSE error:', event.error);
          if (isCurrentChat()) {
            setError(event.error);
            setIsLoading(false);
          }
          activeStreamRef.current = null;
          activeStreamChatIdRef.current = null;
        },
      }, attachedImages);
      
      // Store stream reference for potential interruption
      activeStreamRef.current = stream;
    } catch (err) {
      setError('Failed to send message');
      activeStreamRef.current = null;
      setIsLoading(false);
    }
  };

  const handleStopStream = () => {
    stopCurrentStream(true);
  };

  const handleOptionSelect = async (option: OptionButton) => {
    setPendingOptions(null);
    await handleSendMessage(option.value);
  };

  const handleSelectChat = async (selectedChatId: string) => {
    // Don't interrupt the running stream - let it complete in the background
    // Just switch the view to the selected chat
    setChatId(selectedChatId);
    setIsNewChat(false);
    setMessages([]);
    setError(null);
    setPendingOptions(null);
    setSelectedTool(null);
    
    // Check if this chat is currently streaming
    const isSwitchingToStreamingChat = activeStreamChatIdRef.current === selectedChatId;
    
    if (isSwitchingToStreamingChat) {
      // Restore streaming state from refs
      setStreamingText(streamingTextRef.current);
      setStreamingTools([...streamingToolsRef.current]);
      setIsLoading(true);
    } else {
      // Different chat - clear streaming display
      setStreamingText('');
      setStreamingTools([]);
      streamingTextRef.current = '';
      streamingToolsRef.current = [];
      setIsLoading(false);
    }
  };

  const handleNewChat = async () => {
    if (!userId) return;
    // Don't create chat in DB yet - just enter new chat mode
    // Chat will be created when user sends their first message
    // Don't interrupt running streams - let them complete in background
    setChatId(null);
    setIsNewChat(true);
    setMessages([]);
    setError(null);
    setPendingOptions(null);
    setSelectedTool(null);
    setResources([]);
    
    // Clear streaming display (but don't clear refs - stream continues in background)
    setStreamingText('');
    setStreamingTools([]);
    setIsLoading(false);
  };

  const handleSelectTool = async (tool: ToolCallStatus) => {
    console.log('🖱️ handleSelectTool called:', {
      tool_name: tool.tool_name,
      arguments: tool.arguments,
      resources_count: resources.length,
      has_file_content: !!tool.file_content
    });
    
    const isCodeTool = tool.tool_name === 'execute_code' || tool.tool_name === 'run_python';
    const isFileTool = ['write_chat_file', 'read_chat_file', 'replace_in_chat_file'].includes(tool.tool_name);
    
    // Toggle: if clicking the same tool, close it
    if (selectedTool?.tool_call_id === tool.tool_call_id) {
      setSelectedTool(null);
      return;
    }
    
    if (isFileTool) {
      // If tool already has file content (from streaming), use it directly
      if (tool.file_content) {
        setSelectedTool(tool);
        return;
      }
      
      // Otherwise, fetch file content and add it to the tool
      const filename = tool.arguments?.filename || tool.arguments?.params?.filename;
      console.log('📁 File tool clicked, looking for filename:', filename);
      
      if (filename && chatId) {
        try {
          // Fetch file content from the API
          const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          const response = await fetch(`${API_BASE_URL}/api/chat-files/${chatId}/download/${encodeURIComponent(filename)}`);
          
          if (response.ok) {
            const content = await response.text();
            const fileType = filename.split('.').pop() || 'text';
            
            // Create a modified tool with file_content
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
            // File not found, show error in panel
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
          // Show error in panel
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
      }
    } else if (isCodeTool) {
      // For code tools, show terminal if there's any output
      const hasOutput = tool.code_output?.stdout || tool.code_output?.stderr || tool.error || tool.result_summary;
      if (hasOutput) {
        setSelectedTool(tool);
      }
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

  const showComputerPanel = selectedTool !== null;

  return (
    <div className="flex h-full bg-white">
      <ChatHistorySidebar
        userId={userId}
        currentChatId={chatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        isCollapsed={isSidebarCollapsed}
        onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        refreshTrigger={chatHistoryRefresh}
        isCreatingChat={isCreatingChat}
      />

      {/* Main content area - shrinks when computer panel is open, constrained width otherwise */}
      <div className={`flex-1 flex flex-col relative min-w-0 overflow-hidden transition-all duration-300 ${showComputerPanel ? 'mr-[620px]' : 'max-w-5xl mx-auto w-full'}`}>
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
          <div className="px-6 py-4">
            {!chatId && !isNewChat ? (
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
                    chatId={chatId || undefined}
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
                    chatId={chatId || undefined}
                    onSelectTool={handleSelectTool}
                    resources={resources}
                    onFileClick={(resource) => setSelectedResource(resource)}
                  />
                )}

                {streamingText && (
                  <ChatMessage 
                    role="assistant" 
                    content={streamingText} 
                    chatId={chatId || undefined}
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
          <div className="px-6 py-3 bg-red-50 border-t border-red-200">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Only show bottom input when there are messages */}
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

      {/* Computer Panel - fixed on right side (unified for terminal and file viewing) */}
      {showComputerPanel && selectedTool && (
        <div className="fixed right-0 top-0 h-full w-[620px] z-40">
          <ComputerPanel
            mode={selectedTool.file_content ? 'file' : 'terminal'}
            // Terminal props
            command={selectedTool.tool_name.replace(/_/g, ' ')}
            output={
              selectedTool.code_output?.stdout || 
              selectedTool.code_output?.stderr ||
              selectedTool.result_summary ||
              selectedTool.error ||
              ''
            }
            isError={selectedTool.status === 'error' || !!selectedTool.error || !!selectedTool.code_output?.stderr}
            // File props
            filename={selectedTool.file_content?.filename}
            fileContent={selectedTool.file_content?.content}
            fileType={selectedTool.file_content?.file_type}
            // Common props
            isStreaming={selectedTool.status === 'calling'}
            onClose={() => setSelectedTool(null)}
          />
        </div>
      )}
      
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
      
      <ResourceViewer
        resource={selectedResource}
        isOpen={!!selectedResource}
        onClose={() => setSelectedResource(null)}
      />
    </div>
  );
}
