'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ChatModeBanner from './ChatModeBanner';
import NewChatWelcome from './NewChatWelcome';
import FileViewer from '../FileViewer';
import ComputerPanel from '../ComputerPanel';
import AgentPeekPanel from './AgentPeekPanel';
import { useAuth } from '@/contexts/AuthContext';
import { useChatMode } from '@/contexts/ChatModeContext';
import { chatApi, snaptradeApi } from '@/lib/api';
import { getApiBaseUrl } from '@/lib/utils';
import { useChatStream, ChatStreamState } from '@/hooks/useChatStream';
import { useNotifications } from '@/hooks/useNotifications';
import type { AppSidebarRef } from '@/components/layout/AppSidebar';
import type {
  Message,
  ToolCallStatus,
  SSEOptionsEvent,
  OptionButton,
  ImageAttachment,
} from '@/lib/types';

interface ChatViewProps {
  // Injected by AppLayout to synchronize sidebar state
  externalChatId?: string | null;
  onChatIdChange?: (chatId: string | null) => void;
  onCreatingChatChange?: (creating: boolean) => void;
  onLoadingChange?: (loading: boolean) => void;
  onHistoryRefresh?: () => void;
  onSwapsReceived?: (chatId: string, swaps: import('@/lib/types').SwapData[]) => void;
  sidebarRef?: React.RefObject<AppSidebarRef>;
  prefillMessage?: string;
  prefillLabel?: string;
  onVisualizationClick?: (filename: string) => void;
  // If set, this chat is scoped to a trading bot
  botId?: string;
  rightOffset?: number;
  // Compact mode for chat drawer
  compact?: boolean;
  onPersonaChange?: (personaId: string | null) => void;
}

function formatErrorForUser(error: string): string {
  if (
    (error.includes('Expecting') && error.includes('delimiter')) ||
    error.includes('JSONDecodeError') ||
    error.match(/line \d+ column \d+/)
  ) {
    return 'Something went wrong processing the response. Please try again.';
  }
  if (error.includes('Traceback') || error.includes('File "')) {
    return 'An internal error occurred. Please try again.';
  }
  if (error.includes('Internal Server Error') || error.includes('500')) {
    return 'Server error. Please try again in a moment.';
  }
  if (error.includes('fetch') || error.includes('network') || error.includes('ECONNREFUSED')) {
    return 'Connection error. Please check your internet connection.';
  }
  return error;
}

async function loadFileContent(url: string, filename: string): Promise<string> {
  const { getAuthHeader } = await import('@/lib/api');
  const authHeader = await getAuthHeader();
  const response = await fetch(url, { headers: authHeader });
  if (!response.ok) throw new Error(`Failed to load file: ${response.status}`);

  const isImageFile = /\.(png|jpg|jpeg|gif|webp)$/i.test(filename);
  if (isImageFile) {
    const blob = await response.blob();
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result as string;
        resolve(base64.split(',')[1] || base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }
  return response.text();
}

export default function ChatView({
  externalChatId,
  onChatIdChange,
  onCreatingChatChange,
  onLoadingChange,
  onHistoryRefresh,
  onSwapsReceived,
  sidebarRef,
  prefillMessage,
  prefillLabel,
  onVisualizationClick,
  botId,
  rightOffset = 0,
  onPersonaChange,
}: ChatViewProps) {
  const { user } = useAuth();
  const { mode } = useChatMode();

  const [currentChatId, setCurrentChatIdLocal] = useState<string | null>(
    externalChatId !== undefined ? externalChatId : null
  );
  const [isNewChat, setIsNewChat] = useState(externalChatId === null);
  const [isCreatingChat, setIsCreatingChatLocal] = useState(false);

  // Display state mirrors the active chat's ChatStreamState
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState('');
  const [streamingTools, setStreamingTools] = useState<ToolCallStatus[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingOptions, setPendingOptions] = useState<SSEOptionsEvent | null>(null);
  const [streamStartTime, setStreamStartTime] = useState<number | null>(null);
  const [timeEstimate, setTimeEstimate] = useState<import('@/hooks/useChatStream').TimeEstimate | null>(null);
  const [emailRequested, setEmailRequested] = useState(false);

  // UI state
  const [selectedTool, setSelectedTool] = useState<ToolCallStatus | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [isPortfolioConnected, setIsPortfolioConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  // Active investor persona for this chat
  const [activePersonaId, setActivePersonaIdLocal] = useState<string | null>(null);
  const setActivePersonaId = useCallback((id: string | null) => {
    setActivePersonaIdLocal(id);
    onPersonaChange?.(id);
  }, [onPersonaChange]);

  // Sub-agent peek panel
  const [peekAgent, setPeekAgent] = useState<{ agentId: string; chatId: string; name: string } | null>(null);

  // Browser notifications
  const { requestPermission, sendNotification } = useNotifications();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const skipNextHistoryLoad = useRef(false);
  const currentChatIdRef = useRef<string | null>(null);
  const prevIsLoadingRef = useRef(false);

  // Sync display state from a ChatStreamState snapshot
  const syncDisplay = useCallback((state: ChatStreamState) => {
    setMessages(state.messages);
    setStreamingText(state.streamingText);
    setStreamingTools(state.streamingTools);
    setIsLoading(state.isLoading);
    setError(state.error);
    setPendingOptions(state.pendingOptions);
    setStreamStartTime(state.streamStartTime);
    setTimeEstimate(state.timeEstimate);

    // Notify parent of loading state changes
    if (state.isLoading !== prevIsLoadingRef.current) {
      // Stream just finished → send browser notification if tab is hidden
      if (prevIsLoadingRef.current && !state.isLoading) {
        sendNotification('Finch', 'Your analysis is ready');
      }
      // Stream just started → request notification permission for long tasks
      if (!prevIsLoadingRef.current && state.isLoading) {
        requestPermission();
      }
      prevIsLoadingRef.current = state.isLoading;
      onLoadingChange?.(state.isLoading);
    }
  }, [onLoadingChange, sendNotification, requestPermission]);

  const clearDisplay = useCallback(() => {
    setMessages([]);
    setStreamingText('');
    setStreamingTools([]);
    setIsLoading(false);
    setError(null);
    setPendingOptions(null);
    setStreamStartTime(null);
    setTimeEstimate(null);
  }, []);

  // Sync external chat id changes (e.g. sidebar selection)
  useEffect(() => {
    if (externalChatId !== undefined && externalChatId !== currentChatId) {
      if (externalChatId === null) {
        setCurrentChatIdLocal(null);
        setIsNewChat(true);
        clearDisplay();
      } else {
        setCurrentChatIdLocal(externalChatId);
        setIsNewChat(false);
        clearDisplay();
      }
    }
  }, [externalChatId, clearDisplay, currentChatId]);

  // Allow other panels (e.g. StrategiesPanel) to inject a prompt into chat via window event
  const handleSendMessageRef = useRef<((content: string) => void) | null>(null);
  useEffect(() => {
    const handler = (e: Event) => {
      const prompt = (e as CustomEvent<string>).detail;
      if (prompt && handleSendMessageRef.current) handleSendMessageRef.current(prompt);
    };
    window.addEventListener('chat:prompt', handler);
    return () => window.removeEventListener('chat:prompt', handler);
  }, []);
  const setCurrentChatId = useCallback((id: string | null) => {
    setCurrentChatIdLocal(id);
    onChatIdChange?.(id);
  }, [onChatIdChange]);

  const setIsCreatingChat = useCallback((creating: boolean) => {
    setIsCreatingChatLocal(creating);
    onCreatingChatChange?.(creating);
  }, [onCreatingChatChange]);

  currentChatIdRef.current = currentChatId;
  const userId = user?.id || null;

  const { getChatState, updateChatState, sendMessage, stopStream, setCurrentChatId: setStreamChatId } =
    useChatStream({
      onTitleGenerated: (chatId, title, icon) => {
        setIsCreatingChat(false);
        sidebarRef?.current?.updateChatTitle(chatId, title, icon);
      },
      onHistoryRefresh: () => onHistoryRefresh?.(),
      onSwapsReceived,
    });

  // Keep the hook's internal ref in sync when we switch chats
  useEffect(() => {
    setStreamChatId(currentChatId);
  }, [currentChatId, setStreamChatId]);

  // Update selected tool when streaming tools change
  useEffect(() => {
    if (selectedTool) {
      const updated = streamingTools.find(t => t.tool_call_id === selectedTool.tool_call_id);
      if (updated) setSelectedTool(updated);
    }
  }, [streamingTools, selectedTool?.tool_call_id]);

  // Initialize: load most recent chat or show new chat state
  // Skip when an external chat ID is provided (e.g. bot-scoped chats)
  useEffect(() => {
    if (externalChatId !== undefined) return;
    const init = async () => {
      if (!userId) return;
      try {
        const response = await chatApi.getUserChats(userId);
        if (response.chats?.length > 0) {
          setCurrentChatId(response.chats[0].chat_id);
          setIsNewChat(false);
        } else {
          setIsNewChat(true);
        }
      } catch {
        setIsNewChat(true);
      }
    };
    init();
  }, [userId]);

  // Load chat history when switching chats
  useEffect(() => {
    const load = async () => {
      if (!currentChatId) return;

      if (skipNextHistoryLoad.current) {
        skipNextHistoryLoad.current = false;
        return;
      }

      const state = getChatState(currentChatId);

      // If streaming or already loaded, just sync display
      if (state.isLoading || state.stream || state.messages.length > 0) {
        syncDisplay(state);
        return;
      }

      // Load from backend only if no messages cached
      try {
        const displayData = await chatApi.getChatHistoryForDisplay(currentChatId);

        const loadedMessages: Message[] = displayData.messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
          toolCalls: msg.tool_calls,
        }));

        updateChatState(currentChatId, { messages: loadedMessages }, syncDisplay);
      } catch {
        // Silently fail — user can retry
      }
    };
    load();
  }, [currentChatId, getChatState, syncDisplay, updateChatState]);

  // Check portfolio connection status
  useEffect(() => {
    if (!userId) return;
    snaptradeApi.checkStatus(userId)
      .then(status => setIsPortfolioConnected(status.is_connected))
      .catch(() => setIsPortfolioConnected(false));
  }, [userId]);

  // Visibility change: smart reconnection when tab becomes visible again
  useEffect(() => {
    const handleVisibilityChange = async () => {
      if (document.hidden || !currentChatId) return;

      const state = getChatState(currentChatId);
      if (!state.wasStreamingBeforeHidden) {
        syncDisplay(state);
        return;
      }

      try {
        const status = await chatApi.checkChatStatus(currentChatId);

        if (status.is_processing && state.stream) {
          state.stream.reconnect?.();
          return;
        }

        updateChatState(currentChatId, {
          streamingText: '',
          streamingTools: [],
          isLoading: status.is_processing,
          stream: null,
          wasStreamingBeforeHidden: false,
        }, syncDisplay);

        if (status.is_processing) {
          const pollInterval = setInterval(async () => {
            const current = await chatApi.checkChatStatus(currentChatId);
            if (!current.is_processing) {
              clearInterval(pollInterval);
              updateChatState(currentChatId, {
                isLoading: false,
              }, syncDisplay);
            }
          }, 2000);
        }
      } catch {
        setIsLoading(false);
        setError('Connection lost. Please refresh if messages are missing.');
        const state = getChatState(currentChatId);
        state.wasStreamingBeforeHidden = false;
      }
    };

    const handleBeforeUnload = () => {
      // Close all active streams on page unload
      if (currentChatId) {
        const state = getChatState(currentChatId);
        state.stream?.close();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [currentChatId, getChatState, updateChatState, syncDisplay]);

  const handleSendMessage = async (content: string, images?: ImageAttachment[], skills?: string[], _files?: unknown, investorPersona?: string) => {
    if ((!content.trim() && (!images || images.length === 0)) || !userId) return;

    // Track investor persona for the lifetime of this chat
    const personaToUse = investorPersona || activePersonaId;
    if (investorPersona) setActivePersonaId(investorPersona);

    setEmailRequested(false);
    const isFirst = isNewChat || !currentChatId;
    let creatingChatTimeout: NodeJS.Timeout | null = null;

    if (isFirst) {
      skipNextHistoryLoad.current = true;
      setIsNewChat(false);
      setIsCreatingChat(true);

      // Safety timeout: ensure creating state clears after 30 seconds max
      creatingChatTimeout = setTimeout(() => {
        setIsCreatingChat(false);
      }, 30000);
    }

    try {
      await sendMessage(
        content,
        userId,
        currentChatId,
        isFirst,
        images,
        syncDisplay,
        (newChatId) => {
          currentChatIdRef.current = newChatId;
          setCurrentChatId(newChatId);
        },
        skills,
        personaToUse || undefined,
      );
    } catch {
      // Errors handled inside useChatStream
    } finally {
      if (creatingChatTimeout) {
        clearTimeout(creatingChatTimeout);
      }
    }
  };

  // Keep the ref fresh so the chat:prompt window listener always calls the latest version
  handleSendMessageRef.current = (msg: string) => handleSendMessage(msg);

  const handleStopStream = () => {
    if (currentChatId) {
      stopStream(currentChatId, true, syncDisplay);
    }
  };

  const handleOptionSelect = async (option: OptionButton) => {
    if (currentChatId) {
      updateChatState(currentChatId, { pendingOptions: null }, syncDisplay);
    }
    await handleSendMessage(option.value);
  };

  const handleSelectChat = (selectedChatId: string) => {
    if (selectedChatId === currentChatId) return;
    setCurrentChatId(selectedChatId);
    setIsNewChat(false);
    setSelectedTool(null);
    setActivePersonaId(null);
    syncDisplay(getChatState(selectedChatId));
  };

  const handleNewChat = useCallback(() => {
    if (!userId) return;
    setCurrentChatId(null);
    setIsNewChat(true);
    setSelectedTool(null);
    setActivePersonaId(null);
    clearDisplay();
  }, [userId, clearDisplay, setCurrentChatId]);

  const handleSelectTool = async (tool: ToolCallStatus) => {
    if (selectedTool?.tool_call_id === tool.tool_call_id) return;

    const isFileTool = ['write_chat_file', 'read_chat_file', 'replace_in_chat_file'].includes(tool.tool_name);
    const isSearchTool = tool.tool_name === 'web_search' || tool.tool_name === 'news_search';
    const isScrapeTool = tool.tool_name === 'scrape_url';
    const isCodeTool = tool.tool_name === 'execute_code' || tool.tool_name === 'run_python' || tool.tool_name === 'bash';

    if (isScrapeTool) {
      setSelectedTool(tool.scraped_content ? tool : {
        ...tool,
        scraped_content: {
          url: tool.arguments?.url || 'Unknown URL',
          title: '',
          content: '',
          is_complete: tool.status === 'completed',
        },
      });
      return;
    }

    if (isSearchTool) {
      setSelectedTool(tool.search_results ? tool : {
        ...tool,
        search_results: {
          query: tool.arguments?.query || 'Unknown query',
          results: [],
          is_complete: tool.status === 'completed',
        },
      });
      return;
    }

    if (isFileTool) {
      if (tool.file_content) { setSelectedTool(tool); return; }

      const filename = tool.arguments?.filename || tool.arguments?.params?.filename;
      if (filename && currentChatId) {
        try {
          const url = `${getApiBaseUrl()}/api/chat-files/${currentChatId}/download/${encodeURIComponent(filename)}`;
          const content = await loadFileContent(url, filename);
          setSelectedTool({
            ...tool,
            file_content: {
              filename,
              content,
              file_type: filename.split('.').pop()?.toLowerCase() || 'text',
              is_complete: true,
            },
          });
        } catch {
          setSelectedTool({
            ...tool,
            file_content: { filename: filename || 'unknown', content: `Error loading file.`, file_type: 'text', is_complete: true },
          });
        }
      } else {
        setSelectedTool({
          ...tool,
          file_content: { filename: 'unknown', content: 'Could not determine filename.', file_type: 'text', is_complete: true },
        });
      }
      return;
    }

    if (isCodeTool) {
      const hasOutput = tool.code_output?.stdout || tool.code_output?.stderr || tool.error || tool.result_summary;
      setSelectedTool(hasOutput ? tool : {
        ...tool,
        code_output: { stdout: '(No output recorded)', stderr: '' },
      });
      return;
    }

    if (tool.result_summary || tool.error) {
      setSelectedTool({
        ...tool,
        code_output: { stdout: tool.result_summary || '', stderr: tool.error || '' },
      });
    }
  };

  const handleExportPdf = async () => {
    if (!currentChatId || isExporting || messages.length === 0) return;
    setIsExporting(true);
    try {
      const printWindow = window.open('', '_blank');
      if (!printWindow) throw new Error('Could not open print window. Please allow popups.');

      const htmlContent = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Chat Export</title>
        <style>
          @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 800px; margin: 0 auto; padding: 40px; }
          .header { text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #e5e7eb; }
          .header h1 { font-size: 24px; color: #111827; margin: 0 0 8px 0; }
          .header .date { font-size: 14px; color: #6b7280; }
          .message { margin-bottom: 24px; }
          .message-label { font-size: 12px; font-weight: 600; margin-bottom: 6px; }
          .message-label.user { color: #7c3aed; }
          .message-label.assistant { color: #059669; }
          .message-content { font-size: 14px; line-height: 1.7; }
          .message-content.user { background: #f3f4f6; padding: 12px 16px; border-radius: 8px; }
          .tool-call { display: inline-block; background: #ecfdf5; color: #166534; padding: 4px 10px; border-radius: 6px; font-size: 12px; margin: 2px 4px 2px 0; }
          .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center; font-size: 12px; color: #9ca3af; }
          code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 13px; }
          pre { background: #1f2937; color: #e5e7eb; padding: 16px; border-radius: 8px; overflow-x: auto; }
          pre code { background: none; padding: 0; color: inherit; }
        </style></head><body>
        <div class="header"><h1>Chat Export</h1>
        <div class="date">${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div></div>
        ${messages.map(msg => {
          let content = msg.content
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/\[file:([^\]]+)\]/g, '<span style="color:#2563eb;background:#eff6ff;padding:2px 6px;border-radius:4px;">📎 $1</span>')
            .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br/>');
          if (!content.startsWith('<p>') && !content.startsWith('<pre>')) content = '<p>' + content + '</p>';
          const toolCallsHtml = msg.toolCalls?.map(tc => `<span class="tool-call">🔧 ${tc.statusMessage || tc.tool_name}</span>`).join('') || '';
          return `<div class="message"><div class="message-label ${msg.role}">${msg.role === 'user' ? 'You' : 'Assistant'}</div>${toolCallsHtml ? `<div style="margin-bottom:8px">${toolCallsHtml}</div>` : ''}<div class="message-content ${msg.role}">${content}</div></div>`;
        }).join('')}
        <div class="footer">Exported from Finch &bull; ${new Date().toLocaleDateString()}</div>
        <script>window.onload = function() { window.print(); }</script></body></html>`;

      printWindow.document.write(htmlContent);
      printWindow.document.close();
    } catch {
      setError('Failed to export chat as PDF');
    } finally {
      setIsExporting(false);
    }
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

      <div
        className={`flex-1 flex flex-col relative min-w-0 overflow-hidden transition-all duration-300`}
        style={showComputerPanel ? {
          marginRight: selectedTool?.file_content
            ? `${650 + rightOffset}px`
            : `${520 + rightOffset}px`
        } : undefined}
      >
        <ChatModeBanner />

        {/* Email notification banner — appears at top during long streams */}
        {isLoading && streamStartTime && !emailRequested && currentChatId && (Date.now() - streamStartTime) > 15000 && (
          <div className="flex items-center justify-center gap-2 py-2 px-4 bg-gray-50 border-b border-gray-200 animate-in fade-in duration-300">
            <span className="text-xs text-gray-500">This is taking a while.</span>
            <button
              onClick={() => {
                setEmailRequested(true);
                chatApi.requestEmailNotification(currentChatId).catch(() => {});
              }}
              className="flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Email me when done
            </button>
          </div>
        )}
        {isLoading && emailRequested && (
          <div className="flex items-center justify-center gap-1.5 py-2 px-4 bg-green-50 border-b border-green-200 animate-in fade-in duration-300">
            <svg className="w-3.5 h-3.5 text-green-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-xs text-green-700">We'll email you when this is done</span>
          </div>
        )}

        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className={`pt-8 pb-4 ${showComputerPanel ? 'px-3 sm:px-6' : 'max-w-3xl mx-auto w-full px-4 sm:px-8'}`}>
            {!currentChatId && !isNewChat && !isLoading && messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex space-x-2">
                  {[0, 0.1, 0.2].map((delay, i) => (
                    <div key={i} className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: `${delay}s` }} />
                  ))}
                </div>
              </div>
            ) : messages.length === 0 && !isLoading ? (
              <NewChatWelcome onSendMessage={handleSendMessage} disabled={isLoading || isConnecting} prefillMessage={prefillMessage} prefillLabel={prefillLabel} />
            ) : (
              <>
                {messages.map((msg, i) => {
                  // Only show actions when fully idle — never during streaming
                  const nextIsUser = messages[i + 1]?.role === 'user';
                  const isLast = i === messages.length - 1;
                  const showActions = !isLoading && msg.role === 'assistant' && (
                    nextIsUser || isLast
                  );

                  // Collect full section text for copy
                  let groupContent = '';
                  if (showActions) {
                    for (let j = i; j >= 0 && messages[j].role === 'assistant'; j--) {
                      if (messages[j].content) groupContent = messages[j].content + (groupContent ? '\n\n' + groupContent : '');
                    }
                  }

                  const messageActions = showActions && currentChatId ? [
                    {
                      icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>,
                      label: 'Copy',
                      onClick: () => navigator.clipboard.writeText(groupContent),
                    },
                    {
                      icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" /></svg>,
                      label: 'Good response',
                      onClick: () => {},
                    },
                    {
                      icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v2a3.5 3.5 0 003.5 3.5h.174a.535.535 0 00.524-.448l.497-2.986A1.5 1.5 0 0116.18 14.5H18a2.5 2.5 0 002.5-2.5v0a2.5 2.5 0 00-.69-1.726l-3.549-3.643A2 2 0 0014.846 6H10m0 8H7.5" /></svg>,
                      label: 'Bad response',
                      onClick: () => {},
                    },
                  ] : undefined;

                  return (
                    <ChatMessage
                      key={i}
                      role={msg.role}
                      content={msg.content}
                      toolCalls={msg.toolCalls}
                      swap_data={msg.swap_data}
                      chatId={currentChatId || undefined}
                      userId={userId || undefined}
                      onSelectTool={handleSelectTool}
                      onFileClick={(filename) => setSelectedFile(filename)}
                      onVisualizationClick={onVisualizationClick}
                      onSendMessage={(text) => handleSendMessage(text)}
                      onPeekAgent={(agentId, chatId, name) => setPeekAgent({ agentId, chatId, name })}
                      actions={messageActions}
                      isLastAssistantMessage={showActions && isLast}
                    />
                  );
                })}

                {(streamingText || streamingTools.length > 0) && (
                  <ChatMessage
                    role="assistant"
                    content={streamingText}
                    toolCalls={streamingTools.length > 0 ? streamingTools : undefined}
                    chatId={currentChatId || undefined}
                    onSelectTool={handleSelectTool}
                    onFileClick={(filename) => setSelectedFile(filename)}
                    onVisualizationClick={onVisualizationClick}
                    onPeekAgent={(agentId, chatId, name) => setPeekAgent({ agentId, chatId, name })}
                    isStreaming={true}
                    startTime={streamStartTime}
                    timeEstimate={timeEstimate}
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
                      {[0, 0.1, 0.2].map((delay, i) => (
                        <div key={i} className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: `${delay}s` }} />
                      ))}
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
                <div className="h-40" />
              </>
            )}
          </div>
        </div>

        {error && (
          <div className={`py-3 bg-red-50 border-t border-red-200 ${showComputerPanel ? 'px-3 sm:px-6' : 'max-w-3xl mx-auto w-full px-4 sm:px-8'}`}>
            <p className="text-xs sm:text-sm text-red-600">{formatErrorForUser(error)}</p>
          </div>
        )}

        {messages.length > 0 && (
          <div className="absolute bottom-0 left-0 right-0 z-10">
            <div className="max-w-3xl mx-auto px-4 sm:px-8 relative z-10">
              <ChatInput
                onSendMessage={handleSendMessage}
                onStop={handleStopStream}
                disabled={isConnecting || !!pendingOptions}
                isStreaming={isLoading}
                placeholder={mode.type === 'general' ? 'Ask me anything about investing...' : `Ask about ${mode.type}...`}
                chatId={currentChatId || undefined}
              />
            </div>
            <div className="h-10 bg-white -mt-6" />
          </div>
        )}
      </div>

      {showComputerPanel && selectedTool && (
        <div
          className={`fixed top-0 h-full z-40 ${
            selectedTool.file_content ? 'w-full md:w-[650px]' : 'w-full md:w-[520px]'
          }`}
          style={{ right: rightOffset }}
        >
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
            isEditOperation={selectedTool.tool_name === 'replace_in_chat_file'}
            oldStr={selectedTool.arguments?.old_str}
            newStr={selectedTool.arguments?.new_str}
            searchResults={selectedTool.search_results}
            scrapedContent={selectedTool.scraped_content}
            isStreaming={selectedTool.status === 'detected' || selectedTool.status === 'calling'}
            onClose={() => setSelectedTool(null)}
          />
        </div>
      )}

      {/* Agent Peek Panel — slides in from right when a sub-agent card is clicked */}
      {peekAgent && (
        <div
          className="fixed top-0 right-0 h-full w-full md:w-[380px] z-50 shadow-2xl"
          style={rightOffset ? { right: rightOffset } : undefined}
        >
          <AgentPeekPanel
            agentId={peekAgent.agentId}
            chatId={peekAgent.chatId}
            agentName={peekAgent.name}
            onClose={() => setPeekAgent(null)}
          />
        </div>
      )}

      {selectedFile && (
        <div
          className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4 backdrop-blur-sm"
          onClick={() => setSelectedFile(null)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl max-w-5xl w-full flex flex-col overflow-hidden"
            style={{ maxHeight: '88vh' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-gray-50 shrink-0">
              <span className="text-sm font-medium text-gray-700 truncate">{selectedFile}</span>
              <button
                onClick={() => setSelectedFile(null)}
                className="p-1 ml-3 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 shrink-0"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-auto" style={{ maxHeight: 'calc(88vh - 48px)' }}>
              <FileViewer filename={selectedFile} chatId={currentChatId} />
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
