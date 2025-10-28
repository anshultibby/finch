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
  session_id?: string;  // This is actually user_id
  chat_id?: string;
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

export interface UserChatsResponse {
  user_id: string;
  chats: Array<{
    chat_id: string;
    title: string | null;
    created_at: string;
    updated_at: string;
  }>;
}

export const chatApi = {
  sendMessage: async (message: string, userId: string, chatId: string): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat', {
      message,
      session_id: userId,  // Using session_id field for user_id
      chat_id: chatId,
    });
    return response.data;
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

