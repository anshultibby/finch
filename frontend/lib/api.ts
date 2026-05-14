// ═══════════════════════════════════════════════════════════════════════════
// API Client
// ═══════════════════════════════════════════════════════════════════════════

import axios from 'axios';
import { supabase } from './supabase';

// Re-export all types for backward compatibility
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
  FileAttachment,
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
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Fetch the current Supabase access token (or null if unauthenticated).
// Exported so raw `fetch` callers (e.g. SSE streams) can attach the same
// Authorization header that the axios interceptor adds.
export async function getAuthHeader(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
}

// Add axios interceptor to automatically include Authorization header
api.interceptors.request.use(
  async (config) => {
    const authHeader = await getAuthHeader();
    if (authHeader.Authorization) {
      config.headers.Authorization = authHeader.Authorization;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// SSE Event Handlers Interface
// ─────────────────────────────────────────────────────────────────────────────

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

// ─────────────────────────────────────────────────────────────────────────────
// Chat API
// ─────────────────────────────────────────────────────────────────────────────

export const chatApi = {
  // Check if a chat is currently being processed on the backend
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
    pageContext?: Record<string, any>
  ): { close: () => void; reconnect: () => void } => {
    const url = new URL('/chat/stream', API_BASE_URL);
    const abortController = new AbortController();

    const requestBody = {
      message,
      user_id: userId,
      chat_id: chatId,
      ...(images && images.length > 0 && { images }),
      ...(skills && skills.length > 0 && { skills }),
      ...(pageContext && { page_context: pageContext }),
    };

    // Track if we're closed to prevent processing after abort
    let isClosed = false;
    let isReconnecting = false;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 3;
    const RECONNECT_DELAY = 2000; // 2 seconds

    // Process a single SSE event - extracted for reuse
    const processEvent = (eventType: string, eventData: unknown) => {
      if (isClosed) return;
      
      // Reset reconnect attempts on successful event
      reconnectAttempts = 0;
      
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
        case 'thinking':
          // Informational - ignore
          break;
      }
    };

    // Events that need a React render yield so intermediate UI states are visible
    const YIELD_AFTER_EVENTS = new Set([
      'tool_call_detected', 'tool_call_start', 'tool_call_complete', 'tools_end', 'message_end', 'done'
    ]);

    // Parse and process SSE events from buffer one at a time.
    // Yields to the event loop after tool-related events so React can render
    // intermediate states (e.g., tool "calling" spinner) before the next event.
    const parseAndProcessEvents = async (data: string): Promise<string> => {
      let buffer = data;

      while (!isClosed) {
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
            const eventType = eventMatch[1];
            const eventData = JSON.parse(dataMatch[1]);
            processEvent(eventType, eventData);

            // Yield to the event loop after significant events so React
            // can render the updated state before we process the next event.
            if (YIELD_AFTER_EVENTS.has(eventType)) {
              await new Promise(resolve => setTimeout(resolve, 0));
            }
          } catch (e) {
            console.error('Error parsing SSE event:', e);
          }
        }
      }

      return buffer;
    };

    // Main fetch stream handler
    const startStream = async () => {
      const authHeader = await getAuthHeader();
      fetch(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader },
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
          isReconnecting = false;

          // Stream processing loop
          const processStream = async () => {
            try {
              while (!isClosed) {
                const { done, value } = await reader.read();
                if (done || isClosed) break;

                buffer += decoder.decode(value, { stream: true });

                // Process events one at a time, yielding to React between
                // tool-related events so intermediate UI states are visible
                buffer = await parseAndProcessEvents(buffer);
              }
            } catch (error) {
              if (!isClosed && (error as Error).name !== 'AbortError') {
                throw error;
              }
            } finally {
              // Always cancel the reader when done to free resources
              reader.cancel().catch(() => {});
            }
          };

          await processStream();
        })
        .catch(async (error) => {
          if (!isClosed && error.name !== 'AbortError') {
            console.error('SSE stream error:', error);

            // Instead of re-sending the message, poll the backend to see if the
            // chat is still being processed.  When processing finishes, fire the
            // done handler so the UI loads the completed result from history.
            if (!isReconnecting) {
              isReconnecting = true;
              console.log('Stream disconnected — polling backend for completion...');

              const pollForCompletion = async () => {
                const POLL_INTERVAL = 3000;
                const MAX_POLLS = 60; // 3 minutes max
                for (let i = 0; i < MAX_POLLS && !isClosed; i++) {
                  try {
                    const status = await chatApi.checkChatStatus(chatId);
                    if (!status.is_processing) {
                      console.log('Backend finished processing — triggering history reload');
                      // Signal that a disconnected stream completed — ChatView
                      // listens for this and reloads messages from the backend.
                      window.dispatchEvent(new CustomEvent('chat:stream-recovered', { detail: chatId }));
                      handlers.onDone?.({ message: 'Stream recovered', timestamp: new Date().toISOString() });
                      return;
                    }
                  } catch {
                    // Status check failed — keep trying
                  }
                  await new Promise(r => setTimeout(r, POLL_INTERVAL));
                }
                // Timed out waiting
                handlers.onError?.({
                  error: 'Connection lost. Please refresh to continue.',
                  timestamp: new Date().toISOString(),
                });
              };

              pollForCompletion();
            }
          }
        });
    };

    // Start the initial stream
    startStream();

    return {
      close: () => {
        isClosed = true;
        abortController.abort();
      },
      reconnect: () => {
        if (!isClosed && !isReconnecting) {
          console.log('Manual reconnect requested');
          reconnectAttempts = 0;
          startStream();
        }
      },
    };
  },

  getChatHistory: async (chatId: string): Promise<ChatHistory> => {
    const response = await api.get<ChatHistory>(`/chat/history/${chatId}`);
    return response.data;
  },

  getChatHistoryForDisplay: async (chatId: string, options?: { limit?: number; before_sequence?: number }): Promise<{
    chat_id: string;
    has_more: boolean;
    oldest_sequence: number | null;
    messages: Array<{
      role: 'user' | 'assistant';
      content: string;
      timestamp?: string;
      tool_calls?: ToolCallStatus[];
    }>;
  }> => {
    const params: Record<string, string> = {};
    if (options?.limit) params.limit = String(options.limit);
    if (options?.before_sequence) params.before_sequence = String(options.before_sequence);
    const response = await api.get(`/chat/history/${chatId}/display`, { params });
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

  requestEmailNotification: async (chatId: string): Promise<void> => {
    await api.post(`/chat/${chatId}/notify-email`);
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

  reset: async (userId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete<{ success: boolean; message: string }>(`/snaptrade/reset/${userId}`);
    return response.data;
  },

  getPortfolio: async (userId: string): Promise<PortfolioResponse> => {
    const response = await api.get<PortfolioResponse>(`/snaptrade/portfolio/${userId}`);
    return response.data;
  },

  getPortfolioPerformance: async (userId: string): Promise<PortfolioPerformance> => {
    const response = await api.get<PortfolioPerformance>(`/snaptrade/portfolio/${userId}/performance`);
    return response.data;
  },

  getPortfolioHistory: async (userId: string, startDate?: string, endDate?: string, accountId?: string): Promise<{ success: boolean; equity_series: Array<{ date: string; value: number }>; message?: string }> => {
    const params = new URLSearchParams();
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    if (accountId) params.set('account_id', accountId);
    const response = await api.get(`/snaptrade/portfolio/${userId}/history?${params.toString()}`);
    return response.data;
  },

  getPortfolioIntraday: async (userId: string, accountId?: string, days: number = 7): Promise<{ success: boolean; equity_series: Array<{ date: string; value: number }>; message?: string }> => {
    const params = new URLSearchParams({ days: String(days) });
    if (accountId) params.set('account_id', accountId);
    const response = await api.get(`/snaptrade/portfolio/${userId}/intraday?${params.toString()}`);
    return response.data;
  },

  buildPortfolioHistory: async (userId: string, accountId?: string, force = false): Promise<{ success: boolean; equity_series?: Array<{ date: string; value: number }>; intraday_series?: Array<{ date: string; value: number }>; snapshots_saved?: number; cached?: boolean; message?: string }> => {
    const params = new URLSearchParams();
    if (accountId) params.set('account_id', accountId);
    if (force) params.set('force', 'true');
    const response = await api.post(`/snaptrade/portfolio/${userId}/build-history?${params.toString()}`);
    return response.data;
  },

  clearPortfolioCache: async (userId: string): Promise<{ success: boolean; snapshots_deleted: number; intraday_deleted: number }> => {
    const response = await api.delete(`/snaptrade/portfolio/${userId}/cache`);
    return response.data;
  },

  toggleAccountVisibility: async (userId: string, accountId: string, isVisible: boolean): Promise<{ success: boolean; message: string }> => {
    const response = await api.patch<{ success: boolean; message: string }>(
      `/snaptrade/accounts/${userId}/${accountId}/visibility`,
      { is_visible: isVisible }
    );
    return response.data;
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

// ─────────────────────────────────────────────────────────────────────────────
// API Keys API
// ─────────────────────────────────────────────────────────────────────────────

export const apiKeysApi = {
  getApiKeys: async (userId: string): Promise<ApiKeysResponse> => {
    const response = await api.get<ApiKeysResponse>(`/api-keys/${userId}`);
    return response.data;
  },

  saveApiKey: async (
    userId: string,
    service: string,
    credentials: Record<string, string>
  ): Promise<ApiKeyResponse> => {
    const response = await api.post<ApiKeyResponse>(`/api-keys/${userId}`, {
      service,
      credentials,
    });
    return response.data;
  },

  deleteApiKey: async (userId: string, service: string): Promise<ApiKeyResponse> => {
    const response = await api.delete<ApiKeyResponse>(`/api-keys/${userId}/${service}`);
    return response.data;
  },

  testApiKey: async (userId: string, service: string): Promise<TestApiKeyResponse> => {
    const response = await api.post<TestApiKeyResponse>(`/api-keys/${userId}/test`, {
      service,
    });
    return response.data;
  },

  testCredentialsBeforeSave: async (
    userId: string,
    service: string,
    credentials: Record<string, string>
  ): Promise<TestApiKeyResponse> => {
    const response = await api.post<TestApiKeyResponse>(`/api-keys/${userId}/test-credentials`, {
      service,
      credentials,
    });
    return response.data;
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Alpaca Broker API
// ─────────────────────────────────────────────────────────────────────────────

export const alpacaBrokerApi = {
  createAccount: async (data: Record<string, unknown>): Promise<{ success: boolean; status: string; alpaca_account_id?: string }> => {
    const response = await api.post('/alpaca/broker/accounts', data);
    return response.data;
  },
  getAccountStatus: async (userId: string): Promise<{ exists: boolean; status?: string; alpaca_account_id?: string; action_required_reason?: string }> => {
    const response = await api.get(`/alpaca/broker/accounts/${userId}`);
    return response.data;
  },
  getPortfolio: async (userId: string) => {
    const response = await api.get(`/alpaca/broker/accounts/${userId}/portfolio`);
    return response.data as import('./types').AlpacaPortfolioResponse;
  },
  placeOrder: async (userId: string, order: { symbol: string; side: string; qty?: number; notional?: number; order_type?: string; time_in_force?: string; limit_price?: number; stop_price?: number }) => {
    const response = await api.post(`/alpaca/broker/accounts/${userId}/orders`, { user_id: userId, ...order });
    return response.data;
  },
  getOrders: async (userId: string, status: string = 'all', limit: number = 50) => {
    const response = await api.get(`/alpaca/broker/accounts/${userId}/orders`, { params: { status, limit } });
    return response.data as import('./types').AlpacaOrder[];
  },
  cancelOrder: async (userId: string, orderId: string) => {
    const response = await api.delete(`/alpaca/broker/accounts/${userId}/orders/${orderId}`);
    return response.data;
  },
  closePosition: async (userId: string, symbol: string) => {
    const response = await api.delete(`/alpaca/broker/accounts/${userId}/positions/${symbol}`);
    return response.data;
  },
  executeSwap: async (data: { user_id: string; account_id: string; sell_symbol: string; sell_qty: number; buy_symbol: string; buy_notional: number }): Promise<{ success: boolean; message: string; sell_order?: unknown; buy_order?: unknown }> => {
    const response = await api.post('/execute/swap', data);
    return response.data;
  },
  executeBrokerSwap: async (data: { user_id: string; alpaca_account_id: string; sell_symbol: string; sell_qty: number; buy_symbol: string; buy_notional: number }): Promise<{ success: boolean; message: string; sell_order?: unknown; buy_order?: unknown }> => {
    const response = await api.post('/alpaca/broker/orders/swap', data);
    return response.data;
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Credits API
// ─────────────────────────────────────────────────────────────────────────────

export interface CreditBalance {
  user_id: string;
  credits: number;
  total_credits_used: number;
}

export interface CreditTransaction {
  id: string;
  amount: number;
  balance_after: number;
  transaction_type: string;
  description: string;
  chat_id?: string;
  tool_name?: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
}

export interface CreditHistoryResponse {
  user_id: string;
  transactions: CreditTransaction[];
  count: number;
}

export interface CreditRequestData {
  user_id: string;
  user_email: string;
  requested_credits: number;
  reason: string;
  current_balance: number;
  total_used: number;
}

export const creditsApi = {
  getBalance: async (userId: string): Promise<CreditBalance> => {
    const response = await api.get<CreditBalance>(`/credits/balance/${userId}`);
    return response.data;
  },

  getHistory: async (userId: string, limit: number = 50): Promise<CreditHistoryResponse> => {
    const response = await api.get<CreditHistoryResponse>(`/credits/history/${userId}`, {
      params: { limit },
    });
    return response.data;
  },

  requestCredits: async (requestData: CreditRequestData): Promise<{ success: boolean; message: string }> => {
    const response = await api.post<{ success: boolean; message: string }>('/credits/request', requestData);
    return response.data;
  },

  getPricing: async (): Promise<{
    credits_per_dollar: number;
    premium_multiplier: number;
    info: string;
    model_pricing: Record<string, unknown>;
  }> => {
    const response = await api.get('/credits/pricing');
    return response.data;
  },

  redeemCode: async (code: string): Promise<{ success: boolean; plan: string; credits_added: number; message: string }> => {
    const response = await api.post('/credits/redeem', { code });
    return response.data;
  },

  createCheckout: async (userId: string): Promise<{ url: string; session_id: string }> => {
    const response = await api.post<{ url: string; session_id: string }>('/credits/checkout', {
      user_id: userId,
      success_url: `${window.location.origin}?upgraded=true`,
      cancel_url: window.location.href,
    });
    return response.data;
  },
};

export interface SkillFile {
  filename: string;
  file_type: string | null;
  content: string;
}

/** A skill from disk merged with the current user's enabled state */
export interface CatalogSkill {
  name: string;
  description: string;
  content: string;      // SKILL.md body (without frontmatter)
  emoji: string | null;
  homepage: string | null;
  category: string | null;
  is_system: boolean;
  files: SkillFile[];
  enabled: boolean;
}

// ============================================================================
// Trading Bots API
// ============================================================================

export const botsApi = {
  async listBots(userId: string) {
    const response = await fetch(`${API_BASE_URL}/bots`, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) throw new Error('Failed to list bots');
    return response.json();
  },

  async getBot(userId: string, botId: string) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}`, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) throw new Error('Failed to get bot');
    return response.json();
  },

  async createBot(userId: string, data: { name?: string; platform?: string; icon?: string; capital_amount?: number }) {
    const response = await fetch(`${API_BASE_URL}/bots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-User-ID': userId },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create bot');
    return response.json();
  },

  async updateBot(userId: string, botId: string, data: Record<string, any>) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-User-ID': userId },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update bot');
    return response.json();
  },

  async deleteBot(userId: string, botId: string) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}`, {
      method: 'DELETE',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) throw new Error('Failed to delete bot');
    return response.json();
  },

  async adjustCapital(userId: string, botId: string, amount: number) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/capital`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-User-ID': userId },
      body: JSON.stringify({ amount }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || 'Failed to adjust capital');
    }
    return response.json();
  },

  async listExecutions(userId: string, botId: string, limit: number = 20) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/executions?limit=${limit}`, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) return [];
    return response.json();
  },

  async listPositions(userId: string, botId: string, status?: string) {
    const url = status
      ? `${API_BASE_URL}/bots/${botId}/positions?status=${status}`
      : `${API_BASE_URL}/bots/${botId}/positions`;
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) return [];
    return response.json();
  },

  async closePosition(userId: string, botId: string, positionId: string) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/positions/${positionId}/close`, {
      method: 'POST',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) throw new Error('Failed to close position');
    return response.json();
  },

  async deleteBotFiles(userId: string, botId: string, fileType?: string) {
    const params = fileType ? `?file_type=${fileType}` : '';
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/files${params}`, {
      method: 'DELETE',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) throw new Error('Failed to delete bot files');
    return response.json();
  },

  async listSandboxFiles(userId: string, botId: string, path: string = '') {
    const params = path ? `?path=${encodeURIComponent(path)}` : '';
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/sandbox/files${params}`, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) return { files: [] };
    return response.json();
  },

  async readSandboxFile(userId: string, botId: string, path: string) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/sandbox/files/read?path=${encodeURIComponent(path)}`, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) return null;
    return response.json();
  },

  downloadSandboxFileUrl(userId: string, botId: string, path: string) {
    return `${API_BASE_URL}/bots/${botId}/sandbox/files/download?path=${encodeURIComponent(path)}`;
  },

  downloadAllSandboxFilesUrl(userId: string, botId: string, path: string = '') {
    const params = path ? `?path=${encodeURIComponent(path)}` : '';
    return `${API_BASE_URL}/bots/${botId}/sandbox/files/download-all${params}`;
  },

  async listBotChats(userId: string, botId: string) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/chats`, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) return [];
    return response.json();
  },

  async createBotChat(userId: string, botId: string) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/chats`, {
      method: 'POST',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) throw new Error('Failed to create bot chat');
    return response.json();
  },

  async getPositionMarket(userId: string, botId: string, positionId: string) {
    const response = await fetch(
      `${API_BASE_URL}/bots/${botId}/positions/${positionId}/market`,
      { method: 'GET', headers: { 'X-User-ID': userId } },
    );
    if (!response.ok) return null;
    const data = await response.json();
    return data.market ?? null;
  },

  async getPositionCandlesticks(
    userId: string,
    botId: string,
    positionId: string,
    periodInterval: 1 | 60 | 1440 = 60,
    hours: number = 168,
  ) {
    const response = await fetch(
      `${API_BASE_URL}/bots/${botId}/positions/${positionId}/candlesticks?period_interval=${periodInterval}&hours=${hours}`,
      { method: 'GET', headers: { 'X-User-ID': userId } },
    );
    if (!response.ok) return [];
    const data = await response.json();
    return data.history ?? [];
  },

  async listWakeups(userId: string, botId: string, status: string = 'pending') {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/wakeups?status=${status}`, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) return [];
    return response.json();
  },

  async cancelWakeup(userId: string, botId: string, wakeupId: string) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/wakeups/${wakeupId}`, {
      method: 'DELETE',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) throw new Error('Failed to cancel wakeup');
    return response.json();
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Trade Logs API
// ─────────────────────────────────────────────────────────────────────────────

export const tradesApi = {
  /** List all trades across all bots */
  async listAll(userId: string, limit: number = 50) {
    const response = await fetch(`${API_BASE_URL}/trades?limit=${limit}`, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) return [];
    return response.json();
  },

  /** List trades for a specific bot */
  async listForBot(userId: string, botId: string, limit: number = 50) {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/trades?limit=${limit}`, {
      method: 'GET',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) return [];
    return response.json();
  },

  /** Approve a pending trade (executes it on the exchange) */
  async approve(userId: string, tradeId: string) {
    const response = await fetch(`${API_BASE_URL}/trades/${tradeId}/approve`, {
      method: 'POST',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) throw new Error('Failed to approve trade');
    return response.json();
  },

  /** Reject a pending trade */
  async reject(userId: string, tradeId: string) {
    const response = await fetch(`${API_BASE_URL}/trades/${tradeId}/reject`, {
      method: 'POST',
      headers: { 'X-User-ID': userId },
    });
    if (!response.ok) throw new Error('Failed to reject trade');
    return response.json();
  },
};

export const skillsApi = {
  async listCatalog(userId: string): Promise<CatalogSkill[]> {
    const response = await fetch(`${API_BASE_URL}/skills/catalog?user_id=${userId}`);
    return response.json();
  },

  async toggleCatalogSkill(userId: string, skillName: string, enabled: boolean): Promise<CatalogSkill> {
    const response = await fetch(
      `${API_BASE_URL}/skills/catalog/${skillName}/toggle?user_id=${userId}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      }
    );
    return response.json();
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Analytics / Transactions API
// ─────────────────────────────────────────────────────────────────────────────

export const analyticsApi = {
  async getTransactions(userId: string, symbol?: string, limit: number = 200) {
    const params = new URLSearchParams({ user_id: userId, limit: String(limit) });
    if (symbol) params.set('symbol', symbol);
    const auth = await getAuthHeader();
    const response = await fetch(`${API_BASE_URL}/api/analytics/transactions?${params}`, {
      headers: { 'X-User-ID': userId, ...auth },
    });
    if (!response.ok) return { transactions: [], count: 0 };
    return response.json() as Promise<{ transactions: import('./types').StockTransaction[]; count: number }>;
  },

  async syncTransactions(userId: string) {
    const auth = await getAuthHeader();
    const response = await fetch(`${API_BASE_URL}/api/analytics/transactions/sync?user_id=${userId}`, {
      method: 'POST',
      headers: { 'X-User-ID': userId, ...auth },
    });
    if (!response.ok) return { success: false };
    return response.json();
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Chat Files API
// ─────────────────────────────────────────────────────────────────────────────

export const chatFilesApi = {
  /** Upload a file to the user's sandbox. Returns {filename, path, size_bytes, media_type}. */
  uploadFile: async (chatId: string, file: File, destDir?: string): Promise<FileAttachment> => {
    const formData = new FormData();
    formData.append('file', file);
    if (destDir) formData.append('dest_dir', destDir);

    const response = await api.post(`/api/chat-files/${chatId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    const d = response.data;
    return { name: d.filename, path: d.path, media_type: d.media_type };
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Market Data API
// ─────────────────────────────────────────────────────────────────────────────

export const marketApi = {
  getQuote: async (symbol: string) => {
    const response = await api.get(`/market/quote/${symbol}`);
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
  getPeers: async (symbol: string, limit = 6) => {
    const response = await api.get(`/market/peers/${symbol}`, { params: { limit } });
    return response.data;
  },
  getGeneralNews: async (limit = 10) => {
    const response = await api.get('/market/general-news', { params: { limit } });
    return response.data;
  },
  getEarnings: async (fromDate?: string, toDate?: string, market?: string) => {
    const params: Record<string, string> = {};
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    if (market) params.market = market;
    const response = await api.get('/market/earnings', { params });
    return response.data;
  },
  getBatchQuotes: async (symbols: string[]) => {
    if (!symbols.length) return [];
    const response = await api.get('/market/batch-quote', { params: { symbols: symbols.join(',') } });
    return response.data;
  },
  getAnalyst: async (symbol: string) => {
    const response = await api.get(`/market/analyst/${symbol}`);
    return response.data;
  },
  getEarningsHistory: async (symbol: string, limit = 12) => {
    const response = await api.get(`/market/earnings-history/${symbol}`, { params: { limit } });
    return response.data;
  },
  getEarningsTranscript: async (symbol: string, quarter: number, year: number) => {
    const response = await api.get(`/market/earnings-transcript/${symbol}`, { params: { quarter, year } });
    return response.data;
  },
  getSecFilings: async (symbol: string, type?: string, limit = 20) => {
    const params: Record<string, any> = { limit };
    if (type) params.type = type;
    const response = await api.get(`/market/sec-filings/${symbol}`, { params });
    return response.data;
  },
  getFinancials: async (symbol: string, statement = 'income-statement', period = 'annual', limit = 6) => {
    const response = await api.get(`/market/financials/${symbol}`, { params: { statement, period, limit } });
    return response.data;
  },
  getSecCitation: async (filingUrl: string, field: string): Promise<{ anchor_id: string | null; url: string }> => {
    const response = await api.get('/market/sec-citation', { params: { filing_url: filingUrl, field } });
    return response.data;
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Watchlist API
// ─────────────────────────────────────────────────────────────────────────────

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

// ─────────────────────────────────────────────────────────────────────────────
// Stock Analysis API
// ─────────────────────────────────────────────────────────────────────────────

export const analysisApi = {
  list: async () => {
    const response = await api.get('/analysis');
    return response.data;
  },
  get: async (symbol: string) => {
    const response = await api.get(`/analysis/${symbol}`);
    return response.data;
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Visualizations API
// ─────────────────────────────────────────────────────────────────────────────

export const visualizationsApi = {
  list: async () => {
    const response = await api.get('/api/visualizations');
    return response.data;
  },
  get: async (id: string) => {
    const response = await api.get(`/api/visualizations/${id}`);
    return response.data;
  },
  getRenderHtml: async (id: string) => {
    const response = await api.get(`/api/visualizations/${id}/render`, { responseType: 'text' });
    return response.data as string;
  },
  update: async (id: string, data: { title?: string; description?: string; category?: string; tags?: string[] }) => {
    const response = await api.patch(`/api/visualizations/${id}`, data);
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/api/visualizations/${id}`);
    return response.data;
  },
  runScript: async (script: string) => {
    const response = await api.post('/api/visualizations/run-script', { script });
    return response.data;
  },
  toggleShare: async (id: string) => {
    const response = await api.post(`/api/visualizations/${id}/share`);
    return response.data as { is_public: boolean; share_token: string | null };
  },
  getShared: async (shareToken: string) => {
    const response = await api.get(`/api/visualizations/shared/${shareToken}`);
    return response.data;
  },
  getSharedHtml: async (shareToken: string) => {
    const response = await api.get(`/api/visualizations/shared/${shareToken}/render`, { responseType: 'text' });
    return response.data as string;
  },
};

export default api;
