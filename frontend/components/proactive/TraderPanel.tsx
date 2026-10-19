'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { ShieldCheck, Pause, Play, Loader2, ChevronRight } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import {
  ideasApi, jobsApi, accountApi, activityApi,
  type TradeIdea, type IdeaScorecard, type ScheduledJob, type AgentEvent,
} from '@/lib/api';
import { usePendingTrades, invalidatePendingTrades } from '@/hooks/usePendingTrades';
import PageHeader from '@/components/ui/PageHeader';
import ApprovalCard from '@/components/activity/ApprovalCard';
import AgentTabView from '@/components/home/AgentTabView';
import { fmtUsd, fmtPct, ui } from './shared';

// The trust surface. Nothing executes without the user: approvals are
// hold-to-confirm, Finch's calls are graded against SPY whether or not they
// were taken, and one switch pauses every automation.
// Mirrors frontend-mobile/app/trader.tsx.

export default function TraderPanel() {
  const { user } = useAuth();
  const { openStock, openChatWithPrompt, loadChat } = useNavigation();
  const { trades: pending, refresh: refreshPending } = usePendingTrades(!!user);
  const [decided, setDecided] = useState<Record<string, string>>({});
  const [ideas, setIdeas] = useState<TradeIdea[]>([]);
  const [score, setScore] = useState<IdeaScorecard | null>(null);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [requireApproval, setRequireApproval] = useState<boolean | null>(null);
  const [toggling, setToggling] = useState(false);

  const load = useCallback(async () => {
    if (!user) return;
    await Promise.all([
      ideasApi.list(50).then(d => { setIdeas(d.ideas || []); setScore(d.scorecard); }).catch(() => {}),
      jobsApi.list().then(d => setJobs(d.jobs || [])).catch(() => {}),
      activityApi.getFeed(15).then(d => setEvents(d.events || [])).catch(() => {}),
      accountApi.getPreferences(user.id).then(p => setRequireApproval(p.require_trade_approval)).catch(() => {}),
    ]);
  }, [user]);

  useEffect(() => { load(); }, [load]);

  if (!user) return null;

  const live = pending.filter(t => !decided[t.id]);
  const openIdeas = ideas.filter(i => i.status === 'proposed' && i.outcome === 'pending');
  const running = jobs.filter(j => j.status === 'pending' || j.status === 'running');
  const paused = jobs.filter(j => j.status === 'paused');

  const toggleAll = async () => {
    const pausing = running.length > 0;
    if (pausing && !window.confirm(`Pause all ${running.length} automations, including any that can propose trades? You can resume anytime.`)) return;
    setToggling(true);
    try {
      await (pausing ? jobsApi.pauseAll() : jobsApi.resumeAll());
      await load();
    } finally {
      setToggling(false);
    }
  };

  const decideIdea = async (idea: TradeIdea, approve: boolean) => {
    await ideasApi.decide(idea.id, approve, approve ? 'manual' : undefined).catch(() => {});
    load();
  };

  return (
    <div className="h-full overflow-y-auto bg-[#fafaf9]">
      <div className={ui.page}>
        <PageHeader title="Trader" subtitle={requireApproval === false ? 'Unattended trading is on' : 'Nothing executes without you'} />

        {/* Kill switch */}
        <div className={`${ui.card} flex items-center gap-3.5 p-4`}>
          <ShieldCheck className={`w-5 h-5 ${running.length > 0 ? 'text-emerald-600' : 'text-stone-400'}`} />
          <div className="flex-1">
            <div className="text-[15px] font-bold text-gray-900">
              {running.length > 0 ? `${running.length} automation${running.length > 1 ? 's' : ''} running` : paused.length > 0 ? 'Everything paused' : 'No automations yet'}
            </div>
            <button onClick={() => { window.location.href = '/settings'; }}
              className={`text-[12.5px] hover:underline ${requireApproval === false ? 'text-red-600' : 'text-stone-500'}`}>
              {requireApproval === false ? 'Approvals are OFF — Finch can trade without asking' : 'Approval required for every trade'}
            </button>
          </div>
          {(running.length > 0 || paused.length > 0) && (
            <button onClick={toggleAll} disabled={toggling}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-full text-[13px] font-bold ${running.length > 0 ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'}`}>
              {toggling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : running.length > 0 ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {running.length > 0 ? 'Pause all' : 'Resume'}
            </button>
          )}
        </div>

        {/* Approvals */}
        <div className={ui.section}>Waiting on you</div>
        {live.length === 0 ? (
          <p className="text-[14px] text-stone-500">No trades waiting. When Finch wants to act, it&apos;ll ask here first — and ping you.</p>
        ) : (
          <div className="space-y-3">
            {live.map(t => (
              <ApprovalCard key={t.id} trade={t} onDecided={(id, status) => {
                setDecided(d => ({ ...d, [id]: status }));
                invalidatePendingTrades();
                refreshPending();
              }} />
            ))}
          </div>
        )}

        {/* Finch's calls + scorecard */}
        <div className={ui.section}>Finch&apos;s calls</div>
        {score && score.scored > 0 && (
          <div className={`${ui.card} grid grid-cols-3 p-4 mb-3`}>
            <Stat label="Hit rate" value={score.hit_rate != null ? `${Math.round(score.hit_rate * 100)}%` : '—'} />
            <Stat label="Avg vs S&P 500" value={fmtPct(score.avg_alpha_pct)} tone={(score.avg_alpha_pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-500'} />
            <Stat label="Graded" value={String(score.scored)} />
          </div>
        )}
        {openIdeas.length === 0 ? (
          <p className="text-[14px] text-stone-500">No open calls. Finch proposes ideas when a catalyst lines up with your goal — every one is graded against the S&amp;P 500, taken or not.</p>
        ) : (
          <div className={`${ui.card} overflow-hidden`}>
            {openIdeas.map(i => (
              <div key={i.id} className="px-4 py-3.5 border-t first:border-t-0 border-stone-100">
                <div className="flex items-center gap-2">
                  <span className={i.direction === 'long' ? 'text-emerald-600' : 'text-red-500'}>{i.direction === 'long' ? '▲' : '▼'}</span>
                  <button onClick={() => openStock(i.symbol)} className="text-[14.5px] font-bold text-gray-900 hover:underline">{i.symbol}</button>
                  <span className="text-[12px] text-stone-400">conviction {i.conviction}/5 · {i.horizon_days}d</span>
                </div>
                <div className="text-[13.5px] text-stone-700 mt-1">{i.catalyst_summary}</div>
                <div className="text-[12px] text-stone-400 mt-1 tabular-nums">Entry {fmtUsd(i.entry_ref)} · Target {fmtUsd(i.target)} · Stop {fmtUsd(i.stop)}</div>
                <div className="flex gap-2 mt-2.5">
                  <button onClick={() => openChatWithPrompt(`Walk me through your ${i.direction} idea on ${i.symbol}: "${i.catalyst_summary}". What's the thesis, the bear case, and how would you size it for me?`, `${i.symbol} idea`)}
                    className="px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700 text-[12.5px] font-bold hover:bg-emerald-100">Discuss</button>
                  <button onClick={() => decideIdea(i, true)} className="px-3 py-1.5 rounded-full border border-stone-200 text-[12.5px] font-semibold text-stone-700 hover:bg-stone-50">I&apos;ll place it</button>
                  <button onClick={() => decideIdea(i, false)} className="px-3 py-1.5 rounded-full text-[12.5px] font-semibold text-stone-500 hover:text-stone-800">Pass</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* The agent's own account */}
        <div className={ui.section}>Agent account</div>
        <AgentTabView userId={user.id} onStockClick={s => openStock(s)} />

        {/* Ledger */}
        {events.length > 0 && (
          <>
            <div className={ui.section}>Recent activity</div>
            <div className={`${ui.card} overflow-hidden`}>
              {events.slice(0, 10).map(e => {
                const chatId = e.data?.chat_id as string | undefined;
                const symbol = e.data?.symbol as string | undefined;
                return (
                  <button key={e.id} onClick={() => (chatId ? loadChat(chatId) : symbol ? openStock(symbol) : undefined)} className={ui.row}>
                    <div className="flex-1 min-w-0">
                      <div className="text-[13.5px] font-semibold text-gray-900 truncate">{e.title}</div>
                      {e.body && <div className="text-[12.5px] text-stone-500 truncate">{e.body}</div>}
                    </div>
                    <span className="text-[11.5px] text-stone-400 flex-shrink-0">{new Date(e.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                    {(symbol || chatId) && <ChevronRight className="w-4 h-4 text-stone-300" />}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <div className="text-[11.5px] font-medium text-stone-500">{label}</div>
      <div className={`text-[19px] font-bold tabular-nums ${tone || 'text-gray-900'}`}>{value}</div>
    </div>
  );
}
