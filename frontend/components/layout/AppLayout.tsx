'use client';

import React, { useRef, useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import AppSidebar, { type SidebarPanel, type AppSidebarRef } from './AppSidebar';
import ChatView from '@/components/chat/ChatView';
import FilesPanel from '../FilesPanel';
import ChartsPanel from '../ChartsPanel';
import SkillsPanel from '../SkillsPanel';
import BotVisualizationsPanel from '../bots/BotVisualizationsPanel';
import { ChatModeProvider } from '@/contexts/ChatModeContext';
import { NavigationProvider } from '@/contexts/NavigationContext';

export default function AppLayout() {
  const { user } = useAuth();
  const [activePanel, setActivePanel] = useState<SidebarPanel>('chat');

  // Allow any panel to switch to chat (e.g. EmptyState prompt selection)
  useEffect(() => {
    const handler = () => setActivePanel('chat');
    window.addEventListener('panel:switch-to-chat', handler);
    return () => window.removeEventListener('panel:switch-to-chat', handler);
  }, []);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [activeChatIsLoading, setActiveChatIsLoading] = useState(false);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);
  const [chatPrefill, setChatPrefill] = useState<string | undefined>();
  const [selectedVisualization, setSelectedVisualization] = useState<string | null>(null);

  useEffect(() => {
    const handler = (e: CustomEvent<{ message: string }>) => {
      setCurrentChatId(null);
      setChatPrefill(e.detail.message);
      setActivePanel('chat');
    };
    window.addEventListener('chat:configure-skill', handler as EventListener);
    return () => window.removeEventListener('chat:configure-skill', handler as EventListener);
  }, []);

  const sidebarRef = useRef<AppSidebarRef>(null);

  if (!user) return null;

  return (
    <div className="flex h-dvh bg-white overflow-hidden">
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
              onVisualizationClick={(filename) => {
                setSelectedVisualization(filename);
                setActivePanel('charts');
              }}
            />
          </ChatModeProvider>
          </NavigationProvider>
        </div>

        {activePanel === 'files' && (
          <div className="h-full">
            <FilesPanel chatId={currentChatId} />
          </div>
        )}

        {activePanel === 'charts' && (
          <div className="h-full">
            <ChartsPanel chatId={currentChatId} selectedChart={selectedVisualization} />
          </div>
        )}

        {activePanel === 'portfolio' && (
          <div className="h-full">
            <BotVisualizationsPanel />
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
