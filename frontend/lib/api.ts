import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ChatMessage {
  message: string;
  user_id?: string;  // Supabase user ID
  chat_id?: string;
}

export interface ToolCallStatus {
  tool_call_id: string;
  tool_name: string;
  status: 'calling' | 'completed' | 'error';
  resource_id?: string;
  error?: string;
}

export interface ChatResponse {
  response: string;
  user_id: string;
  timestamp: string;
  needs_auth?: boolean;
  tool_calls?: ToolCallStatus[];
}

// SSE Event types
export interface SSEToolCallStartEvent {
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  timestamp: string;
}

export interface SSEToolCallCompleteEvent {
  tool_call_id: string;
  tool_name: string;
  status: 'completed' | 'error';
  resource_id?: string;
  error?: string;
  timestamp: string;
}

export interface SSEThinkingEvent {
  message: string;
  timestamp: string;
}

export interface SSEAssistantMessageDeltaEvent {
  delta: string;
}

export interface SSEAssistantMessageEvent {
  content: string;
  timestamp: string;
  needs_auth: boolean;
}

export interface SSEDoneEvent {
  message: string;
  timestamp: string;
}

export interface SSEErrorEvent {
  error: string;
  details?: string;
  timestamp: string;
}

export interface OptionButton {
  id: string;
  label: string;
  value: string;
  description?: string;
}

export interface SSEOptionsEvent {
  type: string;
  question: string;
  options: OptionButton[];
  timestamp: string;
}

export interface SSEToolStatusEvent {
  tool_call_id?: string;
  tool_name?: string;
  status: string;
  message?: string;
  timestamp: string;
}

export interface SSEToolProgressEvent {
  tool_call_id?: string;
  tool_name?: string;
  percent: number;
  message?: string;
  timestamp: string;
}

export interface SSEToolLogEvent {
  tool_call_id?: string;
  tool_name?: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
}

// Callback types for SSE event handlers
export interface SSEEventHandlers {
  onToolCallStart?: (event: SSEToolCallStartEvent) => void;
  onToolCallComplete?: (event: SSEToolCallCompleteEvent) => void;
  onToolStatus?: (event: SSEToolStatusEvent) => void;
  onToolProgress?: (event: SSEToolProgressEvent) => void;
  onToolLog?: (event: SSEToolLogEvent) => void;
  onThinking?: (event: SSEThinkingEvent) => void;
  onAssistantMessageDelta?: (event: SSEAssistantMessageDeltaEvent) => void;
  onAssistantMessage?: (event: SSEAssistantMessageEvent) => void;
  onOptions?: (event: SSEOptionsEvent) => void;
  onDone?: (event: SSEDoneEvent) => void;
  onError?: (event: SSEErrorEvent) => void;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatHistory {
  user_id: string;
  messages: Message[];
}

export interface SnapTradeConnectionRequest {
  user_id: string;
  redirect_uri: string;
}

export interface SnapTradeConnectionResponse {
  success: boolean;
  message: string;
  redirect_uri?: string;
}

export interface SnapTradeStatusResponse {
  success: boolean;
  message: string;
  is_connected: boolean;
  account_count?: number;
  brokerages?: string[];
}

export interface UserChatsResponse {
  user_id: string;
  chats: Array<{
    chat_id: string;
    title: string | null;
    created_at: string;
    updated_at: string;
  }>;
}

export interface ResourceMetadata {
  parameters?: Record<string, any>;
  tool_call_id?: string;
  execution_time_ms?: number;
  total_count?: number;
}

export interface Resource {
  id: string;
  chat_id: string;
  user_id: string;
  tool_name: string;
  resource_type: string;
  title: string;
  data: Record<string, any>;
  metadata?: ResourceMetadata;
  created_at: string;
}

export const chatApi = {
  sendMessage: async (message: string, userId: string, chatId: string): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat', {
      message,
      user_id: userId,
      chat_id: chatId,
    });
    return response.data;
  },

  /**
   * Send a message and receive streaming SSE events
   * This is the recommended way to send messages for real-time updates
   */
  sendMessageStream: (
    message: string,
    userId: string,
    chatId: string,
    handlers: SSEEventHandlers
  ): EventSource => {
    // Create SSE connection
    const url = new URL('/chat/stream', API_BASE_URL);
    
    // We need to POST data, but EventSource only supports GET
    // So we'll use fetch with stream processing instead
    const abortController = new AbortController();
    
    // Start the fetch request
    fetch(url.toString(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        user_id: userId,
        chat_id: chatId,
      }),
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
          
          if (done) {
            break;
          }
          
          // Log when chunks arrive in browser
          console.log(`🌐 Browser received chunk: ${value.length} bytes at ${new Date().toISOString()}`);
          
          // Decode chunk and add to buffer
          buffer += decoder.decode(value, { stream: true });
          
          // Process complete SSE messages
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || ''; // Keep incomplete message in buffer
          
          console.log(`📦 Processing ${lines.length} complete SSE events`);
          
          for (const line of lines) {
            if (!line.trim()) continue;
            
            // Parse SSE format: event: <type>\ndata: <json>
            const eventMatch = line.match(/event:\s*(\w+)/);
            const dataMatch = line.match(/data:\s*([\s\S]+)/);
            
            if (eventMatch && dataMatch) {
              const eventType = eventMatch[1];
              const eventData = JSON.parse(dataMatch[1]);
              
              // Call appropriate handler
              switch (eventType) {
                case 'tool_call_start':
                  handlers.onToolCallStart?.(eventData as SSEToolCallStartEvent);
                  break;
                case 'tool_call_complete':
                  handlers.onToolCallComplete?.(eventData as SSEToolCallCompleteEvent);
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
                case 'thinking':
                  handlers.onThinking?.(eventData as SSEThinkingEvent);
                  break;
                case 'assistant_message_delta':
                  handlers.onAssistantMessageDelta?.(eventData as SSEAssistantMessageDeltaEvent);
                  break;
                case 'assistant_message':
                  handlers.onAssistantMessage?.(eventData as SSEAssistantMessageEvent);
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
    
    // Return a mock EventSource with close method
    return {
      close: () => abortController.abort(),
    } as EventSource;
  },

  getChatHistory: async (chatId: string): Promise<ChatHistory> => {
    const response = await api.get<ChatHistory>(`/chat/history/${chatId}`);
    return response.data;
  },

  clearChatHistory: async (chatId: string): Promise<void> => {
    await api.delete(`/chat/history/${chatId}`);
  },

  getUserChats: async (userId: string): Promise<UserChatsResponse> => {
    const response = await api.get<UserChatsResponse>(`/chat/user/${userId}/chats`);
    return response.data;
  },

  healthCheck: async (): Promise<{ status: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export interface BrokerageAccount {
  id: string;
  account_id: string;
  broker_id: string;
  broker_name: string;
  name: string;
  number: string;
  type: string;
  balance: number;
  connected_at: string;
  last_synced_at: string | null;
}

export interface Brokerage {
  id: string;
  name: string;
  logo: string;
}

export interface BrokerageAccountsResponse {
  success: boolean;
  accounts: BrokerageAccount[];
  message: string;
}

export interface BrokeragesResponse {
  success: boolean;
  brokerages: Brokerage[];
  message: string;
}

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

