// ═══════════════════════════════════════════════════════════════════════════
// API Client
// ═══════════════════════════════════════════════════════════════════════════

import axios from 'axios';

// Re-export all types for backward compatibility
export * from './types';

import type {
  ChatResponse,
  ChatHistory,
  UserChatsResponse,
  GenerateTitleResponse,
  Resource,
  SnapTradeConnectionResponse,
  SnapTradeStatusResponse,
  BrokerageAccountsResponse,
  BrokeragesResponse,
  ImageAttachment,
  SSEAssistantMessageDeltaEvent,
  SSEMessageEndEvent,
  SSEToolCallStartEvent,
  SSEToolCallCompleteEvent,
  SSEToolStatusEvent,
  SSEToolProgressEvent,
  SSEToolLogEvent,
  SSECodeOutputEvent,
  SSEFileContentEvent,
  SSEToolCallStreamingEvent,
  SSEOptionsEvent,
  SSEDoneEvent,
  SSEErrorEvent,
  ToolCallStatus,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// SSE Event Handlers Interface
// ─────────────────────────────────────────────────────────────────────────────

export interface SSEEventHandlers {
  onMessageDelta?: (event: SSEAssistantMessageDeltaEvent) => void;
  onMessageEnd?: (event: SSEMessageEndEvent) => void;
  onToolCallStart?: (event: SSEToolCallStartEvent) => void;
  onToolCallComplete?: (event: SSEToolCallCompleteEvent) => void;
  onToolsEnd?: () => void;
  onToolStatus?: (event: SSEToolStatusEvent) => void;
  onToolProgress?: (event: SSEToolProgressEvent) => void;
  onToolLog?: (event: SSEToolLogEvent) => void;
  onCodeOutput?: (event: SSECodeOutputEvent) => void;
  onFileContent?: (event: SSEFileContentEvent) => void;
  onToolCallStreaming?: (event: SSEToolCallStreamingEvent) => void;
  onDelegationStart?: (event: { direction: string; agent_id: string; parent_agent_id: string }) => void;
  onDelegationEnd?: (event: { success: boolean; summary: string; files_created: string[]; error?: string }) => void;
  onOptions?: (event: SSEOptionsEvent) => void;
  onDone?: (event: SSEDoneEvent) => void;
  onError?: (event: SSEErrorEvent) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Chat API
// ─────────────────────────────────────────────────────────────────────────────

export const chatApi = {
  sendMessage: async (message: string, userId: string, chatId: string): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat', {
      message,
      user_id: userId,
      chat_id: chatId,
    });
    return response.data;
  },

  sendMessageStream: (
    message: string,
    userId: string,
    chatId: string,
    handlers: SSEEventHandlers,
    images?: ImageAttachment[]
  ): { close: () => void } => {
    const url = new URL('/chat/stream', API_BASE_URL);
    const abortController = new AbortController();

    const requestBody = {
      message,
      user_id: userId,
      chat_id: chatId,
      ...(images && images.length > 0 && { images }),
    };

    fetch(url.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
      signal: abortController.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('Response body is null');
        }

        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim()) continue;

            const eventMatch = line.match(/event:\s*(\w+)/);
            const dataMatch = line.match(/data:\s*([\s\S]+)/);

            if (eventMatch && dataMatch) {
              const eventType = eventMatch[1];
              const eventData = JSON.parse(dataMatch[1]);

              switch (eventType) {
                case 'assistant_message_delta':
                case 'message_delta':
                  handlers.onMessageDelta?.(eventData);
                  break;
                case 'message_end':
                  handlers.onMessageEnd?.(eventData);
                  break;
                case 'tool_call_start':
                  handlers.onToolCallStart?.(eventData);
                  break;
                case 'tool_call_complete':
                  handlers.onToolCallComplete?.(eventData);
                  break;
                case 'tools_end':
                  handlers.onToolsEnd?.();
                  break;
                case 'tool_status':
                  handlers.onToolStatus?.(eventData);
                  break;
                case 'tool_progress':
                  handlers.onToolProgress?.(eventData);
                  break;
                case 'delegation_start':
                  handlers.onDelegationStart?.(eventData);
                  break;
                case 'delegation_end':
                  handlers.onDelegationEnd?.(eventData);
                  break;
                case 'tool_log':
                  handlers.onToolLog?.(eventData);
                  break;
                case 'code_output':
                  handlers.onCodeOutput?.(eventData);
                  break;
                case 'file_content':
                  handlers.onFileContent?.(eventData);
                  break;
                case 'tool_call_streaming':
                  handlers.onToolCallStreaming?.(eventData);
                  break;
                case 'tool_options':
                  handlers.onOptions?.(eventData);
                  break;
                case 'done':
                  handlers.onDone?.(eventData);
                  break;
                case 'error':
                  handlers.onError?.(eventData);
                  break;
                case 'thinking':
                  // Informational - ignore
                  break;
              }
            }
          }
        }
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          console.error('SSE stream error:', error);
          handlers.onError?.({
            error: error.message,
            timestamp: new Date().toISOString(),
          });
        }
      });

    return { close: () => abortController.abort() };
  },

  getChatHistory: async (chatId: string): Promise<ChatHistory> => {
    const response = await api.get<ChatHistory>(`/chat/history/${chatId}`);
    return response.data;
  },

  getChatHistoryForDisplay: async (chatId: string): Promise<{
    chat_id: string;
    messages: Array<{
      role: 'user' | 'assistant';
      content: string;
      timestamp?: string;
      tool_calls?: ToolCallStatus[];
    }>;
  }> => {
    const response = await api.get(`/chat/history/${chatId}/display`);
    return response.data;
  },

  clearChatHistory: async (chatId: string): Promise<void> => {
    await api.delete(`/chat/history/${chatId}`);
  },

  getUserChats: async (userId: string): Promise<UserChatsResponse> => {
    const response = await api.get<UserChatsResponse>(`/chat/user/${userId}/chats`);
    return response.data;
  },

  createChat: async (userId: string): Promise<string> => {
    const response = await api.post<{ chat_id: string }>('/chat/create', { user_id: userId });
    return response.data.chat_id;
  },

  generateTitle: async (chatId: string, firstMessage: string): Promise<GenerateTitleResponse> => {
    const response = await api.post<GenerateTitleResponse>('/chat/generate-title', {
      chat_id: chatId,
      first_message: firstMessage,
    });
    return response.data;
  },

  healthCheck: async (): Promise<{ status: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// SnapTrade API
// ─────────────────────────────────────────────────────────────────────────────

export const snaptradeApi = {
  initiateConnection: async (userId: string, redirectUri: string): Promise<SnapTradeConnectionResponse> => {
    const response = await api.post<SnapTradeConnectionResponse>('/snaptrade/connect', {
      user_id: userId,
      redirect_uri: redirectUri,
    });
    return response.data;
  },

  connectBroker: async (userId: string, redirectUri: string, brokerId?: string): Promise<SnapTradeConnectionResponse> => {
    const response = await api.post<SnapTradeConnectionResponse>('/snaptrade/connect/broker', {
      user_id: userId,
      redirect_uri: redirectUri,
      broker_id: brokerId,
    });
    return response.data;
  },

  handleCallback: async (userId: string): Promise<SnapTradeStatusResponse> => {
    const response = await api.post<SnapTradeStatusResponse>('/snaptrade/callback', {
      user_id: userId,
    });
    return response.data;
  },

  checkStatus: async (userId: string): Promise<SnapTradeStatusResponse> => {
    const response = await api.get<SnapTradeStatusResponse>(`/snaptrade/status/${userId}`);
    return response.data;
  },

  getAccounts: async (userId: string): Promise<BrokerageAccountsResponse> => {
    const response = await api.get<BrokerageAccountsResponse>(`/snaptrade/accounts/${userId}`);
    return response.data;
  },

  getBrokerages: async (): Promise<BrokeragesResponse> => {
    const response = await api.get<BrokeragesResponse>('/snaptrade/brokerages');
    return response.data;
  },

  disconnectAccount: async (userId: string, accountId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete<{ success: boolean; message: string }>(
      `/snaptrade/accounts/${userId}/${accountId}`
    );
    return response.data;
  },

  disconnect: async (userId: string): Promise<void> => {
    await api.delete(`/snaptrade/disconnect/${userId}`);
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Resources API
// ─────────────────────────────────────────────────────────────────────────────

export const resourcesApi = {
  getChatResources: async (chatId: string, limit?: number): Promise<Resource[]> => {
    const response = await api.get<Resource[]>(`/resources/chat/${chatId}`, {
      params: { limit },
    });
    return response.data;
  },

  getUserResources: async (userId: string, limit?: number): Promise<Resource[]> => {
    const response = await api.get<Resource[]>(`/resources/user/${userId}`, {
      params: { limit },
    });
    return response.data;
  },

  getResource: async (resourceId: string): Promise<Resource> => {
    const response = await api.get<Resource>(`/resources/${resourceId}`);
    return response.data;
  },

  deleteResource: async (resourceId: string): Promise<void> => {
    await api.delete(`/resources/${resourceId}`);
  },
};

export default api;
