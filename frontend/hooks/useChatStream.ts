'use client';

import { useCallback, useRef } from 'react';
import { chatApi } from '@/lib/api';
import { getFileType, getApiBaseUrl } from '@/lib/utils';
import type {
  Message,
  ToolCallStatus,
  SSEOptionsEvent,
  SSEToolCallDetectedEvent,
  SSEToolCallStartEvent,
  SSEToolCallCompleteEvent,
  SSEToolCallStreamingEvent,
  SSEFileContentEvent,
  ImageAttachment,
} from '@/lib/types';

// ═══════════════════════════════════════════════════════════════════════════
// Chat Stream State Machine
// ═══════════════════════════════════════════════════════════════════════════
//
// During a single assistant turn, the LLM can produce interleaved text and
// tool calls: text → tools → text → tools → …
//
// Display slots (what the user sees):
//   messages[]         – finalized content (text-only or tool-only chunks)
//   streamingText      – live text being typed out
//   streamingTools[]   – live tool cards below the text
//
// Invariants:
//   1. streamingText is NEVER cleared except by saving it to messages.
//   2. Tool events never touch streamingText.
//   3. If streamingText is non-empty when a tool arrives, the tool goes
//      into toolQueue and only becomes visible after the text is saved.
// ═══════════════════════════════════════════════════════════════════════════

export interface TimeEstimate {
  seconds: number;
  tools: number;
  description: string;
}

export interface ChatStreamState {
  messages: Message[];
  streamingText: string;
  streamingTools: ToolCallStatus[];
  toolQueue: ToolCallStatus[];
  isLoading: boolean;
  error: string | null;
  pendingOptions: SSEOptionsEvent | null;
  pendingSwapData: import('@/lib/types').SwapData[] | null;
  stream: { close: () => void; reconnect?: () => void } | null;
  toolInsertionCounter: number;
  wasStreamingBeforeHidden: boolean;
  streamStartTime: number | null;
  timeEstimate: TimeEstimate | null;
}

interface UseChatStreamOptions {
  onChatCreated?: (chatId: string) => void;
  onTitleGenerated?: (chatId: string, title: string, icon: string) => void;
  onHistoryRefresh?: () => void;
  onSwapsReceived?: (chatId: string, swaps: import('@/lib/types').SwapData[]) => void;
}

const INITIAL_STATE: Omit<ChatStreamState, 'messages'> = {
  streamingText: '',
  streamingTools: [],
  toolQueue: [],
  isLoading: false,
  error: null,
  pendingOptions: null,
  pendingSwapData: null,
  stream: null,
  toolInsertionCounter: 0,
  wasStreamingBeforeHidden: false,
  streamStartTime: null,
  timeEstimate: null,
};

export function useChatStream(options: UseChatStreamOptions = {}) {
  const chatStatesRef = useRef<Map<string, ChatStreamState>>(new Map());
  const currentChatIdRef = useRef<string | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  // ── Helpers ──────────────────────────────────────────────────────────────

  const getChatState = useCallback((chatId: string): ChatStreamState => {
    if (!chatStatesRef.current.has(chatId)) {
      chatStatesRef.current.set(chatId, { messages: [], ...INITIAL_STATE });
    }
    return chatStatesRef.current.get(chatId)!;
  }, []);

  const update = useCallback((
    chatId: string,
    updates: Partial<ChatStreamState>,
    notify?: (state: ChatStreamState) => void
  ) => {
    const state = getChatState(chatId);
    Object.assign(state, updates);
    if (chatId === currentChatIdRef.current && notify) notify(state);
  }, [getChatState]);

  // ── Tool list helpers ───────────────────────────────────────────────────

  /** Upsert a tool into an array, preserving insertion order. */
  const upsertTool = useCallback((
    list: ToolCallStatus[],
    tool: ToolCallStatus,
    chatId: string
  ): ToolCallStatus[] => {
    const existing = list.find(t => t.tool_call_id === tool.tool_call_id);
    if (existing) {
      return list.map(t =>
        t.tool_call_id === tool.tool_call_id
          ? { ...t, ...tool, _insertionOrder: existing._insertionOrder }
          : t
      );
    }
    const order = getChatState(chatId).toolInsertionCounter++;
    return [...list, { ...tool, _insertionOrder: order }];
  }, [getChatState]);

  // ── Finalization helpers ────────────────────────────────────────────────

  /** Save accumulated streamingTools as a finalized tool message. */
  const saveTools = useCallback((
    chatId: string,
    notify?: (state: ChatStreamState) => void
  ) => {
    const state = getChatState(chatId);
    if (state.streamingTools.length === 0) return;

    const sorted = [...state.streamingTools].sort(
      (a, b) => (a._insertionOrder ?? 0) - (b._insertionOrder ?? 0)
    );
    update(chatId, {
      messages: [...state.messages, {
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        toolCalls: sorted,
        swap_data: state.pendingSwapData || undefined,
      }],
      streamingTools: [],
      pendingSwapData: null,
    }, notify);
  }, [getChatState, update]);

  // ── Stream control ──────────────────────────────────────────────────────

  const stopStream = useCallback((
    chatId: string,
    savePartial: boolean = false,
    notify?: (state: ChatStreamState) => void
  ) => {
    const state = getChatState(chatId);
    state.stream?.close();

    if (savePartial) {
      const msgs = [...state.messages];
      const allTools = [...state.streamingTools, ...state.toolQueue];

      if (allTools.length > 0) {
        msgs.push({
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          toolCalls: allTools.map(t => ({
            ...t,
            status: (t.status === 'detected' || t.status === 'calling') ? 'completed' as const : t.status,
          })),
        });
      }
      if (state.streamingText) {
        msgs.push({
          role: 'assistant',
          content: state.streamingText + ' [interrupted]',
          timestamp: new Date().toISOString(),
        });
      }
      update(chatId, { messages: msgs, ...INITIAL_STATE }, notify);
    } else {
      update(chatId, INITIAL_STATE, notify);
    }
  }, [getChatState, update]);

  // ── SSE event handlers ──────────────────────────────────────────────────

  const createEventHandlers = useCallback((
    chatId: string,
    notify: (state: ChatStreamState) => void
  ) => ({

    // ── Text ──────────────────────────────────────────────────────────────

    onMessageDelta: (event: { delta: string }) => {
      const state = getChatState(chatId);

      // New text starting while tools are on screen → finalize those tools first
      if (!state.streamingText && state.streamingTools.length > 0) {
        saveTools(chatId, notify);
        // Re-read state after saveTools mutated it
        const fresh = getChatState(chatId);
        update(chatId, { streamingText: event.delta }, notify);
        return;
      }

      update(chatId, { streamingText: state.streamingText + event.delta }, notify);
    },

    onMessageEnd: (event: { content: string; timestamp: string }) => {
      const state = getChatState(chatId);
      // Use event.content (authoritative from backend), fall back to streamingText
      const text = event.content?.trim() ? event.content : state.streamingText;

      const updates: Partial<ChatStreamState> = { streamingText: '' };
      if (text.trim()) {
        updates.messages = [...state.messages, {
          role: 'assistant' as const,
          content: text,
          timestamp: event.timestamp,
        }];
      }
      update(chatId, updates, notify);
    },

    // ── Tool lifecycle ────────────────────────────────────────────────────

    onToolCallDetected: (event: SSEToolCallDetectedEvent) => {
      const state = getChatState(chatId);
      if (state.streamingTools.find(t => t.tool_call_id === event.tool_call_id)) return;

      // Just add the tool. Never touch streamingText here —
      // onMessageEnd handles saving text to messages.
      update(chatId, {
        streamingTools: upsertTool(state.streamingTools, {
          tool_call_id: event.tool_call_id,
          tool_name: event.tool_name,
          status: 'detected',
          statusMessage: event.tool_name,
        }, chatId),
      }, notify);
    },

    onToolCallStart: (event: SSEToolCallStartEvent) => {
      const state = getChatState(chatId);
      update(chatId, {
        streamingTools: upsertTool(state.streamingTools, {
          tool_call_id: event.tool_call_id,
          tool_name: event.tool_name,
          status: 'calling',
          statusMessage: event.user_description || event.tool_name,
          arguments: event.arguments,
          agent_id: event.agent_id,
          parent_agent_id: event.parent_agent_id,
        }, chatId),
      }, notify);
    },

    onToolCallComplete: (event: SSEToolCallCompleteEvent) => {
      const state = getChatState(chatId);
      const existing = state.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
      const hasStreamedOutput = existing?.code_output &&
        (existing.code_output.stdout || existing.code_output.stderr);

      const completed: ToolCallStatus = {
        ...existing,
        tool_call_id: event.tool_call_id,
        tool_name: event.tool_name,
        status: event.status,
        error: event.error,
        code_output: hasStreamedOutput ? existing!.code_output : event.code_output,
        search_results: event.search_results,
        agent_id: event.agent_id,
        parent_agent_id: event.parent_agent_id,
        sub_agent_id: event.sub_agent_id,
        sub_agent_chat_id: event.sub_agent_chat_id,
      };

      const updates: Partial<ChatStreamState> = {
        streamingTools: upsertTool(state.streamingTools, completed, chatId),
      };

      if (event.tool_name === 'present_swaps' && event.swap_data) {
        updates.pendingSwapData = event.swap_data;
        optionsRef.current.onSwapsReceived?.(chatId, event.swap_data);
      }

      update(chatId, updates, notify);
    },

    // ── Tool output streaming ─────────────────────────────────────────────

    onCodeOutput: (event: { stream: 'stdout' | 'stderr'; content: string }) => {
      const state = getChatState(chatId);
      const target = [...state.streamingTools].reverse().find(
        t => t.tool_name === 'execute_code' && t.status === 'calling'
      );
      if (!target) return;

      const output = target.code_output || { stdout: '', stderr: '' };
      const updated: ToolCallStatus = {
        ...target,
        code_output: {
          stdout: event.stream === 'stdout' ? (output.stdout || '') + event.content + '\n' : output.stdout,
          stderr: event.stream === 'stderr' ? (output.stderr || '') + event.content + '\n' : output.stderr,
        },
      };

      update(chatId, { streamingTools: upsertTool(state.streamingTools, updated, chatId) }, notify);
    },

    onFileContent: (event: SSEFileContentEvent) => {
      const state = getChatState(chatId);
      const tool = state.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
      if (!tool) return;

      const content = tool.file_content?.content || '';
      const newContent = event.is_complete ? content : (event.content ? content + event.content : content);

      const updated: ToolCallStatus = {
        ...tool,
        file_content: {
          filename: event.filename,
          content: newContent,
          file_type: event.file_type,
          is_complete: event.is_complete,
        },
      };

      update(chatId, { streamingTools: upsertTool(state.streamingTools, updated, chatId) }, notify);
    },

    onToolCallStreaming: (event: SSEToolCallStreamingEvent) => {
      if (!event.file_content_delta) return;

      const state = getChatState(chatId);
      const existing = state.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
      const currentContent = existing?.file_content?.content || '';

      const updated: ToolCallStatus = {
        tool_call_id: event.tool_call_id,
        tool_name: event.tool_name,
        status: 'calling',
        statusMessage: existing?.statusMessage || `Writing ${event.filename || 'file'}...`,
        file_content: {
          filename: event.filename || existing?.file_content?.filename || 'unknown',
          content: currentContent + event.file_content_delta,
          file_type: getFileType(event.filename || ''),
          is_complete: false,
        },
        ...(existing && {
          arguments: existing.arguments,
          agent_id: existing.agent_id,
          parent_agent_id: existing.parent_agent_id,
          _insertionOrder: existing._insertionOrder,
        }),
      };

      update(chatId, { streamingTools: upsertTool(state.streamingTools, updated, chatId) }, notify);
    },

    // ── Lifecycle ─────────────────────────────────────────────────────────

    onToolsEnd: () => {},

    onTimeEstimate: (event: { estimated_seconds: number; estimated_tools: number; description: string }) => {
      update(chatId, {
        timeEstimate: {
          seconds: event.estimated_seconds,
          tools: event.estimated_tools,
          description: event.description,
        },
      }, notify);
    },

    onOptions: (event: SSEOptionsEvent) => {
      update(chatId, { pendingOptions: event }, notify);
    },

    onDone: async () => {
      const state = getChatState(chatId);

      // Save any unsaved streaming text
      if (state.streamingText.trim()) {
        update(chatId, {
          messages: [...state.messages, {
            role: 'assistant' as const,
            content: state.streamingText,
            timestamp: new Date().toISOString(),
          }],
          streamingText: '',
        }, notify);
      }

      saveTools(chatId, notify);
      window.dispatchEvent(new CustomEvent('bots:refresh'));
      update(chatId, { isLoading: false, stream: null, toolQueue: [] }, notify);
      options.onHistoryRefresh?.();
    },

    onError: (event: { error: string }) => {
      console.error('SSE error:', event.error);
      const state = getChatState(chatId);
      const msgs = [...state.messages];
      const allTools = [...state.streamingTools, ...state.toolQueue];

      if (allTools.length > 0) {
        msgs.push({
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          toolCalls: allTools.map(t => ({
            ...t,
            status: (t.status === 'detected' || t.status === 'calling') ? 'error' as const : t.status,
          })),
        });
      }
      if (state.streamingText.trim()) {
        msgs.push({
          role: 'assistant',
          content: state.streamingText,
          timestamp: new Date().toISOString(),
        });
      }

      update(chatId, {
        messages: msgs,
        streamingText: '',
        streamingTools: [],
        toolQueue: [],
        error: event.error,
        isLoading: false,
        stream: null,
      }, notify);
    },
  }), [getChatState, update, upsertTool, saveTools, options]);

  // ── Send message ────────────────────────────────────────────────────────

  const sendMessage = useCallback(async (
    content: string,
    userId: string,
    chatId: string | null,
    isNewChat: boolean,
    images: ImageAttachment[] | undefined,
    onStateChange: (state: ChatStreamState) => void,
    onChatIdChange: (chatId: string) => void,
    skills?: string[],
    investorPersona?: string
  ): Promise<string> => {
    if (!content.trim() && (!images || images.length === 0)) {
      throw new Error('Message content is required');
    }

    const trimmed = content.trim();

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

    const displayContent = trimmed +
      (images?.length ? ` [${images.length} image${images.length > 1 ? 's' : ''} attached]` : '');

    const state = getChatState(targetChatId);
    state.messages = [...state.messages, {
      role: 'user',
      content: displayContent,
      timestamp: new Date().toISOString(),
    }];
    state.isLoading = true;
    state.toolInsertionCounter = 0;
    state.streamStartTime = Date.now();
    state.timeEstimate = null;
    onStateChange(state);

    // Generate title for first message
    if (state.messages.length === 1) {
      setTimeout(() => {
        chatApi.generateTitle(targetChatId, trimmed)
          .then(r => optionsRef.current.onTitleGenerated?.(targetChatId, r.title, r.icon))
          .catch(() => optionsRef.current.onTitleGenerated?.(targetChatId, trimmed.slice(0, 50) + (trimmed.length > 50 ? '...' : ''), '💬'));
      }, 100);
    }

    try {
      const stream = chatApi.sendMessageStream(
        trimmed, userId, targetChatId,
        createEventHandlers(targetChatId, onStateChange),
        images, skills, investorPersona
      );
      update(targetChatId, { stream }, onStateChange);
      return targetChatId;
    } catch (err) {
      update(targetChatId, {
        messages: state.messages.slice(0, -1),
        error: 'Failed to send message',
        isLoading: false,
        stream: null,
      }, onStateChange);
      throw err;
    }
  }, [getChatState, stopStream, update, createEventHandlers, options]);

  // ── Public API ──────────────────────────────────────────────────────────

  return {
    getChatState,
    updateChatState: update,
    sendMessage,
    stopStream,
    setCurrentChatId: (chatId: string | null) => { currentChatIdRef.current = chatId; },
    clearPendingOptions: (chatId: string, notify?: (state: ChatStreamState) => void) => {
      update(chatId, { pendingOptions: null }, notify);
    },
  };
}
