'use client';

import React, { useRef, useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import AppSidebar, { type AppSidebarRef } from './AppSidebar';
import ChatView from '@/components/chat/ChatView';
import { ChatModeProvider } from '@/contexts/ChatModeContext';
import { NavigationProvider } from '@/contexts/NavigationContext';

export default function AppLayout() {
  const { user } = useAuth();
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [activeChatIsLoading, setActiveChatIsLoading] = useState(false);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);
  const [chatPrefill, setChatPrefill] = useState<string | undefined>();

  const sidebarRef = useRef<AppSidebarRef>(null);

  if (!user) return null;

  return (
    <div className="flex h-dvh bg-white overflow-hidden">
      <AppSidebar
        ref={sidebarRef}
        userId={user.id}
        currentChatId={currentChatId}
        onSelectChat={(chatId) => setCurrentChatId(chatId)}
        onNewChat={() => setCurrentChatId(null)}
        refreshTrigger={chatHistoryRefresh}
        isCreatingChat={isCreatingChat}
        activeChatIsLoading={activeChatIsLoading}
      />

      <div className="flex-1 overflow-hidden">
        <NavigationProvider>
          <ChatModeProvider>
            <ChatView
              externalChatId={currentChatId}
              onChatIdChange={setCurrentChatId}
              onCreatingChatChange={setIsCreatingChat}
              onLoadingChange={setActiveChatIsLoading}
              onHistoryRefresh={() => setChatHistoryRefresh(p => p + 1)}
              sidebarRef={sidebarRef}
              prefillMessage={chatPrefill}
              onVisualizationClick={() => {}}
            />
          </ChatModeProvider>
        </NavigationProvider>
      </div>
    </div>
  );
}
