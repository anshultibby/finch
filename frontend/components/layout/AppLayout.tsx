'use client';

import React, { useRef, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import AppSidebar, { type SidebarPanel, type AppSidebarRef } from './AppSidebar';
import ChatView from '@/components/chat/ChatView';
import StrategiesPanel from '../StrategiesPanel';
import SkillsPanel from '../SkillsPanel';

export default function AppLayout() {
  const { user } = useAuth();
  const [activePanel, setActivePanel] = useState<SidebarPanel>('chat');
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [activeChatIsLoading, setActiveChatIsLoading] = useState(false);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);

  const sidebarRef = useRef<AppSidebarRef>(null);

  if (!user) return null;

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      <AppSidebar
        ref={sidebarRef}
        userId={user.id}
        currentChatId={currentChatId}
        activePanel={activePanel}
        onSelectPanel={setActivePanel}
        onSelectChat={(chatId) => {
          setActivePanel('chat');
          setCurrentChatId(chatId);
        }}
        onNewChat={() => {
          setActivePanel('chat');
          setCurrentChatId(null);
        }}
        refreshTrigger={chatHistoryRefresh}
        isCreatingChat={isCreatingChat}
        activeChatIsLoading={activeChatIsLoading}
      />

      <div className="flex-1 overflow-hidden">
        {/* ChatView is always mounted — streams survive panel switches */}
        <div className={activePanel === 'chat' ? 'h-full' : 'hidden'}>
          <ChatView
            externalChatId={currentChatId}
            onChatIdChange={setCurrentChatId}
            onCreatingChatChange={setIsCreatingChat}
            onLoadingChange={setActiveChatIsLoading}
            onHistoryRefresh={() => setChatHistoryRefresh(p => p + 1)}
            sidebarRef={sidebarRef}
          />
        </div>

        {activePanel === 'strategies' && (
          <div className="h-full">
            <StrategiesPanel />
          </div>
        )}

        {activePanel === 'skills' && (
          <div className="h-full">
            <SkillsPanel />
          </div>
        )}
      </div>
    </div>
  );
}
