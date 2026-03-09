'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { botsApi } from '@/lib/api';
import type { BotDetail, BotChat } from '@/lib/types';
import BotChatList from './BotChatList';
import BotSidebar from './BotSidebar';
import ChatView from '@/components/chat/ChatView';
import { ApiKeysModal } from '@/components';

interface BotViewProps {
  botId: string;
}

const BOT_REFRESH_INTERVAL = 30_000; // 30s sidebar auto-refresh

function getPlatformLabel(platform: string): string {
  switch (platform) {
    case 'kalshi': return 'Kalshi';
    case 'alpaca': return 'Brokerage';
    case 'research': return 'Research';
    default: return platform;
  }
}

export default function BotView({ botId }: BotViewProps) {
  const { user } = useAuth();
  const router = useRouter();
  const [bot, setBot] = useState<BotDetail | null>(null);
  const [chats, setChats] = useState<BotChat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [botLoading, setBotLoading] = useState(true);
  const [chatsLoading, setChatsLoading] = useState(true);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);
  const sidebarRef = useRef(null);
  const [showApiKeys, setShowApiKeys] = useState(false);
  const autoCreatingRef = useRef(false);

  const fetchBot = useCallback(async () => {
    if (!user) return;
    try {
      const data = await botsApi.getBot(user.id, botId);
      setBot(data);
    } catch (e) {
      console.error('Failed to fetch bot:', e);
    } finally {
      setBotLoading(false);
    }
  }, [user, botId]);

  const fetchChats = useCallback(async () => {
    if (!user) return;
    try {
      const data = await botsApi.listBotChats(user.id, botId);
      setChats(data);
    } catch (e) {
      console.error('Failed to fetch bot chats:', e);
    } finally {
      setChatsLoading(false);
    }
  }, [user, botId]);

  // Parallel initial load
  useEffect(() => {
    fetchBot();
    fetchChats();
  }, [fetchBot, fetchChats]);

  // Auto-refresh bot data (positions, stats) periodically
  useEffect(() => {
    const interval = setInterval(fetchBot, BOT_REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchBot]);

  // Select first chat when chats load and none is active
  useEffect(() => {
    if (!activeChatId && chats.length > 0) {
      setActiveChatId(chats[0].chat_id);
    }
  }, [chats, activeChatId]);

  // Auto-create first chat for new bots (guarded against double-fire)
  useEffect(() => {
    if (!user || !bot || chatsLoading || chats.length > 0 || activeChatId || autoCreatingRef.current) return;
    autoCreatingRef.current = true;
    const createFirstChat = async () => {
      try {
        const chat = await botsApi.createBotChat(user.id, botId);
        setChats([chat]);
        setActiveChatId(chat.chat_id);
      } catch (e) {
        console.error('Failed to create initial chat:', e);
      }
    };
    createFirstChat();
  }, [user, bot, chatsLoading, chats.length, activeChatId, botId]);

  const handleNewChat = async () => {
    if (!user) return;
    try {
      const chat = await botsApi.createBotChat(user.id, botId);
      setChats((prev) => [chat, ...prev]);
      setActiveChatId(chat.chat_id);
    } catch (e) {
      console.error('Failed to create chat:', e);
    }
  };

  const handleClosePosition = async (positionId: string) => {
    if (!user) return;
    try {
      await botsApi.closePosition(user.id, botId, positionId);
      fetchBot(); // Refresh bot data
    } catch (e) {
      console.error('Failed to close position:', e);
    }
  };

  if (!user) return null;

  if (botLoading && !bot) {
    return (
      <div className="flex h-dvh items-center justify-center bg-white">
        <div className="w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!bot) {
    return (
      <div className="flex h-dvh items-center justify-center bg-white">
        <div className="text-center">
          <p className="text-gray-500">Bot not found</p>
          <button onClick={() => router.push('/')} className="mt-2 text-blue-500 text-sm hover:underline">
            Back to home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-dvh bg-white">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-gray-200 bg-white shrink-0">
        <button
          onClick={() => router.push('/')}
          className="p-1.5 -ml-1 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
        <span className="text-lg">{bot.icon || '🤖'}</span>
        <h1 className="text-sm font-semibold text-gray-900">{bot.name}</h1>
        <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
          {getPlatformLabel(bot.platform)}
        </span>
        <div className="flex-1" />
        {/* Settings button */}
        <button onClick={() => setShowApiKeys(true)} className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
          </svg>
        </button>
      </div>

      {/* 3-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Chat list */}
        <div className="w-56 shrink-0">
          <BotChatList
            chats={chats}
            activeChatId={activeChatId}
            onSelectChat={setActiveChatId}
            onNewChat={handleNewChat}
            loading={chatsLoading}
          />
        </div>

        {/* Center: Chat */}
        <div className="flex-1 min-w-0">
          {activeChatId ? (
            <ChatView
              externalChatId={activeChatId}
              onChatIdChange={setActiveChatId}
              onCreatingChatChange={() => {}}
              onLoadingChange={() => {}}
              onHistoryRefresh={() => {
                setChatHistoryRefresh((p) => p + 1);
                fetchChats();
              }}
              sidebarRef={sidebarRef}
              botId={botId}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              {chatsLoading ? 'Loading...' : 'Select or create a chat'}
            </div>
          )}
        </div>

        {/* Right: Sidebar */}
        <div className="w-72 shrink-0">
          <BotSidebar bot={bot} userId={user.id} onClosePosition={handleClosePosition} onCapitalChanged={fetchBot} />
        </div>
      </div>
      {showApiKeys && (
        <ApiKeysModal isOpen={showApiKeys} onClose={() => setShowApiKeys(false)} />
      )}
    </div>
  );
}
