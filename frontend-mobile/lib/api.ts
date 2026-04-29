import axios from 'axios';
import { supabase } from './supabase';

export * from './types';

import type {
  ChatHistory,
  UserChatsResponse,
  GenerateTitleResponse,
  Resource,
  SnapTradeConnectionResponse,
  SnapTradeStatusResponse,
  BrokerageAccountsResponse,
  BrokeragesResponse,
  PortfolioResponse,
  PortfolioPerformance,
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
  SSEToolCallDetectedEvent,
  SSEToolCallStreamingEvent,
  SSEOptionsEvent,
  SSEDoneEvent,
  SSEErrorEvent,
  ToolCallStatus,
  ApiKeysResponse,
  ApiKeyResponse,
  TestApiKeyResponse,
  AlpacaPortfolioResponse,
  AlpacaOrder,
} from './types';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export async function getAuthHeader(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
}

api.interceptors.request.use(async (config) => {
  const authHeader = await getAuthHeader();
  if (authHeader.Authorization) {
    config.headers.Authorization = authHeader.Authorization;
  }
  return config;
});

// SSE Event Handlers Interface
export interface SSEEventHandlers {
  onMessageDelta?: (event: SSEAssistantMessageDeltaEvent) => void;
  onMessageEnd?: (event: SSEMessageEndEvent) => void;
  onToolCallDetected?: (event: SSEToolCallDetectedEvent) => void;
  onToolCallStart?: (event: SSEToolCallStartEvent) => void;
  onToolCallComplete?: (event: SSEToolCallCompleteEvent) => void;
  onToolsEnd?: () => void;
  onToolStatus?: (event: SSEToolStatusEvent) => void;
  onToolProgress?: (event: SSEToolProgressEvent) => void;
  onToolLog?: (event: SSEToolLogEvent) => void;
  onCodeOutput?: (event: SSECodeOutputEvent) => void;
  onFileContent?: (event: SSEFileContentEvent) => void;
  onToolCallStreaming?: (event: SSEToolCallStreamingEvent) => void;
  onTimeEstimate?: (event: { estimated_seconds: number; estimated_tools: number; description: string }) => void;
  onOptions?: (event: SSEOptionsEvent) => void;
  onDone?: (event: SSEDoneEvent) => void;
  onError?: (event: SSEErrorEvent) => void;
}

export const chatApi = {
  checkChatStatus: async (chatId: string): Promise<{ is_processing: boolean; last_activity: string }> => {
    try {
      const response = await api.get(`/chat/status/${chatId}`);
      return response.data;
    } catch {
      return { is_processing: false, last_activity: new Date().toISOString() };
    }
  },

  sendMessageStream: (
    message: string,
    userId: string,
    chatId: string,
    handlers: SSEEventHandlers,
    images?: ImageAttachment[],
    skills?: string[],
    investorPersona?: string
  ): { close: () => void } => {
    const url = `${API_BASE_URL}/chat/stream`;
    const abortController = new AbortController();

    const requestBody = {
      message,
      user_id: userId,
      chat_id: chatId,
      ...(images && images.length > 0 && { images }),
      ...(skills && skills.length > 0 && { skills }),
      ...(investorPersona && { investor_persona: investorPersona }),
    };

    let isClosed = false;

    const processEvent = (eventType: string, eventData: unknown) => {
      if (isClosed) return;
      switch (eventType) {
        case 'assistant_message_delta':
        case 'message_delta':
          handlers.onMessageDelta?.(eventData as SSEAssistantMessageDeltaEvent);
          break;
        case 'message_end':
          handlers.onMessageEnd?.(eventData as SSEMessageEndEvent);
          break;
        case 'tool_call_detected':
          handlers.onToolCallDetected?.(eventData as SSEToolCallDetectedEvent);
          break;
        case 'tool_call_start':
          handlers.onToolCallStart?.(eventData as SSEToolCallStartEvent);
          break;
        case 'tool_call_complete':
          handlers.onToolCallComplete?.(eventData as SSEToolCallCompleteEvent);
          break;
        case 'tools_end':
          handlers.onToolsEnd?.();
          break;
        case 'tool_status':
          handlers.onToolStatus?.(eventData as SSEToolStatusEvent);
          break;
        case 'tool_progress':
          handlers.onToolProgress?.(eventData as SSEToolProgressEvent);
          break;
        case 'tool_log':
          handlers.onToolLog?.(eventData as SSEToolLogEvent);
          break;
        case 'code_output':
          handlers.onCodeOutput?.(eventData as SSECodeOutputEvent);
          break;
        case 'file_content':
          handlers.onFileContent?.(eventData as SSEFileContentEvent);
          break;
        case 'tool_call_streaming':
          handlers.onToolCallStreaming?.(eventData as SSEToolCallStreamingEvent);
          break;
        case 'time_estimate':
          handlers.onTimeEstimate?.(eventData as { estimated_seconds: number; estimated_tools: number; description: string });
          break;
        case 'tool_options':
          handlers.onOptions?.(eventData as SSEOptionsEvent);
          break;
        case 'done':
          handlers.onDone?.(eventData as SSEDoneEvent);
          break;
        case 'error':
          handlers.onError?.(eventData as SSEErrorEvent);
          break;
      }
    };

    const startStream = async () => {
      const authHeader = await getAuthHeader();
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeader },
          body: JSON.stringify(requestBody),
          signal: abortController.signal,
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const reader = response.body?.getReader();
        if (!reader) throw new Error('Response body is null');

        const decoder = new TextDecoder();
        let buffer = '';

        while (!isClosed) {
          const { done, value } = await reader.read();
          if (done || isClosed) break;

          buffer += decoder.decode(value, { stream: true });

          while (true) {
            const eventEnd = buffer.indexOf('\n\n');
            if (eventEnd === -1) break;

            const eventStr = buffer.substring(0, eventEnd);
            buffer = buffer.substring(eventEnd + 2);

            if (!eventStr.trim()) continue;

            const eventMatch = eventStr.match(/event:\s*(\w+)/);
            const dataMatch = eventStr.match(/data:\s*([\s\S]+)/);

            if (eventMatch && dataMatch) {
              try {
                processEvent(eventMatch[1], JSON.parse(dataMatch[1]));
              } catch (e) {
                console.error('Error parsing SSE event:', e);
              }
            }
          }
        }

        reader.cancel().catch(() => {});
      } catch (error: any) {
        if (!isClosed && error.name !== 'AbortError') {
          handlers.onError?.({ error: error.message, timestamp: new Date().toISOString() });
        }
      }
    };

    startStream();

    return {
      close: () => {
        isClosed = true;
        abortController.abort();
      },
    };
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

  requestEmailNotification: async (chatId: string): Promise<void> => {
    await api.post(`/chat/${chatId}/notify-email`);
  },
};

export const alpacaBrokerApi = {
  getAccountStatus: async (userId: string) => {
    const response = await api.get(`/alpaca/broker/accounts/${userId}`);
    return response.data;
  },
  getPortfolio: async (userId: string) => {
    const response = await api.get(`/alpaca/broker/accounts/${userId}/portfolio`);
    return response.data as AlpacaPortfolioResponse;
  },
  placeOrder: async (userId: string, order: { symbol: string; side: string; qty?: number; notional?: number; order_type?: string; time_in_force?: string }) => {
    const response = await api.post(`/alpaca/broker/accounts/${userId}/orders`, { user_id: userId, ...order });
    return response.data;
  },
  getOrders: async (userId: string, status: string = 'all', limit: number = 50) => {
    const response = await api.get(`/alpaca/broker/accounts/${userId}/orders`, { params: { status, limit } });
    return response.data as AlpacaOrder[];
  },
  cancelOrder: async (userId: string, orderId: string) => {
    const response = await api.delete(`/alpaca/broker/accounts/${userId}/orders/${orderId}`);
    return response.data;
  },
};

export const marketApi = {
  getQuote: async (symbol: string) => {
    const response = await api.get(`/market/quote/${symbol}`);
    return response.data;
  },
  getBatchQuotes: async (symbols: string[]) => {
    const response = await api.get('/market/batch-quotes', { params: { symbols: symbols.join(',') } });
    return response.data;
  },
  getProfile: async (symbol: string) => {
    const response = await api.get(`/market/profile/${symbol}`);
    return response.data;
  },
  searchStocks: async (query: string, limit = 10) => {
    const response = await api.get('/market/search', { params: { q: query, limit } });
    return response.data;
  },
  getMovers: async () => {
    const response = await api.get('/market/movers');
    return response.data;
  },
  getNews: async (symbol: string, limit = 10) => {
    const response = await api.get(`/market/news/${symbol}`, { params: { limit } });
    return response.data;
  },
  getGeneralNews: async (limit = 10) => {
    const response = await api.get('/market/general-news', { params: { limit } });
    return response.data;
  },
};

export const watchlistApi = {
  getWatchlist: async (userId: string) => {
    const response = await api.get(`/watchlist/${userId}`);
    return response.data;
  },
  addSymbol: async (userId: string, symbol: string) => {
    const response = await api.post(`/watchlist/${userId}`, { symbol });
    return response.data;
  },
  removeSymbol: async (userId: string, symbol: string) => {
    const response = await api.delete(`/watchlist/${userId}/${symbol}`);
    return response.data;
  },
};

export const creditsApi = {
  getBalance: async (userId: string) => {
    const response = await api.get(`/credits/balance/${userId}`);
    return response.data;
  },
};

export default api;
