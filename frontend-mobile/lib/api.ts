import axios from 'axios';
import { supabase } from './supabase';

export * from './types';

import type {
  ChatHistory,
  UserChatsResponse,
  ModelOption,
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
  SSETodoUpdateEvent,
  SSEDoneEvent,
  SSEErrorEvent,
  FileAttachment,
  ToolCallStatus,
  ApiKeysResponse,
  ApiKeyResponse,
  TestApiKeyResponse,
  Visualization,
} from './types';

import { Platform } from 'react-native';

const API_BASE_URL = Platform.OS === 'web'
  ? 'http://localhost:8000'
  : (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000');

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
  onTodoUpdate?: (event: SSETodoUpdateEvent) => void;
  onThinkingDelta?: (event: { delta: string }) => void;
  onOptions?: (event: SSEOptionsEvent) => void;
  onDone?: (event: SSEDoneEvent) => void;
  onError?: (event: SSEErrorEvent) => void;
  /** Fired when a dropped stream finished server-side — reload history to show the result. */
  onStreamRecovered?: () => void;
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
    model?: string
  ): { close: () => void } => {
    const url = `${API_BASE_URL}/chat/stream`;
    const abortController = new AbortController();

    const requestBody = {
      message,
      user_id: userId,
      chat_id: chatId,
      ...(images && images.length > 0 && { images }),
      ...(skills && skills.length > 0 && { skills }),
      ...(model && { model }),
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
        case 'todo_update':
          handlers.onTodoUpdate?.(eventData as SSETodoUpdateEvent);
          break;
        case 'thinking_delta':
          handlers.onThinkingDelta?.(eventData as { delta: string });
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

            // Skip SSE comments (heartbeat keepalives from the server)
            if (eventStr.startsWith(':')) continue;

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
          // The connection dropped (flaky cellular, app backgrounded, …) but the
          // backend keeps processing. Poll status until it finishes, then let the
          // UI reload the completed result from history instead of erroring out.
          const POLL_INTERVAL = 3000;
          const MAX_POLLS = 100; // ~5 minutes
          for (let i = 0; i < MAX_POLLS && !isClosed; i++) {
            try {
              const status = await chatApi.checkChatStatus(chatId);
              if (!status.is_processing) {
                handlers.onStreamRecovered?.();
                handlers.onDone?.({ message: 'Stream recovered', timestamp: new Date().toISOString() });
                return;
              }
            } catch {
              // Status check failed — keep trying
            }
            await new Promise(r => setTimeout(r, POLL_INTERVAL));
          }
          if (!isClosed) {
            handlers.onError?.({ error: 'Connection lost. Pull to refresh to see the result.', timestamp: new Date().toISOString() });
          }
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

  getModels: async (): Promise<ModelOption[]> => {
    const response = await api.get<{ models: ModelOption[] }>('/chat/models');
    return response.data.models;
  },

  generateTitle: async (chatId: string, firstMessage: string): Promise<GenerateTitleResponse> => {
    const response = await api.post<GenerateTitleResponse>('/chat/generate-title', {
      chat_id: chatId,
      first_message: firstMessage,
    });
    return response.data;
  },

  renameChat: async (chatId: string, title: string): Promise<{ chat_id: string; title: string; icon: string | null }> => {
    const response = await api.patch(`/chat/${chatId}`, { title });
    return response.data;
  },

  deleteChat: async (chatId: string): Promise<{ deleted: boolean }> => {
    const response = await api.delete(`/chat/${chatId}`);
    return response.data;
  },

  shareChat: async (chatId: string): Promise<{ is_public: boolean; share_token: string | null }> => {
    const response = await api.post(`/chat/${chatId}/share`);
    return response.data;
  },

  requestEmailNotification: async (chatId: string): Promise<void> => {
    await api.post(`/chat/${chatId}/notify-email`);
  },

  submitFeedback: async (
    chatId: string,
    messageIndex: number,
    feedbackType: 'like' | 'dislike',
    comment?: string,
    messageContent?: string,
  ): Promise<void> => {
    await api.post(`/chat/${chatId}/feedback`, {
      message_index: messageIndex,
      feedback_type: feedbackType,
      comment,
      message_content: messageContent,
    });
  },
};

export const chatFilesApi = {
  /** Upload a document (PDF/CSV/…) to the user's sandbox so the agent can read it. */
  uploadFile: async (
    chatId: string,
    file: { uri: string; name: string; mimeType: string },
  ): Promise<FileAttachment> => {
    const formData = new FormData();
    // React Native FormData takes a {uri, name, type} descriptor instead of a Blob.
    formData.append('file', { uri: file.uri, name: file.name, type: file.mimeType } as any);
    const response = await api.post(`/api/chat-files/${chatId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    const d = response.data;
    return { name: d.filename, path: d.path, media_type: d.media_type };
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
  getGeneralNews: async (limit = 10, market = 'us') => {
    const response = await api.get('/market/general-news', { params: { limit, market } });
    return response.data;
  },
  getEarnings: async () => {
    const response = await api.get('/market/earnings');
    return response.data;
  },
  getPeers: async (symbol: string, limit = 6) => {
    const response = await api.get(`/market/peers/${symbol}`, { params: { limit } });
    return response.data;
  },
  getAnalyst: async (symbol: string) => {
    const response = await api.get(`/market/analyst/${symbol}`);
    return response.data;
  },
  getEarningsHistory: async (symbol: string, limit = 8) => {
    const response = await api.get(`/market/earnings-history/${symbol}`, { params: { limit } });
    return response.data;
  },
  getFinancials: async (symbol: string, statement = 'income-statement', period = 'annual', limit = 4) => {
    const response = await api.get(`/market/financials/${symbol}`, { params: { statement, period, limit } });
    return response.data;
  },
  getPrices: async (symbols: string[], days = 365) => {
    const response = await api.get('/market/prices', { params: { symbols: symbols.join(','), days } });
    return response.data;
  },
};

export const analysisApi = {
  getAll: async () => {
    const response = await api.get('/analysis');
    return response.data;
  },
  getBySymbol: async (symbol: string) => {
    const response = await api.get(`/analysis/${symbol}`);
    return response.data;
  },
};

export const apiKeysApi = {
  getKeys: async (userId: string) => {
    const response = await api.get(`/api-keys/${userId}`);
    return response.data;
  },
  saveKey: async (userId: string, service: string, credentials: Record<string, string>) => {
    const response = await api.post(`/api-keys/${userId}`, { service, credentials });
    return response.data;
  },
  deleteKey: async (userId: string, service: string) => {
    const response = await api.delete(`/api-keys/${userId}/${service}`);
    return response.data;
  },
  testKey: async (userId: string, service: string) => {
    const response = await api.post(`/api-keys/${userId}/test`, { service });
    return response.data;
  },
};

export const watchlistApi = {
  getLists: async (userId: string) => {
    const response = await api.get(`/watchlist/${userId}/lists`);
    return response.data;
  },
  createList: async (userId: string, name: string) => {
    const response = await api.post(`/watchlist/${userId}/lists`, { name });
    return response.data;
  },
  renameList: async (userId: string, listId: string, name: string) => {
    const response = await api.patch(`/watchlist/${userId}/lists/${listId}`, { name });
    return response.data;
  },
  deleteList: async (userId: string, listId: string) => {
    const response = await api.delete(`/watchlist/${userId}/lists/${listId}`);
    return response.data;
  },
  getWatchlist: async (userId: string, listId?: string) => {
    const params = listId ? `?list_id=${listId}` : '';
    const response = await api.get(`/watchlist/${userId}${params}`);
    return response.data;
  },
  addSymbol: async (userId: string, symbol: string, listId?: string) => {
    const response = await api.post(`/watchlist/${userId}`, { symbol, list_id: listId });
    return response.data;
  },
  removeSymbol: async (userId: string, symbol: string, listId?: string) => {
    const params = listId ? `?list_id=${listId}` : '';
    const response = await api.delete(`/watchlist/${userId}/${symbol}${params}`);
    return response.data;
  },
};

export const snaptradeApi = {
  getStatus: async (userId: string) => {
    const response = await api.get(`/snaptrade/status/${userId}`);
    return response.data as SnapTradeStatusResponse;
  },
  connect: async (userId: string, redirectUri: string) => {
    const response = await api.post('/snaptrade/connect', { user_id: userId, redirect_uri: redirectUri });
    return response.data as SnapTradeConnectionResponse;
  },
  connectBroker: async (userId: string, redirectUri: string, brokerId?: string) => {
    const response = await api.post('/snaptrade/connect/broker', { user_id: userId, redirect_uri: redirectUri, broker_id: brokerId });
    return response.data as SnapTradeConnectionResponse;
  },
  callback: async (userId: string) => {
    const response = await api.post('/snaptrade/callback', { user_id: userId });
    return response.data as SnapTradeStatusResponse;
  },
  getBrokerages: async () => {
    const response = await api.get('/snaptrade/brokerages');
    return response.data as { success: boolean; brokerages: Array<{ id: string; name: string; logo: string }>; message: string };
  },
  getAccounts: async (userId: string) => {
    const response = await api.get(`/snaptrade/accounts/${userId}`);
    return response.data as { success: boolean; accounts: Array<{ id: string; name: string; number: string; institution: string; type: string; balance: number }>; message: string };
  },
  deleteAccount: async (userId: string, accountId: string) => {
    const response = await api.delete(`/snaptrade/accounts/${userId}/${accountId}`);
    return response.data;
  },
  disconnect: async (userId: string) => {
    const response = await api.delete(`/snaptrade/disconnect/${userId}`);
    return response.data;
  },
  getPortfolio: async (userId: string) => {
    const response = await api.get(`/snaptrade/portfolio/${userId}`);
    return response.data as PortfolioResponse;
  },
  getPerformance: async (userId: string) => {
    const response = await api.get(`/snaptrade/portfolio/${userId}/performance`);
    return response.data as PortfolioPerformance;
  },
};

export const creditsApi = {
  getBalance: async (userId: string) => {
    const response = await api.get(`/credits/balance/${userId}`);
    return response.data;
  },
};

export interface UserPreferences {
  require_trade_approval: boolean;
  morning_brief_enabled: boolean;
  morning_brief_time: string;     // HH:MM (local)
  morning_brief_timezone: string; // IANA, e.g. Asia/Kolkata
  morning_brief_phone: string;    // E.164 WhatsApp number; empty disables WhatsApp
}

export const accountApi = {
  // Permanently delete the user's account (App Store Guideline 5.1.1(v)).
  deleteAccount: async (userId: string) => {
    const response = await api.delete(`/account/${userId}`);
    return response.data;
  },

  getPreferences: async (userId: string): Promise<UserPreferences> => {
    const response = await api.get(`/account/${userId}/preferences`);
    return response.data as UserPreferences;
  },

  updatePreferences: async (
    userId: string,
    updates: Partial<UserPreferences>
  ): Promise<UserPreferences> => {
    const response = await api.patch(`/account/${userId}/preferences`, updates);
    return response.data as UserPreferences;
  },
};

export const notificationsApi = {
  getNotifications: async (limit = 50, unreadOnly = false) => {
    const response = await api.get('/push/notifications', { params: { limit, unread_only: unreadOnly } });
    return response.data;
  },
  getUnreadCount: async () => {
    const response = await api.get('/push/notifications/count');
    return response.data;
  },
  markRead: async (notificationIds?: string[]) => {
    const response = await api.post('/push/notifications/read', { notification_ids: notificationIds || null });
    return response.data;
  },
};

export const visualizationsApi = {
  list: async (): Promise<{ visualizations: Visualization[] }> => {
    const response = await api.get('/api/visualizations');
    return response.data;
  },
  getRenderHtml: async (id: string): Promise<string> => {
    const response = await api.get(`/api/visualizations/${id}/render`, { responseType: 'text' });
    return response.data as string;
  },
};

// Robinhood agentic trading — native (on-device) loopback OAuth, then hand the
// code to the backend to exchange + store. See lib/robinhoodAuth.ts for the flow.
export const robinhoodApi = {
  nativeExchange: async (
    userId: string,
    params: { code: string; code_verifier: string; client_id: string; redirect_uri: string },
  ): Promise<{ success: boolean; is_connected: boolean }> => {
    const response = await api.post('/robinhood/native/exchange', { user_id: userId, ...params });
    return response.data;
  },
  checkStatus: async (userId: string): Promise<{ is_connected: boolean }> => {
    const response = await api.get(`/robinhood/status/${userId}`);
    return response.data;
  },
  disconnect: async (userId: string): Promise<{ success: boolean }> => {
    const response = await api.delete(`/robinhood/disconnect/${userId}`);
    return response.data;
  },
  getPortfolio: async (userId: string): Promise<RobinhoodPortfolioResponse> => {
    const response = await api.get(`/robinhood/portfolio/${userId}`);
    return response.data;
  },
};

export interface RobinhoodHolding {
  symbol: string;
  quantity: number;
  average_buy_price: number;
  last_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_pct: number;
  today_pct: number;
}
export interface RobinhoodOrder {
  side: string; symbol: string; quantity: string; price: string; at: string; state: string;
}
export interface RobinhoodPortfolioResponse {
  is_connected: boolean;
  agentic_account: { account_number: string } | null;
  total_value: string | null;
  buying_power: string | null;
  holdings: RobinhoodHolding[];
  orders: RobinhoodOrder[];
}

export default api;
