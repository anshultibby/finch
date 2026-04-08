'use client';

import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { botsApi, tradesApi } from '@/lib/api';
import type { BotDetail, BotChat, BotWakeup, TradeLog } from '@/lib/types';
import BotChatList, { type BotPanel } from './BotChatList';
import BotDocViewer from './BotDocViewer';
import BotJournalViewer from './BotJournalViewer';
import BotPositionsPanel from './BotPositionsPanel';
import BotTradesPanel from './BotTradesPanel';
import BotFilesPanel from './BotFilesPanel';
import BotVisualizationsPanel from './BotVisualizationsPanel';
import ChatView from '@/components/chat/ChatView';
import { ApiKeysModal } from '@/components';

interface BotViewProps {
  botId: string;
}

const BOT_REFRESH_INTERVAL = 30_000; // 30s auto-refresh

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
  const [wakeups, setWakeups] = useState<BotWakeup[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [activePanel, setActivePanel] = useState<BotPanel>('chat');
  const [botLoading, setBotLoading] = useState(true);
  const [chatsLoading, setChatsLoading] = useState(true);
  const [chatHistoryRefresh, setChatHistoryRefresh] = useState(0);
  const [pendingTradeCount, setPendingTradeCount] = useState(0);
  const [showApiKeys, setShowApiKeys] = useState(false);
  const [showCapitalModal, setShowCapitalModal] = useState(false);
  const [capitalInput, setCapitalInput] = useState('');
  const [capitalAdjusting, setCapitalAdjusting] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
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

  const fetchWakeups = useCallback(async () => {
    if (!user) return;
    try {
      const data = await botsApi.listWakeups(user.id, botId);
      setWakeups(data);
    } catch (e) {
      console.error('Failed to fetch wakeups:', e);
    }
  }, [user, botId]);

  const fetchPendingTrades = useCallback(async () => {
    if (!user) return;
    try {
      const trades: TradeLog[] = await tradesApi.listForBot(user.id, botId);
      setPendingTradeCount(trades.filter(t => t.status === 'pending_approval').length);
    } catch {
      // ignore
    }
  }, [user, botId]);

  // Parallel initial load
  useEffect(() => {
    fetchBot();
    fetchChats();
    fetchWakeups();
    fetchPendingTrades();
  }, [fetchBot, fetchChats, fetchWakeups, fetchPendingTrades]);

  // Auto-refresh bot data (positions, stats) periodically
  useEffect(() => {
    const interval = setInterval(fetchBot, BOT_REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchBot]);

  // Poll pending trades every 15s
  useEffect(() => {
    const interval = setInterval(fetchPendingTrades, 15_000);
    return () => clearInterval(interval);
  }, [fetchPendingTrades]);

  // Select first non-wakeup chat when chats load and none is active
  useEffect(() => {
    if (!activeChatId && chats.length > 0) {
      const firstUserChat = chats.find((c) => !c.title?.startsWith('Wakeup:'));
      if (firstUserChat) setActiveChatId(firstUserChat.chat_id);
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

  // Extract strategy, memory, and journal entries from bot data
  const { strategyContent, memoryContent, journalEntries } = useMemo(() => {
    if (!bot) return { strategyContent: '', memoryContent: '', journalEntries: [] };
    const files = bot.files || [];

    let strategy = bot.mandate || '';
    let memory = '';
    const journal: Array<{ filename: string; content: string; updated_at?: string }> = [];

    for (const f of files) {
      if (f.filename === 'STRATEGY.md' || f.file_type === 'strategy') {
        strategy = f.content || strategy;
      } else if (f.filename === 'MEMORY.md' || f.file_type === 'memory') {
        memory = f.content || '';
      } else if (f.file_type === 'log') {
        journal.push({ filename: f.filename, content: f.content, updated_at: f.updated_at });
      }
      // Legacy fallbacks
      else if (f.filename === 'CONTEXT.md' || f.file_type === 'context') {
        strategy = strategy || f.content || '';
      } else if (f.filename === 'AGENTS.md' || f.file_type === 'agents') {
        memory = memory || f.content || '';
      }
    }

    return { strategyContent: strategy, memoryContent: memory, journalEntries: journal };
  }, [bot]);

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

  const handleCapitalAdjust = async (direction: 'add' | 'withdraw') => {
    if (!user) return;
    const amount = parseFloat(capitalInput);
    if (!amount || amount <= 0) return;
    setCapitalAdjusting(true);
    try {
      await botsApi.adjustCapital(user.id, botId, direction === 'add' ? amount : -amount);
      setCapitalInput('');
      setShowCapitalModal(false);
      fetchBot();
    } catch (e: any) {
      alert(e.message || 'Failed to adjust capital');
    } finally {
      setCapitalAdjusting(false);
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

  const renderOverlayPanel = () => {
    switch (activePanel) {
      case 'strategy':
        return (
          <BotDocViewer
            title="Strategy"
            icon="⚡"
            content={strategyContent}
            description="Trading thesis, signal rules, risk parameters"
            onBack={() => setActivePanel('chat')}
          />
        );
      case 'memory':
        return (
          <BotDocViewer
            title="Memory"
            icon="🧠"
            content={memoryContent}
            description="Learned behaviors, rules & preferences"
            onBack={() => setActivePanel('chat')}
          />
        );
      case 'journal':
        return (
          <BotJournalViewer
            entries={journalEntries}
            onBack={() => setActivePanel('chat')}
          />
        );
      case 'positions':
        return (
          <BotPositionsPanel
            bot={bot}
            userId={user.id}
            onBack={() => setActivePanel('chat')}
            onClosePosition={handleClosePosition}
          />
        );
      case 'trades':
        return (
          <BotTradesPanel
            userId={user.id}
            botId={botId}
            refreshKey={chatHistoryRefresh}
            onBack={() => setActivePanel('chat')}
            onTradeAction={fetchPendingTrades}
          />
        );
      case 'files':
        return (
          <BotFilesPanel
            userId={user.id}
            botId={botId}
            onBack={() => setActivePanel('chat')}
          />
        );
      case 'visualizations':
        return (
          <BotVisualizationsPanel
            onBack={() => setActivePanel('chat')}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex h-dvh bg-[#fafaf9]">
      {/* Left sidebar */}
      {sidebarOpen ? (
        <div className="shrink-0 w-56 flex flex-col bg-[#f8f8f7] border-r border-gray-200/60 transition-all duration-200">
          {/* Sidebar header */}
          <div className="flex items-center gap-2 px-3 py-2.5 shrink-0">
            <button
              onClick={() => router.push('/')}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-white/60 rounded-md transition-all"
              title="All agents"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            <span className="text-sm">{bot.icon || '🤖'}</span>
            <span className="text-xs font-semibold text-gray-900 truncate flex-1">{bot.name}</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-white/60 rounded-md transition-all"
              title="Collapse sidebar"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M9 3v18" />
              </svg>
            </button>
          </div>
          {/* Nav + chats */}
          <div className="flex-1 overflow-hidden">
            <BotChatList
              chats={chats}
              activeChatId={activeChatId}
              activePanel={activePanel}
              onSelectChat={setActiveChatId}
              onNewChat={handleNewChat}
              onSelectPanel={setActivePanel}
              loading={chatsLoading}
              hasPositions={(bot.positions?.length ?? 0) > 0}
              hasTrades={true}
              pendingTradeCount={pendingTradeCount}
              wakeups={wakeups}
            />
          </div>
          {/* Bottom: settings */}
          <div className="shrink-0 px-2 py-2 border-t border-gray-200/60">
            <button
              onClick={() => setShowApiKeys(true)}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 text-[13px] text-gray-500 rounded-lg hover:bg-white/80 hover:text-gray-700 transition-all"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
              </svg>
              Settings
            </button>
          </div>
        </div>
      ) : (
        /* Collapsed icon rail */
        <div className="shrink-0 w-12 flex flex-col items-center bg-[#f8f8f7] border-r border-gray-200/60 py-3 gap-1">
          {[
            { label: 'Open sidebar', onClick: () => setSidebarOpen(true), icon: <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 3v18" /></>, active: false },
            { label: 'New chat', onClick: () => handleNewChat(), icon: <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />, active: false },
            { label: 'Current chat', onClick: () => setActivePanel('chat'), icon: <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />, active: activePanel === 'chat', dividerAfter: true },
            { label: 'Positions', onClick: () => setActivePanel('positions'), icon: <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />, active: activePanel === 'positions' },
            { label: 'Trades', onClick: () => setActivePanel('trades'), icon: <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 3M21 7.5H7.5" />, active: activePanel === 'trades' },
            { label: 'Files', onClick: () => setActivePanel('files'), icon: <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />, active: activePanel === 'files' },
          ].map((item: any) => (
            <React.Fragment key={item.label}>
              <button
                onClick={item.onClick}
                className={`relative group p-2 rounded-lg transition-all duration-200 ${item.active ? 'bg-white text-gray-900 shadow-sm border border-gray-100' : 'text-gray-500 hover:text-gray-700 hover:bg-white/60'}`}
              >
                <svg className="w-[18px] h-[18px] relative" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">{item.icon}</svg>
                <span className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2.5 py-1 text-xs font-medium text-white bg-gray-900 rounded-lg whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-lg">
                  {item.label}
                </span>
              </button>
              {item.dividerAfter && <div className="w-6 border-t border-gray-200/60 my-1" />}
            </React.Fragment>
          ))}
          {/* Spacer + settings at bottom */}
          <div className="flex-1" />
          <button
            onClick={() => setShowApiKeys(true)}
            className="relative group p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-white/60 transition-all duration-200"
          >
            <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
            <span className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2.5 py-1 text-xs font-medium text-white bg-gray-900 rounded-lg whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-lg">
              Settings
            </span>
          </button>
        </div>
      )}

      {/* Main content area */}
      <div className="flex-1 min-w-0 flex flex-col relative bg-white">
        {/* Inline title row */}
        <div className="flex items-center gap-2.5 px-4 py-2 shrink-0 border-b border-gray-100/80">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-gradient-to-br from-gray-900 to-gray-700 flex items-center justify-center">
              <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.306a11.95 11.95 0 015.814-5.518l2.74-1.22" />
              </svg>
            </div>
            <span className="text-[13px] font-semibold text-gray-900">Finch</span>
          </div>
          <div className="flex-1" />
          {bot.capital_balance != null && bot.platform !== 'research' && (
            <button
              onClick={() => setShowCapitalModal(true)}
              className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-gray-50 border border-gray-100 hover:bg-gray-100 hover:border-gray-200 transition-all"
            >
              <span className="text-[11px] font-semibold text-gray-700 tabular-nums">${bot.capital_balance.toFixed(2)}</span>
            </button>
          )}
        </div>
        {/* Content panels */}
        <div className="flex-1 min-h-0 relative">
          <div className={activePanel !== 'chat' ? 'absolute inset-0 invisible' : 'h-full'}>
            {activeChatId ? (
              <ChatView
                externalChatId={activeChatId}
                onChatIdChange={setActiveChatId}
                onCreatingChatChange={() => {}}
                onLoadingChange={() => {}}
                onHistoryRefresh={() => {
                  setChatHistoryRefresh((p) => p + 1);
                  fetchChats();
                  fetchBot();
                }}
                botId={botId}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                {chatsLoading ? 'Loading...' : 'Select or create a chat'}
              </div>
            )}
          </div>
          {activePanel !== 'chat' && (
            <div className="absolute inset-0 z-10 bg-white">
              {renderOverlayPanel()}
            </div>
          )}
        </div>
      </div>
      {showApiKeys && (
        <ApiKeysModal isOpen={showApiKeys} onClose={() => setShowApiKeys(false)} />
      )}
      {showCapitalModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-80">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900">Adjust Capital</h3>
              <button onClick={() => setShowCapitalModal(false)} className="text-gray-400 hover:text-gray-600">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="mb-4 space-y-2">
              {bot.starting_capital != null && (
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-gray-400">Capital</span>
                  <span className="text-sm font-semibold text-gray-700 tabular-nums">${bot.starting_capital.toFixed(2)}</span>
                </div>
              )}
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-gray-400">Cash</span>
                <span className="text-lg font-bold text-gray-900 tabular-nums">${(bot.capital_balance ?? 0).toFixed(2)}</span>
              </div>
              {(() => {
                const deployed = (bot.positions || []).reduce((s, p) => s + (p.cost_usd || 0), 0);
                return deployed > 0 ? (
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs text-gray-400">In positions</span>
                    <span className="text-sm font-medium text-gray-600 tabular-nums">${deployed.toFixed(2)}</span>
                  </div>
                ) : null;
              })()}
              {(() => {
                const totalPnl = (bot.total_profit_usd || 0) + (bot.open_unrealized_pnl || 0);
                return totalPnl !== 0 ? (
                  <div className="flex items-baseline justify-between pt-1 border-t border-gray-100">
                    <span className="text-xs text-gray-400">P&L</span>
                    <span className={`text-sm font-bold tabular-nums ${totalPnl > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      {totalPnl >= 0 ? '+' : ''}${Math.abs(totalPnl).toFixed(2)}
                    </span>
                  </div>
                ) : null;
              })()}
            </div>
            <div className="flex items-center gap-2 mb-4">
              <div className="relative flex-1">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">$</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  value={capitalInput}
                  onChange={(e) => setCapitalInput(e.target.value)}
                  autoFocus
                  className="w-full pl-7 pr-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 tabular-nums"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleCapitalAdjust('add')}
                disabled={capitalAdjusting || !capitalInput}
                className="flex-1 py-2 rounded-lg text-sm font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-100 disabled:opacity-40 transition-colors"
              >
                Deposit
              </button>
              <button
                onClick={() => handleCapitalAdjust('withdraw')}
                disabled={capitalAdjusting || !capitalInput}
                className="flex-1 py-2 rounded-lg text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 border border-red-100 disabled:opacity-40 transition-colors"
              >
                Withdraw
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
