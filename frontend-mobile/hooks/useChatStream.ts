import { useState, useCallback, useRef } from 'react';
import { chatApi, SSEEventHandlers } from '@/lib/api';
import type { Message, ToolCallStatus, ImageAttachment } from '@/lib/types';

interface ChatStreamState {
  messages: Message[];
  streamingText: string;
  streamingTools: ToolCallStatus[];
  isStreaming: boolean;
  error: string | null;
}

export function useChatStream(userId: string, chatId: string) {
  const [state, setState] = useState<ChatStreamState>({
    messages: [],
    streamingText: '',
    streamingTools: [],
    isStreaming: false,
    error: null,
  });

  const streamRef = useRef<{ close: () => void } | null>(null);

  const setMessages = useCallback((msgs: Message[]) => {
    setState(prev => ({ ...prev, messages: msgs }));
  }, []);

  const sendMessage = useCallback((text: string, images?: ImageAttachment[], model?: string) => {
    const userMessage: Message = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      streamingText: '',
      streamingTools: [],
      isStreaming: true,
      error: null,
    }));

    const handlers: SSEEventHandlers = {
      onMessageDelta: (event) => {
        setState(prev => ({
          ...prev,
          streamingText: prev.streamingText + event.delta,
        }));
      },
      onToolCallStart: (event) => {
        setState(prev => ({
          ...prev,
          streamingTools: [
            ...prev.streamingTools,
            {
              tool_call_id: event.tool_call_id,
              tool_name: event.tool_name,
              status: 'calling',
              arguments: event.arguments,
            },
          ],
        }));
      },
      onToolCallComplete: (event) => {
        setState(prev => ({
          ...prev,
          streamingTools: prev.streamingTools.map(t =>
            t.tool_call_id === event.tool_call_id
              ? { ...t, status: event.status, result_summary: event.result_summary, error: event.error }
              : t
          ),
        }));
      },
      onToolCallDetected: (event) => {
        setState(prev => ({
          ...prev,
          streamingTools: [
            ...prev.streamingTools,
            {
              tool_call_id: event.tool_call_id,
              tool_name: event.tool_name,
              status: 'detected',
            },
          ],
        }));
      },
      onDone: () => {
        setState(prev => {
          const assistantMessage: Message = {
            role: 'assistant',
            content: prev.streamingText,
            timestamp: new Date().toISOString(),
            toolCalls: prev.streamingTools.length > 0 ? prev.streamingTools : undefined,
          };
          return {
            ...prev,
            messages: [...prev.messages, assistantMessage],
            streamingText: '',
            streamingTools: [],
            isStreaming: false,
          };
        });
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
  }, [userId, chatId]);

  const stopStream = useCallback(() => {
    streamRef.current?.close();
    setState(prev => ({ ...prev, isStreaming: false }));
  }, []);

  return {
    ...state,
    setMessages,
    sendMessage,
    stopStream,
  };
}
