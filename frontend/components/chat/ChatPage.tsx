'use client';

import React from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import ChatView from './ChatView';
import type { AppSidebarRef } from '@/components/layout/AppSidebar';

interface ChatPageProps {
  sidebarRef: React.RefObject<AppSidebarRef>;
  onCreatingChatChange: (v: boolean) => void;
  onLoadingChange: (v: boolean) => void;
  onHistoryRefresh: () => void;
}

export default function ChatPage({
  sidebarRef,
  onCreatingChatChange,
  onLoadingChange,
  onHistoryRefresh,
}: ChatPageProps) {
  const { currentChatId, setCurrentChatId, chatContext } = useNavigation();

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex-1 overflow-hidden">
        <ChatView
          externalChatId={currentChatId}
          onChatIdChange={setCurrentChatId}
          onCreatingChatChange={onCreatingChatChange}
          onLoadingChange={onLoadingChange}
          onHistoryRefresh={onHistoryRefresh}
          sidebarRef={sidebarRef}
          prefillMessage={chatContext?.prefill}
          prefillLabel={chatContext?.prefillLabel}
        />
      </div>
    </div>
  );
}
