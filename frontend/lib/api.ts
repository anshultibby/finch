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

export interface RobinhoodLoginRequest {
  username: string;
  password: string;
  session_id: string;
  mfa_code?: string;
}

export interface RobinhoodLoginResponse {
  success: boolean;
  message: string;
  has_credentials: boolean;
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

export const robinhoodApi = {
  login: async (username: string, password: string, sessionId: string, mfaCode?: string): Promise<RobinhoodLoginResponse> => {
    const response = await api.post<RobinhoodLoginResponse>('/robinhood/credentials', {
      username,
      password,
      session_id: sessionId,
      mfa_code: mfaCode,
    });
    return response.data;
  },

  checkSession: async (sessionId: string): Promise<RobinhoodLoginResponse> => {
    const response = await api.get<RobinhoodLoginResponse>(`/robinhood/credentials/${sessionId}`);
    return response.data;
  },

  logout: async (sessionId: string): Promise<void> => {
    await api.delete(`/robinhood/credentials/${sessionId}`);
  },
};

export default api;

