'use client';

import React from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import ChatView from './ChatView';
import type { AppSidebarRef } from '@/components/layout/AppSidebar';
import type { SwapData } from '@/lib/types';

interface ChatPageProps {
  sidebarRef: React.RefObject<AppSidebarRef>;
  onCreatingChatChange: (v: boolean) => void;
  onLoadingChange: (v: boolean) => void;
  onHistoryRefresh: () => void;
  onSwapsReceived?: (chatId: string, swaps: SwapData[]) => void;
}

export default function ChatPage({
  sidebarRef,
  onCreatingChatChange,
  onLoadingChange,
  onHistoryRefresh,
  onSwapsReceived,
}: ChatPageProps) {
  const { currentChatId, setCurrentChatId, chatContext, startNewChat } = useNavigation();

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Page header */}
      <div className="shrink-0 flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-emerald-50 flex items-center justify-center">
            <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
            </svg>
          </div>
          <div>
            <div className="text-sm font-semibold text-gray-900">AI Assistant</div>
            {currentChatId && <div className="text-[11px] text-gray-400">Continuing conversation</div>}
          </div>
        </div>
        <button
          onClick={startNewChat}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
          title="Start a new chat"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New chat
        </button>
      </div>

      {/* Chat content — full page (no compact mode) */}
      <div className="flex-1 overflow-hidden max-w-4xl w-full mx-auto">
        <ChatView
          externalChatId={currentChatId}
          onChatIdChange={setCurrentChatId}
          onCreatingChatChange={onCreatingChatChange}
          onLoadingChange={onLoadingChange}
          onHistoryRefresh={onHistoryRefresh}
          onSwapsReceived={onSwapsReceived}
          sidebarRef={sidebarRef}
          prefillMessage={chatContext?.prefill}
          prefillLabel={chatContext?.prefillLabel}
          onVisualizationClick={() => {}}
        />
      </div>
    </div>
  );
}
