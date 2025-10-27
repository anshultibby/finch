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
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  timestamp: string;
  needs_auth?: boolean;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatHistory {
  session_id: string;
  messages: Message[];
}

export interface SnapTradeConnectionRequest {
  session_id: string;
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

export const chatApi = {
  sendMessage: async (message: string, sessionId?: string): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat', {
      message,
      session_id: sessionId,
    });
    return response.data;
  },

  getChatHistory: async (sessionId: string): Promise<ChatHistory> => {
    const response = await api.get<ChatHistory>(`/chat/history/${sessionId}`);
    return response.data;
  },

  clearChatHistory: async (sessionId: string): Promise<void> => {
    await api.delete(`/chat/history/${sessionId}`);
  },

  healthCheck: async (): Promise<{ status: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export const snaptradeApi = {
  initiateConnection: async (sessionId: string, redirectUri: string): Promise<SnapTradeConnectionResponse> => {
    const response = await api.post<SnapTradeConnectionResponse>('/snaptrade/connect', {
      session_id: sessionId,
      redirect_uri: redirectUri,
    });
    return response.data;
  },

  handleCallback: async (sessionId: string): Promise<SnapTradeStatusResponse> => {
    const response = await api.post<SnapTradeStatusResponse>('/snaptrade/callback', {
      session_id: sessionId,
    });
    return response.data;
  },

  checkStatus: async (sessionId: string): Promise<SnapTradeStatusResponse> => {
    const response = await api.get<SnapTradeStatusResponse>(`/snaptrade/status/${sessionId}`);
    return response.data;
  },

  disconnect: async (sessionId: string): Promise<void> => {
    await api.delete(`/snaptrade/disconnect/${sessionId}`);
  },
};

export default api;

