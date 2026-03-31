'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ChatModeBanner from './ChatModeBanner';
import NewChatWelcome from './NewChatWelcome';
import FileViewer from '../FileViewer';
import ComputerPanel from '../ComputerPanel';
import dynamic from 'next/dynamic';
const PdfCopilot = dynamic(() => import('../PdfCopilot'), { ssr: false });
import { useAuth } from '@/contexts/AuthContext';
import { useChatMode } from '@/contexts/ChatModeContext';
import { chatApi, snaptradeApi } from '@/lib/api';
import { getApiBaseUrl } from '@/lib/utils';
import { useChatStream, ChatStreamState } from '@/hooks/useChatStream';
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
  sidebarRef?: React.RefObject<AppSidebarRef>;
  prefillMessage?: string;
  // If set, this chat is scoped to a trading bot
  botId?: string;
  rightOffset?: number;
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
  const response = await fetch(url);
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
  sidebarRef,
  prefillMessage,
  botId,
  rightOffset = 0,
}: ChatViewProps) {
  const { user } = useAuth();
  const { mode } = useChatMode();

  const [currentChatId, setCurrentChatIdLocal] = useState<string | null>(null);
  const [isNewChat, setIsNewChat] = useState(false);
  const [isCreatingChat, setIsCreatingChatLocal] = useState(false);

  // Display state mirrors the active chat's ChatStreamState
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState('');
  const [streamingTools, setStreamingTools] = useState<ToolCallStatus[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingOptions, setPendingOptions] = useState<SSEOptionsEvent | null>(null);


  // Side-panel state
  const [selectedTool, setSelectedTool] = useState<ToolCallStatus | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [openPdfs, setOpenPdfs] = useState<string[]>([]); // multiple open PDFs
  const [activePdfIndex, setActivePdfIndex] = useState(0);
  const [pdfRefresh, setPdfRefresh] = useState(0);
  // 'tool' = ComputerPanel, 'pdf' = PdfCopilot. Both can coexist; activePanel picks which is visible.
  const [activePanel, setActivePanel] = useState<'tool' | 'pdf' | null>(null);
  const [panelCollapsed, setPanelCollapsed] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isPortfolioConnected, setIsPortfolioConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

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

    // Notify parent of loading state changes
    if (state.isLoading !== prevIsLoadingRef.current) {
      prevIsLoadingRef.current = state.isLoading;
      onLoadingChange?.(state.isLoading);
    }
  }, [onLoadingChange]);

  const clearDisplay = useCallback(() => {
    setMessages([]);
    setStreamingText('');
    setStreamingTools([]);
    setIsLoading(false);
    setError(null);
    setPendingOptions(null);
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
        onHistoryRefresh?.();
      },
      onHistoryRefresh: () => onHistoryRefresh?.(),
      onOpenFile: (path) => {
        if (path.toLowerCase().endsWith('.pdf')) {
          setOpenPdfs(prev => {
            const existing = prev.indexOf(path);
            if (existing >= 0) { setActivePdfIndex(existing); return prev; }
            setActivePdfIndex(prev.length);
            return [...prev, path];
          });
          setActivePanel('pdf');
          setPanelCollapsed(false);
          setPdfRefresh(n => n + 1);
        } else {
          setSelectedFile(path);
        }
      },
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

  // Refresh PDF copilot when agent fills a form via code execution
  const prevToolsRef = useRef<string>('');
  useEffect(() => {
    const key = streamingTools.map(t => `${t.tool_call_id}:${t.status}`).join(',');
    if (key === prevToolsRef.current) return;
    prevToolsRef.current = key;

    if (openPdfs.length === 0) return;
    for (const tool of streamingTools) {
      if (tool.status !== 'completed') continue;
      const isCodeTool = tool.tool_name === 'execute_code' || tool.tool_name === 'bash';
      if (!isCodeTool) continue;

      const output = tool.result_summary || '';
      const code = tool.arguments?.code || tool.arguments?.cmd || '';
      const allText = output + code;

      if (allText.includes('fill_form') || allText.includes('overlay_text')) {
        setPdfRefresh(n => n + 1);
      }
    }
  }, [streamingTools, openPdfs]);

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

  const handleSendMessage = async (content: string, images?: ImageAttachment[], skills?: string[], _files?: unknown) => {
    if ((!content.trim() && (!images || images.length === 0)) || !userId) return;

    // (Tax doc uploads don't auto-open PDF — agent will download the form first)

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
    syncDisplay(getChatState(selectedChatId));
  };

  const handleNewChat = useCallback(() => {
    if (!userId) return;
    setCurrentChatId(null);
    setIsNewChat(true);
    setSelectedTool(null);
    clearDisplay();
  }, [userId, clearDisplay, setCurrentChatId]);

  const handleSelectTool = async (tool: ToolCallStatus) => {
    if (selectedTool?.tool_call_id === tool.tool_call_id) {
      // Toggle: clicking same tool switches to tool panel if on another tab
      if (activePanel !== 'tool') setActivePanel('tool');
      return;
    }
    setActivePanel('tool');

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

  const handleFileClick = useCallback((filename: string) => {
    if (filename.toLowerCase().endsWith('.pdf')) {
      setOpenPdfs(prev => {
        const existing = prev.indexOf(filename);
        if (existing >= 0) { setActivePdfIndex(existing); return prev; }
        setActivePdfIndex(prev.length);
        return [...prev, filename];
      });
      setActivePanel('pdf');
      setPanelCollapsed(false);
    } else {
      setSelectedFile(filename);
    }
  }, []);

  if (!userId) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-500">Please sign in to use the chat.</p>
      </div>
    );
  }

  const hasTool = selectedTool !== null;
  const hasPdf = openPdfs.length > 0;
  const activePdf = openPdfs[activePdfIndex] || null;
  const effectivePanel = activePanel || (hasTool ? 'tool' : hasPdf ? 'pdf' : null);
  const hasAnyPanel = hasTool || hasPdf;
  const COLLAPSED_WIDTH = 44;
  const expandedWidth = effectivePanel === 'tool'
    ? (selectedTool?.file_content ? 650 : 520)
    : effectivePanel === 'pdf' ? 650 : 0;
  const panelWidth = !hasAnyPanel ? 0 : panelCollapsed ? COLLAPSED_WIDTH : expandedWidth;

  return (
    <div className="flex h-full bg-white">

      <div
        className={`flex-1 flex flex-col relative min-w-0 overflow-hidden transition-all duration-300`}
        style={panelWidth > 0 ? { marginRight: `${panelWidth + rightOffset}px` } : undefined}
      >
        <ChatModeBanner />

        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className={`py-3 sm:py-4 ${panelWidth > 0 ? 'px-3 sm:px-6' : 'max-w-5xl mx-auto w-full px-3 sm:px-6'}`}>
            {!currentChatId && !isNewChat && !isLoading && messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex space-x-2">
                  {[0, 0.1, 0.2].map((delay, i) => (
                    <div key={i} className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: `${delay}s` }} />
                  ))}
                </div>
              </div>
            ) : messages.length === 0 && !isLoading ? (
              <NewChatWelcome onSendMessage={handleSendMessage} disabled={isLoading || isConnecting} prefillMessage={prefillMessage} />
            ) : (
              <>
                {messages.map((msg, i) => {
                  const lastAssistantIdx = messages.reduce((last, m, idx) => m.role === 'assistant' ? idx : last, -1);
                  const isLastAssistant = msg.role === 'assistant' && i === lastAssistantIdx && !isLoading && !streamingText && streamingTools.length === 0;

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
                      images={msg.images}
                      chatId={currentChatId || undefined}
                      onSelectTool={handleSelectTool}
                      onFileClick={handleFileClick}
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
                    onFileClick={handleFileClick}
                  />
                )}

                {streamingText && (
                  <ChatMessage
                    role="assistant"
                    content={streamingText}
                    chatId={currentChatId || undefined}
                    onFileClick={handleFileClick}
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
                <div className="h-32" />
              </>
            )}
          </div>
        </div>

        {error && (
          <div className={`py-3 bg-red-50 border-t border-red-200 ${panelWidth > 0 ? 'px-3 sm:px-6' : 'max-w-5xl mx-auto w-full px-3 sm:px-6'}`}>
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
                placeholder={mode.type === 'general' ? 'Ask me anything about investing...' : `Ask about ${mode.type}...`}
                chatId={currentChatId || undefined}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Side panel ── */}
      {hasAnyPanel && (
        <div
          className="fixed bottom-0 z-40 flex flex-col bg-white border-l border-gray-200 shadow-xl transition-all duration-200"
          style={{ right: rightOffset, width: `${panelWidth}px`, top: 0 }}
        >
          {/* Collapsed rail */}
          {panelCollapsed ? (
            <div className="flex flex-col items-center h-full bg-gray-50 py-3 gap-3">
              <button
                onClick={() => setPanelCollapsed(false)}
                title="Expand panel"
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M15 3v18" />
                </svg>
              </button>
              <div className="w-6 border-t border-gray-200" />
              {openPdfs.map((pdf, i) => (
                <button
                  key={pdf}
                  onClick={() => { setActivePdfIndex(i); setActivePanel('pdf'); setPanelCollapsed(false); }}
                  title={pdf.split('/').pop() || 'PDF'}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-gray-200 transition-colors"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                  </svg>
                </button>
              ))}
              {hasTool && (
                <button
                  onClick={() => { setActivePanel('tool'); setPanelCollapsed(false); }}
                  title="Output"
                  className="p-1.5 rounded-lg text-gray-400 hover:text-blue-500 hover:bg-gray-200 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </button>
              )}
            </div>
          ) : (
            <>
              {/* Tab bar */}
              <div className="flex items-center border-b border-gray-200 bg-gray-50 flex-shrink-0">
                {/* Collapse button — sidebar icon */}
                <button
                  onClick={() => setPanelCollapsed(true)}
                  title="Collapse panel"
                  className="p-2 ml-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg flex-shrink-0"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M15 3v18" />
                  </svg>
                </button>
                <div className="flex flex-1 min-w-0 overflow-x-auto">
                  {hasTool && (
                    <button
                      onClick={() => setActivePanel('tool')}
                      className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors whitespace-nowrap flex-shrink-0 ${
                        effectivePanel === 'tool'
                          ? 'border-blue-500 text-blue-600 bg-white'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      Output
                    </button>
                  )}
                  {openPdfs.map((pdf, i) => (
                    <button
                      key={pdf}
                      onClick={() => { setActivePdfIndex(i); setActivePanel('pdf'); }}
                      className={`group flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors whitespace-nowrap flex-shrink-0 ${
                        effectivePanel === 'pdf' && activePdfIndex === i
                          ? 'border-blue-500 text-blue-600 bg-white'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <svg className="w-3.5 h-3.5 text-red-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                      </svg>
                      <span className="truncate max-w-[100px]">{pdf.split('/').pop()}</span>
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenPdfs(prev => {
                            const next = prev.filter((_, j) => j !== i);
                            if (activePdfIndex >= next.length) setActivePdfIndex(Math.max(0, next.length - 1));
                            if (next.length === 0 && !hasTool) setActivePanel(null);
                            else if (next.length === 0) setActivePanel('tool');
                            return next;
                          });
                        }}
                        className="ml-1 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 transition-opacity"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Panel content */}
              <div className="flex-1 min-h-0">
                {effectivePanel === 'tool' && selectedTool && (
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
                    isStreaming={selectedTool.status === 'calling'}
                    onClose={() => {
                      setSelectedTool(null);
                      if (hasPdf) setActivePanel('pdf');
                      else setActivePanel(null);
                    }}
                  />
                )}

                {effectivePanel === 'pdf' && activePdf && currentChatId && (
                  <PdfCopilot
                    key={activePdf}
                    pdfUrl={`${getApiBaseUrl()}/api/chat-files/${currentChatId}/sandbox-file?path=${encodeURIComponent(activePdf)}`}
                    filename={activePdf.split('/').pop() || activePdf}
                    chatId={currentChatId}
                    sandboxPath={activePdf}
                    refreshTrigger={pdfRefresh}
                    onClose={() => {
                      setOpenPdfs(prev => {
                        const next = prev.filter((_, j) => j !== activePdfIndex);
                        if (activePdfIndex >= next.length) setActivePdfIndex(Math.max(0, next.length - 1));
                        if (next.length === 0 && !hasTool) setActivePanel(null);
                        else if (next.length === 0) setActivePanel('tool');
                        return next;
                      });
                    }}
                  />
                )}
              </div>
            </>
          )}
        </div>
      )}

      <FileViewer
        filename={selectedFile}
        chatId={currentChatId}
        isOpen={!!selectedFile}
        onClose={() => setSelectedFile(null)}
      />

    </div>
  );
}
