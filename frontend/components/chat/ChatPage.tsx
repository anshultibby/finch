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
  const { currentChatId, setCurrentChatId, chatContext } = useNavigation();

  return (
    <div className="flex flex-col h-full bg-white">
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
