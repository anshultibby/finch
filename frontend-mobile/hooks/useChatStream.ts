import { useState, useCallback, useRef } from 'react';
import { Platform } from 'react-native';
import * as Haptics from 'expo-haptics';
import { chatApi, SSEEventHandlers } from '@/lib/api';
import type { Message, ToolCallStatus, ImageAttachment, TodoItem } from '@/lib/types';

interface ChatStreamState {
  messages: Message[];
  streamingText: string;
  streamingTools: ToolCallStatus[];
  /** Live task-phase checklist from update_todos. Ephemeral — cleared on done. */
  todos: TodoItem[];
  /** Live reasoning text. Evaporates when answer text or a tool arrives. */
  thinkingText: string;
  isStreaming: boolean;
  error: string | null;
}

const EMPTY_STREAM = {
  streamingText: '',
  streamingTools: [] as ToolCallStatus[],
  todos: [] as TodoItem[],
  thinkingText: '',
};

export function useChatStream(userId: string, chatId: string) {
  const [state, setState] = useState<ChatStreamState>({
    messages: [],
    ...EMPTY_STREAM,
    isStreaming: false,
    error: null,
  });

  const streamRef = useRef<{ close: () => void } | null>(null);
  const isStreamingRef = useRef(false);
  isStreamingRef.current = state.isStreaming;

  const setMessages = useCallback((msgs: Message[]) => {
    setState(prev => ({ ...prev, messages: msgs }));
  }, []);

  // Replace local state with the server's view of the chat. Used when a
  // dropped stream finished server-side (recovery) — the in-memory transcript
  // is stale, so reload the completed turn from history.
  const reloadFromServer = useCallback(async () => {
    try {
      const data = await chatApi.getChatHistoryForDisplay(chatId);
      setState(prev => ({
        ...prev,
        messages: (data.messages || []).map(m => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp || new Date().toISOString(),
          toolCalls: m.tool_calls,
        })),
        ...EMPTY_STREAM,
        isStreaming: false,
        error: null,
      }));
    } catch {
      setState(prev => ({ ...prev, isStreaming: false }));
    }
  }, [chatId]);

  // Called when the app returns to the foreground: iOS suspends sockets, so a
  // stream that was running when the user left is likely dead. If the backend
  // already finished, pull the result; if it's still working, keep waiting
  // (the poll fallback in sendMessageStream covers the rest).
  const recoverIfStalled = useCallback(async () => {
    if (!isStreamingRef.current) return;
    const status = await chatApi.checkChatStatus(chatId);
    if (!status.is_processing) {
      await reloadFromServer();
      if (Platform.OS !== 'web') {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      }
    }
  }, [chatId, reloadFromServer]);

  const sendMessage = useCallback((text: string, images?: ImageAttachment[], model?: string) => {
    const userMessage: Message = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      ...EMPTY_STREAM,
      isStreaming: true,
      error: null,
    }));

    const handlers: SSEEventHandlers = {
      onMessageDelta: (event) => {
        setState(prev => ({
          ...prev,
          streamingText: prev.streamingText + event.delta,
          thinkingText: '',
        }));
      },
      onThinkingDelta: (event) => {
        setState(prev => ({
          ...prev,
          thinkingText: prev.thinkingText + event.delta,
        }));
      },
      onTodoUpdate: (event) => {
        setState(prev => ({ ...prev, todos: event.todos || [] }));
      },
      onToolCallDetected: (event) => {
        setState(prev => {
          if (event.tool_call_id && prev.streamingTools.some(t => t.tool_call_id === event.tool_call_id)) {
            return prev;
          }
          return {
            ...prev,
            streamingTools: [
              ...prev.streamingTools,
              {
                tool_call_id: event.tool_call_id,
                tool_name: event.tool_name,
                status: 'detected',
              },
            ],
          };
        });
      },
      onToolCallStart: (event) => {
        setState(prev => {
          const existing = prev.streamingTools.find(t => t.tool_call_id === event.tool_call_id);
          const started: ToolCallStatus = {
            tool_call_id: event.tool_call_id,
            tool_name: event.tool_name,
            status: 'calling',
            arguments: event.arguments,
            task_id: event.task_id,
            agent_id: event.agent_id,
            parent_agent_id: event.parent_agent_id,
          };
          return {
            ...prev,
            thinkingText: '',
            streamingTools: existing
              ? prev.streamingTools.map(t =>
                  t.tool_call_id === event.tool_call_id ? { ...t, ...started } : t
                )
              : [...prev.streamingTools, started],
          };
        });
      },
      onToolStatus: (event) => {
        if (!event.tool_call_id) return;
        setState(prev => ({
          ...prev,
          streamingTools: prev.streamingTools.map(t =>
            t.tool_call_id === event.tool_call_id ? { ...t, statusMessage: event.message } : t
          ),
        }));
      },
      onToolCallComplete: (event) => {
        setState(prev => ({
          ...prev,
          streamingTools: prev.streamingTools.map(t =>
            t.tool_call_id === event.tool_call_id
              ? { ...t, status: event.status, result_summary: event.result_summary, error: event.error, task_id: event.task_id ?? t.task_id }
              : t
          ),
        }));
      },
      onDone: () => {
        if (Platform.OS !== 'web') {
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
        }
        setState(prev => {
          const assistantMessage: Message = {
            role: 'assistant',
            content: prev.streamingText,
            timestamp: new Date().toISOString(),
            toolCalls: prev.streamingTools.length > 0 ? prev.streamingTools : undefined,
          };
          // A recovered stream has no local transcript — reloadFromServer
          // (via onStreamRecovered) repopulates messages instead.
          const hasLocalTurn = prev.streamingText.length > 0 || prev.streamingTools.length > 0;
          return {
            ...prev,
            messages: hasLocalTurn ? [...prev.messages, assistantMessage] : prev.messages,
            ...EMPTY_STREAM,
            isStreaming: false,
          };
        });
      },
      onStreamRecovered: () => {
        reloadFromServer();
      },
      onError: (event) => {
        setState(prev => ({
          ...prev,
          isStreaming: false,
          error: event.error,
        }));
      },
    };

    streamRef.current = chatApi.sendMessageStream(text, userId, chatId, handlers, images, undefined, model);
  }, [userId, chatId, reloadFromServer]);

  const stopStream = useCallback(() => {
    streamRef.current?.close();
    setState(prev => ({ ...prev, ...EMPTY_STREAM, isStreaming: false }));
  }, []);

  return {
    ...state,
    setMessages,
    sendMessage,
    stopStream,
    recoverIfStalled,
  };
}
