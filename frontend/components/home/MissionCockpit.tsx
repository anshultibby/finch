'use client';

/**
 * MissionCockpit — the goal-oriented home. Reads the user's active goal and
 * frames the app around it: a dark "mission control" band up top (the one bold
 * surface), then an Ask-Finch entry and quick jumps into the rest of the app.
 *
 * The band adapts to the goal kind — a scoreboard for `number`, a calmer,
 * scoreboard-free framing for grow / income / protect (so a "just watch my
 * portfolio" user never gets a pace bar they didn't ask for).
 *
 * v1 keeps it honest: no fabricated progress. Live pace/positions get wired in
 * once brokerage data flows through here.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { ArrowRight, LineChart, Bot, Wrench, Sparkles } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { goalApi, type Goal } from '@/lib/api';

const money = (n?: number | null) => (n == null ? '' : `$${n.toLocaleString('en-US')}`);

function daysBetween(fromISO: string, toISO?: string | null): number | null {
  if (!toISO) return null;
  const a = new Date(fromISO).getTime();
  const b = new Date(toISO).getTime();
  return Math.max(0, Math.round((b - a) / 86_400_000));
}

function bandCopy(goal: Goal): { eyebrow: string; title: string; tag: string; scoreboard: boolean } {
  const riskWord = goal.risk == null ? '' : goal.risk <= 3 ? 'careful' : goal.risk <= 7 ? 'balanced' : 'full send';
  const assets = `stocks${goal.options_enabled ? ' + options' : ''}`;
  switch (goal.kind) {
    case 'number':
      return {
        eyebrow: 'Your mission',
        title: goal.title || `Make ${money(goal.target_amount)}`,
        tag: [`target ${money(goal.target_amount)}`, assets, riskWord].filter(Boolean).join(' · '),
        scoreboard: true,
      };
    case 'grow':
      return {
        eyebrow: 'The long game',
        title: goal.title || `Grow steadily over ${goal.horizon_years ?? 10} years`,
        tag: [`${goal.horizon_years ?? 10}-year horizon`, goal.monthly_contribution ? `${money(goal.monthly_contribution)}/mo` : '', riskWord].filter(Boolean).join(' · '),
        scoreboard: false,
      };
    case 'income':
      return {
        eyebrow: 'Cash flow',
        title: goal.title || `Generate ${money(goal.monthly_income)}/mo`,
        tag: [`${money(goal.monthly_income)}/mo target`, assets, riskWord].filter(Boolean).join(' · '),
        scoreboard: false,
      };
    case 'protect':
    default:
      return {
        eyebrow: 'On watch',
        title: goal.title || 'Watch & protect my portfolio',
        tag: 'monitoring — no scoreboard, just a heads-up when it matters',
        scoreboard: false,
      };
  }
}

export default function MissionCockpit() {
  const { user } = useAuth();
  const { openChatWithPrompt, navigateTo } = useNavigation();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [ask, setAsk] = useState('');

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    goalApi.getGoal(user.id)
      .then(g => { if (!cancelled) setGoal(g); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [user]);

  const copy = useMemo(() => (goal ? bandCopy(goal) : null), [goal]);
  const totalDays = useMemo(
    () => (goal?.deadline ? daysBetween(goal.created_at?.slice(0, 10) || new Date().toISOString().slice(0, 10), goal.deadline) : null),
    [goal],
  );

  const suggestions = goal
    ? goal.kind === 'protect'
      ? ['Anything I should worry about today?', 'Summarise my risk', 'What changed overnight?']
      : ['How am I doing on my goal?', "What should I do today?", 'Find me an idea that fits']
    : ['What should I look into?'];

  const submitAsk = (text: string) => {
    if (!text.trim()) return;
    openChatWithPrompt(text.trim());
    setAsk('');
  };

  if (loading) {
    return <div className="h-full grid place-items-center text-gray-400 text-sm">Loading your mission…</div>;
  }

  return (
    <div className="min-h-full" style={{ background: 'radial-gradient(1200px 400px at 82% -12%, #f1efeb, transparent), #fafaf9' }}>
      {/* ── mission control band ── */}
      <div
        className="text-[#f5f5f4] border-b border-black"
        style={{
          background:
            'radial-gradient(680px 220px at 12% -20%, rgba(52,211,153,.14), transparent), radial-gradient(400px 200px at 92% -30%, rgba(99,102,241,.12), transparent), #0b0a08',
        }}
      >
        <div className="max-w-[1100px] mx-auto px-6 py-6">
          {copy && (
            <div className="grid gap-6 md:grid-cols-[1.6fr_1fr] items-center">
              <div>
                <div className="font-mono text-[11px] tracking-[.14em] uppercase text-stone-400 mb-2">
                  {copy.eyebrow}{copy.scoreboard && totalDays ? ` · ${totalDays}-day sprint` : ''}
                </div>
                <h1 className="text-2xl font-semibold tracking-tight leading-tight" style={{ fontFamily: 'var(--font-numeric), var(--font-body), sans-serif' }}>
                  {copy.title}
                </h1>
                <span className="inline-flex items-center gap-2 mt-3 text-xs text-stone-400 bg-[#191512] border border-white/10 px-3 py-1 rounded-full">
                  {copy.tag}
                </span>
              </div>

              {copy.scoreboard ? (
                <div>
                  <div className="flex items-baseline gap-2 mb-2" style={{ fontFamily: 'var(--font-numeric), sans-serif' }}>
                    <span className="text-3xl font-semibold tracking-tight">$0</span>
                    <span className="text-sm text-stone-400">/ {money(goal?.target_amount)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: '2%', background: 'linear-gradient(90deg,#059669,#34d399)' }} />
                  </div>
                  <div className="mt-2 text-[11px] text-stone-400">
                    Connect a brokerage and I&apos;ll track your pace toward this in real time.
                  </div>
                </div>
              ) : (
                <div className="bg-[#191512] border border-white/10 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Bot className="w-4 h-4 text-emerald-400" />
                    <span className="text-[12.5px] font-semibold">Finch</span>
                    <span className="font-mono text-[10px] tracking-wider uppercase text-stone-400">on watch</span>
                  </div>
                  <p className="text-[12.5px] text-stone-300 leading-relaxed">
                    {goal?.kind === 'protect'
                      ? "I'm watching your book and the things you flagged. You'll only hear from me when something actually needs you."
                      : "I'll keep this on track quietly and flag the moments that matter. Ask me anything below."}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── body ── */}
      <div className="max-w-[1100px] mx-auto px-6 py-7 grid gap-5 lg:grid-cols-[1.3fr_1fr] items-start">
        {/* Ask Finch */}
        <div className="finch-surface rounded-2xl border border-[color:var(--finch-border,rgba(0,0,0,.06))] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-emerald-600" />
            <h2 className="text-sm font-semibold text-gray-900">Ask Finch</h2>
          </div>
          <div className="flex items-end gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 focus-within:border-emerald-500 transition-colors">
            <textarea
              rows={1}
              value={ask}
              onChange={e => setAsk(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitAsk(ask); } }}
              placeholder="Ask about your goal, a stock, the market…"
              className="flex-1 resize-none outline-none text-sm text-gray-900 bg-transparent max-h-28 py-1"
            />
            <button
              type="button"
              onClick={() => submitAsk(ask)}
              disabled={!ask.trim()}
              className="w-8 h-8 rounded-lg bg-gray-900 text-white grid place-items-center disabled:opacity-30 hover:bg-black transition-colors"
              aria-label="Send"
            >
              ↑
            </button>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            {suggestions.map(s => (
              <button
                key={s}
                type="button"
                onClick={() => submitAsk(s)}
                className="text-xs text-gray-600 border border-gray-200 bg-stone-50 rounded-full px-3 py-1.5 hover:border-emerald-500 hover:text-emerald-700 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Quick jumps into the rest of the app */}
        <div className="grid gap-3">
          <div className="font-mono text-[11px] tracking-[.13em] uppercase text-gray-400 px-1">Jump to</div>
          <QuickTile icon={<LineChart className="w-5 h-5" />} title="Markets" sub="Indices, movers, watchlist, earnings" onClick={() => navigateTo({ type: 'home' })} />
          <QuickTile icon={<Bot className="w-5 h-5" />} title="Automations" sub="Trading jobs — caps, approvals, activity" onClick={() => navigateTo({ type: 'jobs' })} />
          <QuickTile icon={<Wrench className="w-5 h-5" />} title="Build" sub="Widgets, alerts & calendars" onClick={() => navigateTo({ type: 'widgets' })} />
        </div>
      </div>
    </div>
  );
}

function QuickTile({ icon, title, sub, onClick }: { icon: React.ReactNode; title: string; sub: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="finch-surface finch-surface-hover text-left rounded-xl border border-[color:var(--finch-border,rgba(0,0,0,.06))] p-4 flex items-center gap-3 group"
    >
      <span className="w-10 h-10 rounded-lg bg-stone-50 border border-gray-100 grid place-items-center text-emerald-700">{icon}</span>
      <span className="flex-1">
        <span className="block text-sm font-semibold text-gray-900">{title}</span>
        <span className="block text-xs text-gray-500">{sub}</span>
      </span>
      <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-gray-600 transition-colors" />
    </button>
  );
}
