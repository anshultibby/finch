'use client';

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import { useAuth } from '@/contexts/AuthContext';
import ChatView from './ChatView';
import type { AppSidebarRef } from '@/components/layout/AppSidebar';
import type { SwapData } from '@/lib/types';

interface ChatDrawerProps {
  sidebarRef: React.RefObject<AppSidebarRef>;
  currentChatId: string | null;
  onChatIdChange: (id: string | null) => void;
  onCreatingChatChange: (v: boolean) => void;
  onLoadingChange: (v: boolean) => void;
  onHistoryRefresh: () => void;
  onSwapsReceived?: (chatId: string, swaps: SwapData[]) => void;
}

export default function ChatDrawer({
  sidebarRef,
  currentChatId,
  onChatIdChange,
  onCreatingChatChange,
  onLoadingChange,
  onHistoryRefresh,
  onSwapsReceived,
}: ChatDrawerProps) {
  const { chatDrawerOpen, setChatDrawerOpen, chatContext } = useNavigation();
  const [prefill, setPrefill] = useState<string | undefined>();

  // When chat context changes (e.g. "Ask AI about AAPL"), set the prefill
  useEffect(() => {
    if (chatContext?.prefill && chatDrawerOpen) {
      setPrefill(chatContext.prefill);
    }
  }, [chatContext, chatDrawerOpen]);

  // Clear prefill after it's consumed
  const handleChatIdChange = useCallback((id: string | null) => {
    onChatIdChange(id);
    if (id) setPrefill(undefined);
  }, [onChatIdChange]);

  if (!chatDrawerOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20 md:bg-transparent md:pointer-events-none"
        onClick={() => setChatDrawerOpen(false)}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[440px] md:w-[480px] flex flex-col bg-white shadow-2xl border-l border-gray-200 animate-slide-in-right">
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center">
              <svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 0 1 .778-.332 48.294 48.294 0 0 0 5.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
              </svg>
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900">AI Assistant</div>
              {chatContext?.symbol && (
                <div className="text-[11px] text-gray-400">Chatting about {chatContext.symbol}</div>
              )}
            </div>
          </div>
          <button onClick={() => setChatDrawerOpen(false)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Chat content */}
        <div className="flex-1 overflow-hidden">
          <ChatView
            externalChatId={currentChatId}
            onChatIdChange={handleChatIdChange}
            onCreatingChatChange={onCreatingChatChange}
            onLoadingChange={onLoadingChange}
            onHistoryRefresh={onHistoryRefresh}
            onSwapsReceived={onSwapsReceived}
            sidebarRef={sidebarRef}
            prefillMessage={prefill}
            onVisualizationClick={() => {}}
            compact
          />
        </div>
      </div>
    </>
  );
}
