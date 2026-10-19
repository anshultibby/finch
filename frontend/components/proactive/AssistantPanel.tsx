'use client';

import React, { useEffect, useState } from 'react';
import { ArrowUpRight, ArrowUp, Sparkles, ListChecks, LayoutGrid, Brain, ChevronRight } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { ideasApi, watchlistApi, type TradeIdea } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';
import { ui } from './shared';

// The assistant never opens on a blank page: Finch's own ideas first, then
// prompts shaped around the user's stocks. Conversation history stays in the
// sidebar on web (it's the drawer's job on mobile — see app/(tabs)/chat/index.tsx).

function prompts(sym?: string) {
  const s = sym || 'NVDA';
  return [
    'What changed in my portfolio this week, and what should I do about it?',
    `Give me a bull vs. bear case on ${s} — and pick a side`,
    `Help me write my thesis on ${s} — why I own it and what would make me wrong`,
    'Review my recent trades and tell me what I keep getting wrong',
    'Show me strategies that fit my goal, and help me adopt one',
  ];
}

export default function AssistantPanel() {
  const { user } = useAuth();
  const { openChatWithPrompt, startNewChat, navigateTo } = useNavigation();
  const [ideas, setIdeas] = useState<TradeIdea[]>([]);
  const [topSymbol, setTopSymbol] = useState<string>();
  const [ask, setAsk] = useState('');

  useEffect(() => {
    if (!user) return;
    ideasApi.list(20).then(d => setIdeas((d.ideas || []).filter(i => i.status === 'proposed' && i.outcome === 'pending'))).catch(() => {});
    watchlistApi.getWatchlist(user.id).then(d => {
      const first = (d?.symbols || d?.watchlist || [])[0];
      setTopSymbol(first ? (typeof first === 'string' ? first : first.symbol) : undefined);
    }).catch(() => {});
  }, [user]);

  const submit = () => { const q = ask.trim(); if (q) { openChatWithPrompt(q); setAsk(''); } };

  return (
    <div className="h-full overflow-y-auto bg-[#fafaf9]">
      <div className={ui.page}>
        <PageHeader title="Ask Finch" subtitle="Your analyst — it takes a stance"
          actions={<button onClick={startNewChat} className="px-3.5 py-2 rounded-xl bg-gray-900 text-white text-[13px] font-semibold hover:bg-gray-800">New chat</button>} />

        <div className="flex items-center gap-2 bg-white border border-stone-200 rounded-2xl pl-4 pr-2 py-2 shadow-sm focus-within:border-emerald-300">
          <Sparkles className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <input autoFocus value={ask} onChange={e => setAsk(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder="Ask about any stock, your portfolio, or the market…" className="flex-1 bg-transparent text-[15px] py-1.5 focus:outline-none" />
          <button onClick={submit} disabled={!ask.trim()} aria-label="Send"
            className={`w-8 h-8 rounded-full flex items-center justify-center ${ask.trim() ? 'bg-emerald-600 text-white' : 'bg-stone-200 text-white'}`}>
            <ArrowUp className="w-4 h-4" strokeWidth={2.6} />
          </button>
        </div>

        {ideas.length > 0 && (
          <>
            <div className={ui.section}>Ideas from Finch</div>
            <div className={`${ui.card} overflow-hidden`}>
              {ideas.slice(0, 4).map(i => (
                <button key={i.id} className={ui.row}
                  onClick={() => openChatWithPrompt(`Walk me through your ${i.direction} idea on ${i.symbol}: "${i.catalyst_summary}". What's the thesis, the bear case, and how would you size it for me?`, `${i.symbol} idea`)}>
                  <div className="flex-1 min-w-0">
                    <div className="text-[14.5px] font-bold text-gray-900">
                      <span className={i.direction === 'long' ? 'text-emerald-600' : 'text-red-500'}>{i.direction === 'long' ? '▲ ' : '▼ '}</span>{i.symbol}
                    </div>
                    <div className="text-[13px] text-stone-500 line-clamp-2">{i.catalyst_summary}</div>
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-stone-400" />
                </button>
              ))}
            </div>
          </>
        )}

        <div className={ui.section}>Try asking</div>
        <div className={`${ui.card} overflow-hidden`}>
          {prompts(topSymbol).map(p => (
            <button key={p} onClick={() => openChatWithPrompt(p)} className={ui.row}>
              <span className="flex-1 text-[14px] text-gray-900">{p}</span>
              <ArrowUpRight className="w-4 h-4 text-stone-400" />
            </button>
          ))}
        </div>

        <div className={`${ui.card} overflow-hidden mt-6`}>
          <button onClick={() => navigateTo({ type: 'tasks' })} className={ui.row}>
            <ListChecks className="w-4 h-4 text-stone-500" /><span className="flex-1 text-[14px] font-medium text-gray-900">Finch&apos;s tasks</span><ChevronRight className="w-4 h-4 text-stone-300" />
          </button>
          <button onClick={() => navigateTo({ type: 'widgets' })} className={ui.row}>
            <LayoutGrid className="w-4 h-4 text-stone-500" /><span className="flex-1 text-[14px] font-medium text-gray-900">Boards Finch built</span><ChevronRight className="w-4 h-4 text-stone-300" />
          </button>
          <button onClick={() => navigateTo({ type: 'memory-store' })} className={ui.row}>
            <Brain className="w-4 h-4 text-stone-500" /><span className="flex-1 text-[14px] font-medium text-gray-900">What Finch remembers about you</span><ChevronRight className="w-4 h-4 text-stone-300" />
          </button>
        </div>
      </div>
    </div>
  );
}
