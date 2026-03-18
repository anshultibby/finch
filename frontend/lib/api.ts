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

// Add axios interceptor to automatically include Authorization header
api.interceptors.request.use(
  async (config) => {
    // Get the current session from Supabase
    const { data: { session } } = await supabase.auth.getSession();
    
    // If we have a session, add the access token to the Authorization header
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
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
  onToolCallStart?: (event: SSEToolCallStartEvent) => void;
  onToolCallComplete?: (event: SSEToolCallCompleteEvent) => void;
  onToolsEnd?: () => void;
  onToolStatus?: (event: SSEToolStatusEvent) => void;
  onToolProgress?: (event: SSEToolProgressEvent) => void;
  onToolLog?: (event: SSEToolLogEvent) => void;
  onCodeOutput?: (event: SSECodeOutputEvent) => void;
  onFileContent?: (event: SSEFileContentEvent) => void;
  onToolCallStreaming?: (event: SSEToolCallStreamingEvent) => void;
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
    skills?: string[]
  ): { close: () => void; reconnect: () => void } => {
    const url = new URL('/chat/stream', API_BASE_URL);
    const abortController = new AbortController();

    const requestBody = {
      message,
      user_id: userId,
      chat_id: chatId,
      ...(images && images.length > 0 && { images }),
      ...(skills && skills.length > 0 && { skills }),
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

    // Parse and process SSE lines from buffer
    const parseAndProcessEvents = (data: string): string => {
      const lines = data.split('\n\n');
      const remainingBuffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim() || isClosed) continue;

        const eventMatch = line.match(/event:\s*(\w+)/);
        const dataMatch = line.match(/data:\s*([\s\S]+)/);

        if (eventMatch && dataMatch) {
          try {
            const eventType = eventMatch[1];
            const eventData = JSON.parse(dataMatch[1]);
            processEvent(eventType, eventData);
          } catch (e) {
            console.error('Error parsing SSE event:', e);
          }
        }
      }

      return remainingBuffer;
    };

    // Main fetch stream handler
    const startStream = () => {
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
          isReconnecting = false;

          // Stream processing loop
          const processStream = async () => {
            try {
              while (!isClosed) {
                const { done, value } = await reader.read();
                if (done || isClosed) break;

                buffer += decoder.decode(value, { stream: true });
                
                // Process all complete events in the buffer
                // This handles cases where multiple events arrive at once
                buffer = parseAndProcessEvents(buffer);
                
                // Yield to the event loop to allow UI updates
                // This prevents blocking when processing many buffered events
                await new Promise(resolve => setTimeout(resolve, 0));
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
        .catch((error) => {
          if (!isClosed && error.name !== 'AbortError') {
            console.error('SSE stream error:', error);
            
            // Attempt to reconnect if not at max attempts
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS && !isReconnecting) {
              isReconnecting = true;
              reconnectAttempts++;
              console.log(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
              
              setTimeout(() => {
                if (!isClosed) {
                  startStream();
                }
              }, RECONNECT_DELAY * reconnectAttempts); // Exponential backoff
            } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
              handlers.onError?.({
                error: 'Connection lost. Please refresh to continue.',
                timestamp: new Date().toISOString(),
              });
            } else {
              handlers.onError?.({
                error: error.message,
                timestamp: new Date().toISOString(),
              });
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

  getPortfolio: async (userId: string): Promise<PortfolioResponse> => {
    const response = await api.get<PortfolioResponse>(`/snaptrade/portfolio/${userId}`);
    return response.data;
  },

  getPortfolioPerformance: async (userId: string): Promise<PortfolioPerformance> => {
    const response = await api.get<PortfolioPerformance>(`/snaptrade/portfolio/${userId}/performance`);
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

export default api;
