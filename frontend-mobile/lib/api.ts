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
  Widget,
  WidgetSummary,
  WidgetSpec,
  WidgetData,
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
  onCitationsFinalized?: (event: { content: string; dropped: number[] }) => void;
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
        case 'citations_finalized':
          handlers.onCitationsFinalized?.(eventData as { content: string; dropped: number[] });
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
      reasoning?: string | null;
    }>;
  }> => {
    const response = await api.get(`/chat/history/${chatId}/display`);
    return response.data;
  },

  getUserChats: async (userId: string, opts?: { source?: 'user' | 'automation' | 'all' }): Promise<UserChatsResponse> => {
    const qs = opts?.source ? `?source=${opts.source}` : '';
    const response = await api.get<UserChatsResponse>(`/chat/user/${userId}/chats${qs}`);
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

  // Fetch the raw payload behind a citation ([^N]) — the data a claim is grounded
  // in. Rejects (404) when no stored result exists (e.g. sub-agent results).
  getToolResult: async (chatId: string, toolCallId: string): Promise<{ tool_call_id: string; tool_name: string; content: string }> => {
    const response = await api.get(`/chat/history/${chatId}/tool-result/${encodeURIComponent(toolCallId)}`);
    return response.data;
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
  getEarnings: async (fromDate?: string, toDate?: string, market?: string) => {
    const params: Record<string, string> = {};
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    if (market) params.market = market;
    const response = await api.get('/market/earnings', { params });
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
  screen: async (filters: ScreenerFilters, limit = 30): Promise<ScreenerResult[]> => {
    const response = await api.get('/market/screener', { params: { ...filters, limit } });
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

// ─────────────────────────────────────────────────────────────────────────────
// Tasks API — the agent's long-running work, one markdown file per task.
// Read-only: the file in the sandbox is the source of truth, so the way to
// change a task is to ask the agent, not to POST here.
// ─────────────────────────────────────────────────────────────────────────────

export type TaskStatus = 'open' | 'blocked' | 'done' | 'dropped';

export interface AgentTask {
  id: string;
  slug: string;
  title: string;
  status: TaskStatus;
  symbols: string[];
  opened_on: string | null;
  review_on: string | null;
  chat_id: string | null;
  /** True when Finch opened this on its own (from an automation run), not from a chat. */
  is_autonomous: boolean;
  updated_at: string | null;
  /** Only present on the detail fetch. */
  body?: string;
}

export interface TaskListResponse {
  tasks: AgentTask[];
  counts: Record<TaskStatus, number>;
}

export const tasksApi = {
  list: async (params?: { status?: TaskStatus; due_by?: string; symbol?: string; origin?: 'automation' | 'chat' }): Promise<TaskListResponse> =>
    (await api.get('/tasks', { params })).data,
  get: async (slug: string): Promise<AgentTask> => (await api.get(`/tasks/${slug}`)).data,
};

// Insights — instant AI intelligence (why-is-it-moving, portfolio digest)
export interface MoveExplanation {
  symbol: string;
  name: string;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  explanation: string;
  // Finch's read of the move (backend move_context.FRAMEWORK). Optional so an
  // older backend still renders.
  verdict?: MoveVerdict;
  driver?: MoveDriver;
  headline?: string;
  watch?: string;
  context?: MoveContext;
  sources: { title: string; site: string; url: string; publishedDate: string }[];
  cached: boolean;
}

export type MoveVerdict = 'noise' | 'news' | 'narrative_shift';
export type MoveDriver = 'macro' | 'sector' | 'company';

/** Measured inputs behind a verdict — computed, not model-generated. */
export interface MoveContext {
  typical_move_pct: number | null;
  move_multiple: number | null;
  sector: string | null;
  sector_etf: string | null;
  sector_change_pct: number | null;
  spy_change_pct: number | null;
  idiosyncratic_pct: number | null;
  volume_ratio: number | null;
  earnings: string | null;
}

export const VERDICT_META: Record<MoveVerdict, { label: string; fg: string; bg: string }> = {
  noise: { label: 'Routine', fg: '#57534e', bg: '#f5f5f4' },
  news: { label: 'News · story intact', fg: '#1d4ed8', bg: '#eff6ff' },
  narrative_shift: { label: 'Story change', fg: '#b45309', bg: '#fffbeb' },
};

export const DRIVER_LABEL: Record<MoveDriver, string> = {
  macro: 'Macro-driven',
  sector: 'Sector-driven',
  company: 'Company-specific',
};

export interface DigestMover {
  symbol: string;
  name: string;
  change_pct: number;
  change: number;
  contribution: number;
  value: number;
}

export interface PortfolioDigest {
  success: boolean;
  mode: 'portfolio' | 'watchlist' | 'empty';
  total_value?: number;
  day_change?: number;
  day_change_pct?: number;
  movers?: DigestMover[];
  narrative?: string;
  generated_at?: string;
}

export const insightsApi = {
  whyIsItMoving: async (symbol: string): Promise<MoveExplanation> => {
    const response = await api.get(`/insights/why/${symbol}`);
    return response.data;
  },
  getPortfolioDigest: async (userId: string): Promise<PortfolioDigest> => {
    const response = await api.get(`/insights/portfolio-digest/${userId}`);
    return response.data;
  },
};

// ── Agent activity — the agent's ledger + "while you were gone" recap ───────

export interface AgentEvent {
  id: string;
  event_type: 'job_run' | 'alert' | 'trade_proposed' | 'trade_decided' | 'brief' | 'insight';
  source: string | null;
  title: string;
  body: string | null;
  data: Record<string, unknown>;
  value_cents: number | null;
  created_at: string;
}

export interface PendingTradeItem {
  id: string;
  summary: string | null;
  order_params: Record<string, unknown>;
  broker: string;
  expires_at: string | null;
  created_at: string | null;
}

export interface ActivityRecap {
  since: string;
  last_seen_at: string | null;
  headline: string | null;
  counts: Record<string, number>;
  events: AgentEvent[];
  pending_trades: PendingTradeItem[];
  next_run: { name: string; run_at: string | null; system_key: string | null } | null;
  running_now: { name: string; started_at: string | null; chat_id: string | null } | null;
  has_content: boolean;
}

export const activityApi = {
  getRecap: async (): Promise<ActivityRecap> => {
    const response = await api.get('/activity/recap');
    return response.data;
  },
  getFeed: async (limit = 50, before?: string): Promise<{ events: AgentEvent[] }> => {
    const response = await api.get('/activity', { params: { limit, before } });
    return response.data;
  },
  markSeen: async (): Promise<void> => {
    await api.post('/activity/seen');
  },
};

export const pendingTradesApi = {
  list: async (): Promise<{ pending_trades: PendingTradeItem[] }> => {
    const response = await api.get('/trades/pending');
    return response.data;
  },
  approve: async (tradeId: string) => {
    const response = await api.post(`/trades/pending/${tradeId}/approve`);
    return response.data;
  },
  reject: async (tradeId: string) => {
    const response = await api.post(`/trades/pending/${tradeId}/reject`);
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
  // Pull the user's Robinhood watchlists into a synced "Robinhood" list.
  syncRobinhood: async (userId: string) => {
    const response = await api.post(`/watchlist/${userId}/sync/robinhood`);
    return response.data;
  },
  // Extract tickers from uploaded/camera screenshots and add them to a list.
  importScreenshot: async (userId: string, images: string[], listId?: string) => {
    const response = await api.post(`/watchlist/${userId}/sync/screenshot`, { images, list_id: listId });
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

export interface CreditBalance {
  user_id: string;
  credits: number;
  total_credits_used: number;
  plan: 'free' | 'pro' | 'admin';
  subscription_provider: 'stripe' | 'apple' | null;
  subscription_status: string | null;
  cancel_at_period_end: boolean;
  current_period_end: string | null;
}

export const creditsApi = {
  getBalance: async (userId: string): Promise<CreditBalance> => {
    const response = await api.get(`/credits/balance/${userId}`);
    return response.data as CreditBalance;
  },
};

export interface UserPreferences {
  require_trade_approval: boolean;
  morning_brief_enabled: boolean;
  morning_brief_time: string;     // HH:MM (local)
  morning_brief_timezone: string; // IANA, e.g. Asia/Kolkata
  morning_brief_phone: string;    // E.164 WhatsApp number; empty disables WhatsApp
  heartbeat_enabled: boolean;         // recurring agentic portfolio/news watch
  heartbeat_interval_minutes: number; // min 5; free plan fixed to 1440 (daily)
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

// ─────────────────────────────────────────────────────────────────────────────
// Goal / "mission" API — keep in sync with web frontend/lib/api.ts
// ─────────────────────────────────────────────────────────────────────────────

export type GoalKind = 'number' | 'grow' | 'income' | 'protect';

export interface Goal {
  kind: GoalKind;
  title: string;
  objective?: string | null;
  target_amount?: number | null;
  deadline?: string | null;          // ISO date (YYYY-MM-DD)
  horizon_years?: number | null;
  monthly_contribution?: number | null;
  monthly_income?: number | null;
  risk?: number | null;              // 1..10
  options_enabled: boolean;
  config: Record<string, any>;
  preferences?: Record<string, any>; // profile "about me": watch, notify, experience, constraints, notes
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export type SetGoalRequest = Partial<Omit<Goal, 'kind' | 'status' | 'created_at' | 'updated_at'>> & {
  kind: GoalKind;
};

export const goalApi = {
  // Returns null when no goal is set yet (drives the onboarding gate).
  getGoal: async (userId: string): Promise<Goal | null> => {
    const response = await api.get(`/account/${userId}/goal`);
    return (response.data ?? null) as Goal | null;
  },
  setGoal: async (userId: string, goal: SetGoalRequest): Promise<Goal> => {
    const response = await api.put(`/account/${userId}/goal`, goal);
    return response.data as Goal;
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

// Widgets — agent-built live dashboards. Mirrors frontend/lib/api.ts widgetsApi.
// Auth is attached automatically by the axios interceptor; the shared endpoints
// are public but sending the bearer is harmless.
export const widgetsApi = {
  list: async (): Promise<WidgetSummary[]> => (await api.get('/widgets')).data,
  gallery: async (params?: { q?: string; sort?: 'recent' | 'popular' }): Promise<WidgetSummary[]> =>
    (await api.get('/widgets/gallery', { params })).data,
  get: async (id: string): Promise<Widget> => (await api.get(`/widgets/${id}`)).data,
  create: async (body: {
    title: string; description?: string; emoji?: string; tags?: string[]; spec: WidgetSpec;
  }): Promise<Widget> => (await api.post('/widgets', body)).data,
  update: async (
    id: string,
    body: { title?: string; description?: string; emoji?: string; tags?: string[]; spec?: WidgetSpec },
  ): Promise<Widget> => (await api.patch(`/widgets/${id}`, body)).data,
  delete: async (id: string) => (await api.delete(`/widgets/${id}`)).data,
  publish: async (id: string, unpublish = false): Promise<Widget> =>
    (await api.post(`/widgets/${id}/publish`, { unpublish })).data,
  clone: async (id: string): Promise<Widget> => (await api.post(`/widgets/${id}/clone`)).data,
  getData: async (id: string): Promise<WidgetData> => (await api.get(`/widgets/${id}/data`)).data,
  getShared: async (slug: string): Promise<Widget | null> => {
    try { return (await api.get(`/widgets/shared/${encodeURIComponent(slug)}`)).data; } catch { return null; }
  },
  getSharedData: async (slug: string): Promise<WidgetData> => {
    try { return (await api.get(`/widgets/shared/${encodeURIComponent(slug)}/data`)).data; } catch { return {}; }
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

// ── Screener ─────────────────────────────────────────────────────────────────

export interface ScreenerFilters {
  sector?: string;
  industry?: string;
  market_cap_min?: number;
  market_cap_max?: number;
  beta_min?: number;
  beta_max?: number;
  dividend_min?: number;
  price_min?: number;
  price_max?: number;
  volume_min?: number;
}

export interface ScreenerResult {
  symbol: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  price: number | null;
  beta: number | null;
  dividend: number | null;
  volume: number | null;
  exchange: string | null;
}

// ── Scheduled jobs (automations) — mirrors web jobsApi ──────────────────────

export type Recurrence = 'hourly' | 'daily' | 'weekly' | 'weekdays' | null;

export interface ScheduledJob {
  id: string;
  name: string;
  message: string;
  run_at: string;
  recurrence: Recurrence | string;
  status: 'pending' | 'running' | 'done' | 'failed' | 'cancelled' | 'paused';
  created_at: string;
  last_run_at: string | null;
  run_count: number;
  last_error: string | null;
  last_run_credits: number;
  credits_spent: number;
  system_key: string | null;
  comped: boolean;
  activity_gated: boolean;
  run_chat_id: string | null;
}

export interface CreateJobInput {
  message: string;
  run_at: string;
  recurrence?: Recurrence;
  name?: string;
}

export interface JobListResponse {
  jobs: ScheduledJob[];
  recurring_count: number;
  oneoff_count: number;
  recurring_limit: number;
  oneoff_limit: number;
}

export const jobsApi = {
  list: async (): Promise<JobListResponse> => (await api.get('/jobs')).data,
  create: async (input: CreateJobInput): Promise<ScheduledJob> => (await api.post('/jobs', input)).data,
  cancel: async (jobId: string): Promise<void> => { await api.delete(`/jobs/${jobId}`); },
  pause: async (jobId: string): Promise<void> => { await api.post(`/jobs/${jobId}/pause`); },
  resume: async (jobId: string): Promise<void> => { await api.post(`/jobs/${jobId}/resume`); },
  pauseAll: async (): Promise<void> => { await api.post('/jobs/pause-all'); },
  resumeAll: async (): Promise<void> => { await api.post('/jobs/resume-all'); },
};

// ── Trade ideas — Finch's calls + the scorecard that grades them ─────────────

export interface TradeIdea {
  id: string;
  created_at: string;
  symbol: string;
  direction: 'long' | 'short';
  catalyst_type: string;
  catalyst_summary: string;
  thesis: string;
  bear_case: string | null;
  sources: { title?: string; url?: string }[];
  entry_ref: number;
  stop: number;
  target: number;
  horizon_days: number;
  conviction: number;
  status: 'proposed' | 'approved' | 'rejected';
  outcome: 'pending' | 'target' | 'stop' | 'expired';
  return_pct: number | null;
  benchmark_return_pct: number | null;
}

export interface IdeaScorecard {
  total: number;
  open: number;
  scored: number;
  wins: number;
  losses: number;
  hit_rate: number | null;
  avg_return_pct: number | null;
  avg_alpha_pct: number | null;
}

export const ideasApi = {
  list: async (limit = 50): Promise<{ ideas: TradeIdea[]; scorecard: IdeaScorecard }> =>
    (await api.get('/ideas', { params: { limit } })).data,
  decide: async (ideaId: string, approve: boolean, execution_mode?: 'auto' | 'manual'): Promise<TradeIdea> =>
    (await api.post(`/ideas/${ideaId}/decide`, { approve, execution_mode })).data,
};

// ── Theses — the user's own story on each stock (backend: services/theses.py,
// stored in the memory store at store/theses/) ─────────────────────────────

export type ThesisStance = 'own' | 'watch' | 'avoid';
export type ThesisStatus = 'intact' | 'weakened' | 'broken';

export interface ThesisLogEntry {
  date: string;
  verdict: MoveVerdict;
  status: ThesisStatus | null;
  note: string;
}

export interface Thesis {
  symbol: string;
  stance: ThesisStance;
  why: string;
  breaks: string;
  written: string | null;
  updated: string | null;
  log: ThesisLogEntry[];
}

export interface ThesisCheck {
  read: MoveExplanation;
  check: { status: ThesisStatus; reason: string } | null;
}

export const THESIS_STATUS_META: Record<ThesisStatus, { label: string; fg: string; bg: string }> = {
  intact: { label: 'Thesis intact', fg: '#047857', bg: '#ecfdf5' },
  weakened: { label: 'Thesis weakened', fg: '#b45309', bg: '#fffbeb' },
  broken: { label: 'Thesis broken', fg: '#b91c1c', bg: '#fef2f2' },
};

export const thesesApi = {
  list: async (): Promise<{ theses: Thesis[] }> => (await api.get('/theses')).data,
  /** null when the user hasn't written one. */
  get: async (symbol: string): Promise<Thesis | null> =>
    (await api.get(`/theses/${encodeURIComponent(symbol)}`)).data ?? null,
  save: async (symbol: string, body: { why: string; breaks?: string; stance: ThesisStance }): Promise<Thesis> =>
    (await api.put(`/theses/${encodeURIComponent(symbol)}`, body)).data,
  remove: async (symbol: string): Promise<void> => { await api.delete(`/theses/${encodeURIComponent(symbol)}`); },
  check: async (symbol: string): Promise<ThesisCheck> => (await api.get(`/theses/${encodeURIComponent(symbol)}/check`)).data,
};
