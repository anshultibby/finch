'use client';

import { useCallback, useRef } from 'react';
import { chatApi, resourcesApi } from '@/lib/api';
import { getFileType, getApiBaseUrl } from '@/lib/utils';
import type {
  Message,
  ToolCallStatus,
  Resource,
  SSEOptionsEvent,
  SSEToolCallStartEvent,
  SSEToolCallCompleteEvent,
  SSEToolCallStreamingEvent,
  SSEFileContentEvent,
  ImageAttachment,
} from '@/lib/types';
import { FileItem } from '@/components/FileTree';

// ═══════════════════════════════════════════════════════════════════════════
// Chat Stream State Management Hook
// ═══════════════════════════════════════════════════════════════════════════
//
// This hook encapsulates all the complex SSE streaming logic for chat messages.
// It manages per-chat state and provides a clean interface for the ChatView.
//
// DESIGN PRINCIPLE: message_end is the ONLY place that saves text to messages.
// streamingText is purely for live display during streaming.
// ═══════════════════════════════════════════════════════════════════════════

export interface ChatStreamState {
  messages: Message[];
  streamingText: string;
  streamingTools: ToolCallStatus[];
  isLoading: boolean;
  error: string | null;
  pendingOptions: SSEOptionsEvent | null;
  resources: Resource[];
  stream: { close: () => void } | null;
  chatFiles: FileItem[];
  toolInsertionCounter: number;
}

interface UseChatStreamOptions {
  onChatCreated?: (chatId: string) => void;
  onTitleGenerated?: (chatId: string, title: string, icon: string) => void;
  onHistoryRefresh?: () => void;
}

export function useChatStream(options: UseChatStreamOptions = {}) {
  const chatStatesRef = useRef<Map<string, ChatStreamState>>(new Map());
  const currentChatIdRef = useRef<string | null>(null);

  // ─────────────────────────────────────────────────────────────────────────
  // State Management Helpers
  // ─────────────────────────────────────────────────────────────────────────

  const getInitialState = (): ChatStreamState => ({
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

  const getChatState = useCallback((chatId: string): ChatStreamState => {
    if (!chatStatesRef.current.has(chatId)) {
      chatStatesRef.current.set(chatId, getInitialState());
    }
    return chatStatesRef.current.get(chatId)!;
  }, []);

  const updateChatState = useCallback((
    chatId: string,
    updates: Partial<ChatStreamState>,
    onStateChange?: (state: ChatStreamState) => void
  ) => {
    const state = getChatState(chatId);
    Object.assign(state, updates);
    
    if (chatId === currentChatIdRef.current && onStateChange) {
      onStateChange(state);
    }
  }, [getChatState]);

  // ─────────────────────────────────────────────────────────────────────────
  // Tool Management
  // ─────────────────────────────────────────────────────────────────────────

  const addOrUpdateTool = useCallback((
    chatId: string,
    newTool: ToolCallStatus
  ): ToolCallStatus[] => {
    const state = getChatState(chatId);
    const existingTool = state.streamingTools.find(
      t => t.tool_call_id === newTool.tool_call_id
    );

    if (existingTool) {
      return state.streamingTools.map(t =>
        t.tool_call_id === newTool.tool_call_id
          ? { ...t, ...newTool, _insertionOrder: existingTool._insertionOrder }
          : t
      );
    }

    const insertionOrder = state.toolInsertionCounter++;
    return [...state.streamingTools, { ...newTool, _insertionOrder: insertionOrder }];
  }, [getChatState]);

  const saveAccumulatedTools = useCallback((
    chatId: string,
    onStateChange?: (state: ChatStreamState) => void
  ) => {
    const state = getChatState(chatId);
    if (state.streamingTools.length > 0) {
      const sortedTools = [...state.streamingTools].sort(
        (a, b) => (a._insertionOrder ?? 0) - (b._insertionOrder ?? 0)
      );
      updateChatState(chatId, {
        messages: [...state.messages, {
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          toolCalls: sortedTools,
        }],
        streamingTools: [],
      }, onStateChange);
    }
  }, [getChatState, updateChatState]);

  // ─────────────────────────────────────────────────────────────────────────
  // Stream Control
  // ─────────────────────────────────────────────────────────────────────────

  const stopStream = useCallback((
    chatId: string,
    savePartialResponse: boolean = false,
    onStateChange?: (state: ChatStreamState) => void
  ) => {
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
      }, onStateChange);
    } else {
      updateChatState(chatId, {
        streamingText: '',
        streamingTools: [],
        isLoading: false,
        stream: null,
      }, onStateChange);
    }
  }, [getChatState, updateChatState]);

  // ─────────────────────────────────────────────────────────────────────────
  // SSE Event Handlers
  // ─────────────────────────────────────────────────────────────────────────

  const createEventHandlers = useCallback((
    chatId: string,
    onStateChange: (state: ChatStreamState) => void
  ) => ({
    onMessageDelta: (event: { delta: string }) => {
      const state = getChatState(chatId);

      // If text is starting and there are accumulated tools, save tools first
      if (!state.streamingText && state.streamingTools.length > 0) {
        const sortedTools = [...state.streamingTools].sort(
          (a, b) => (a._insertionOrder ?? 0) - (b._insertionOrder ?? 0)
        );
        updateChatState(chatId, {
          messages: [...state.messages, {
            role: 'assistant',
            content: '',
            timestamp: new Date().toISOString(),
            toolCalls: sortedTools,
          }],
          streamingTools: [],
          streamingText: event.delta,
        }, onStateChange);
        return;
      }

      updateChatState(chatId, {
        streamingText: state.streamingText + event.delta,
      }, onStateChange);
    },

    onMessageEnd: (event: { content: string; timestamp: string; tool_calls?: any[] }) => {
      const state = getChatState(chatId);
      const hasToolCalls = event.tool_calls && event.tool_calls.length > 0;

      if (event.content?.trim()) {
        updateChatState(chatId, {
          messages: [...state.messages, {
            role: 'assistant',
            content: event.content,
            timestamp: event.timestamp,
          }],
          streamingText: '',
        }, onStateChange);
      } else {
        updateChatState(chatId, { streamingText: '' }, onStateChange);
      }
    },

    onToolCallStart: (event: SSEToolCallStartEvent) => {
      const state = getChatState(chatId);
      const isNewTool = !state.streamingTools.find(
        t => t.tool_call_id === event.tool_call_id
      );

      const updates: Partial<ChatStreamState> = {};
      if (isNewTool && state.streamingText.trim()) {
        updates.streamingText = '';
      }

      const newTool: ToolCallStatus = {
        tool_call_id: event.tool_call_id,
        tool_name: event.tool_name,
        status: 'calling',
        statusMessage: event.user_description || event.tool_name,
        arguments: event.arguments,
        agent_id: event.agent_id,
        parent_agent_id: event.parent_agent_id,
      };

      updateChatState(chatId, {
        ...updates,
        streamingTools: addOrUpdateTool(chatId, newTool),
      }, onStateChange);
    },

    onToolCallComplete: (event: SSEToolCallCompleteEvent) => {
      const state = getChatState(chatId);
      const existingTool = state.streamingTools.find(
        t => t.tool_call_id === event.tool_call_id
      );

      const hasStreamedOutput = existingTool?.code_output &&
        (existingTool.code_output.stdout || existingTool.code_output.stderr);

      const completedTool: ToolCallStatus = {
        ...existingTool,
        tool_call_id: event.tool_call_id,
        tool_name: event.tool_name,
        status: event.status,
        error: event.error,
        code_output: hasStreamedOutput ? existingTool!.code_output : event.code_output,
        search_results: event.search_results,
        agent_id: event.agent_id,
        parent_agent_id: event.parent_agent_id,
      };

      updateChatState(chatId, {
        streamingTools: addOrUpdateTool(chatId, completedTool),
      }, onStateChange);
    },

    onCodeOutput: (event: { stream: 'stdout' | 'stderr'; content: string }) => {
      const state = getChatState(chatId);
      const executeCodeTools = state.streamingTools.filter(
        t => t.tool_name === 'execute_code' && t.status === 'calling'
      );
      if (executeCodeTools.length === 0) return;

      const latestTool = executeCodeTools[executeCodeTools.length - 1];
      const currentOutput = latestTool.code_output || { stdout: '', stderr: '' };

      updateChatState(chatId, {
        streamingTools: state.streamingTools.map(t =>
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
      }, onStateChange);
    },

    onFileContent: (event: SSEFileContentEvent) => {
      const state = getChatState(chatId);
      const tool = state.streamingTools.find(
        t => t.tool_call_id === event.tool_call_id
      );
      if (!tool) return;

      const currentContent = tool.file_content?.content || '';
      const newContent = event.is_complete
        ? currentContent
        : (event.content ? currentContent + event.content : currentContent);

      updateChatState(chatId, {
        streamingTools: state.streamingTools.map(t =>
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
      }, onStateChange);
    },

    onToolCallStreaming: (event: SSEToolCallStreamingEvent) => {
      if (!event.file_content_delta) return;

      const state = getChatState(chatId);
      const existingTool = state.streamingTools.find(
        t => t.tool_call_id === event.tool_call_id
      );
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

      const updates: Partial<ChatStreamState> = {};
      if (!existingTool && state.streamingText.trim()) {
        updates.streamingText = '';
      }

      updateChatState(chatId, {
        ...updates,
        streamingTools: addOrUpdateTool(chatId, toolWithContent),
      }, onStateChange);
    },

    onToolsEnd: () => {
      // No-op: tools are saved on done
    },

    onOptions: (event: SSEOptionsEvent) => {
      updateChatState(chatId, { pendingOptions: event }, onStateChange);
    },

    onDelegationStart: () => {},
    onDelegationEnd: () => {},

    onDone: async () => {
      saveAccumulatedTools(chatId, onStateChange);

      try {
        const [chatResources, chatFilesResponse] = await Promise.all([
          resourcesApi.getChatResources(chatId),
          fetch(`${getApiBaseUrl()}/api/chat-files/${chatId}`)
            .then(r => r.ok ? r.json() : [])
            .catch(() => [])
        ]);

        updateChatState(chatId, {
          isLoading: false,
          stream: null,
          resources: chatResources,
          chatFiles: chatFilesResponse,
        }, onStateChange);
      } catch (err) {
        console.error('Error reloading resources:', err);
        updateChatState(chatId, {
          isLoading: false,
          stream: null,
        }, onStateChange);
      }

      options.onHistoryRefresh?.();
    },

    onError: (event: { error: string }) => {
      console.error('SSE error:', event.error);
      updateChatState(chatId, {
        error: event.error,
        isLoading: false,
        stream: null,
      }, onStateChange);
    },
  }), [getChatState, updateChatState, addOrUpdateTool, saveAccumulatedTools, options]);

  // ─────────────────────────────────────────────────────────────────────────
  // Send Message
  // ─────────────────────────────────────────────────────────────────────────

  const sendMessage = useCallback(async (
    content: string,
    userId: string,
    chatId: string | null,
    isNewChat: boolean,
    images: ImageAttachment[] | undefined,
    onStateChange: (state: ChatStreamState) => void,
    onChatIdChange: (chatId: string) => void
  ): Promise<string> => {
    if (!content.trim() && (!images || images.length === 0)) {
      throw new Error('Message content is required');
    }

    const trimmedContent = content.trim();

    // Determine target chat ID
    let targetChatId: string;
    if (isNewChat || !chatId) {
      targetChatId = crypto.randomUUID();
      onChatIdChange(targetChatId);
      getChatState(targetChatId);
      options.onChatCreated?.(targetChatId);
    } else {
      targetChatId = chatId;
      if (getChatState(targetChatId).isLoading) {
        stopStream(targetChatId, true, onStateChange);
      }
    }

    currentChatIdRef.current = targetChatId;

    const displayContent = trimmedContent + 
      (images && images.length > 0 
        ? ` [${images.length} image${images.length > 1 ? 's' : ''} attached]` 
        : '');

    const userMessage: Message = {
      role: 'user',
      content: displayContent,
      timestamp: new Date().toISOString(),
    };

    const state = getChatState(targetChatId);
    state.messages = [...state.messages, userMessage];
    state.isLoading = true;
    state.toolInsertionCounter = 0;

    onStateChange(state);

    // Generate title for first message
    const isFirstMessage = state.messages.length === 1;
    if (isFirstMessage) {
      setTimeout(() => {
        chatApi.generateTitle(targetChatId, trimmedContent)
          .then((response) => {
            options.onTitleGenerated?.(targetChatId, response.title, response.icon);
          })
          .catch(err => {
            console.error('Error generating chat title:', err);
            options.onHistoryRefresh?.();
          });
      }, 100);
    }

    try {
      const stream = chatApi.sendMessageStream(
        trimmedContent,
        userId,
        targetChatId,
        createEventHandlers(targetChatId, onStateChange),
        images
      );

      updateChatState(targetChatId, { stream }, onStateChange);
      return targetChatId;
    } catch (err) {
      const messagesWithoutLast = state.messages.slice(0, -1);
      updateChatState(targetChatId, {
        messages: messagesWithoutLast,
        error: 'Failed to send message',
        isLoading: false,
        stream: null,
      }, onStateChange);
      throw err;
    }
  }, [getChatState, stopStream, updateChatState, createEventHandlers, options]);

  // ─────────────────────────────────────────────────────────────────────────
  // Public API
  // ─────────────────────────────────────────────────────────────────────────

  return {
    getChatState,
    updateChatState,
    sendMessage,
    stopStream,
    setCurrentChatId: (chatId: string | null) => {
      currentChatIdRef.current = chatId;
    },
    clearPendingOptions: (chatId: string, onStateChange?: (state: ChatStreamState) => void) => {
      updateChatState(chatId, { pendingOptions: null }, onStateChange);
    },
  };
}

