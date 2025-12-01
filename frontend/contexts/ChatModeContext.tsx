'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

export type ChatModeType = 
  | 'general' 
  | 'create_strategy' 
  | 'execute_strategy' 
  | 'edit_strategy' 
  | 'analyze_performance';

export interface ChatModeMetadata {
  strategyId?: string;
  strategyName?: string;
  tradeId?: string;
  [key: string]: any;
}

export interface ChatMode {
  type: ChatModeType;
  metadata?: ChatModeMetadata;
}

interface ChatModeContextType {
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
  clearMode: () => void;
  isInSpecialMode: boolean;
}

const ChatModeContext = createContext<ChatModeContextType | undefined>(undefined);

const DEFAULT_MODE: ChatMode = { type: 'general' };

export function ChatModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ChatMode>(DEFAULT_MODE);

  const setMode = (newMode: ChatMode) => {
    setModeState(newMode);
  };

  const clearMode = () => {
    setModeState(DEFAULT_MODE);
  };

  const isInSpecialMode = mode.type !== 'general';

  return (
    <ChatModeContext.Provider 
      value={{ 
        mode, 
        setMode, 
        clearMode, 
        isInSpecialMode 
      }}
    >
      {children}
    </ChatModeContext.Provider>
  );
}

export function useChatMode() {
  const context = useContext(ChatModeContext);
  if (context === undefined) {
    throw new Error('useChatMode must be used within a ChatModeProvider');
  }
  return context;
}

