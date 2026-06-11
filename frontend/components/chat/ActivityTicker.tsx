'use client';

import React from 'react';
import type { ToolCallStatus } from '@/lib/types';

// ═══════════════════════════════════════════════════════════════════════════
// ActivityTicker — the "evaporating log" shown while the agent is working.
//
// The current action renders as light shimmering text with a live dot; the
// previous few actions sit above it at decreasing opacity, so finished work
// visually evaporates as the agent moves on. Tapping anywhere expands the
// full step list (handled by ToolCallSummary).
// ═══════════════════════════════════════════════════════════════════════════

interface ActivityTickerProps {
  /** All non-special tools (main agent + sub-agent children) in insertion order */
  tools: ToolCallStatus[];
  elapsedLabel?: string;
  estimateLabel?: string;
  /** Shown while the model is thinking before/between tools */
  thinkingLabel?: string;
  onExpand?: () => void;
}

const VERBS: Record<string, string> = {
  bash: 'Running code',
  execute_code: 'Running code',
  run_python: 'Running code',
  web_search: 'Searching the web',
  news_search: 'Scanning the news',
  scrape_url: 'Reading',
  write_chat_file: 'Writing',
  read_chat_file: 'Reading',
  replace_in_chat_file: 'Editing',
  get_portfolio: 'Fetching your portfolio',
  get_brokerage_status: 'Checking your brokerage',
  get_fmp_data: 'Pulling market data',
  build_custom_etf: 'Building your ETF',
  connect_brokerage: 'Connecting your brokerage',
  delegate: 'Briefing a sub-agent',
  finish_execution: 'Wrapping up',
  get_reddit_trending_stocks: 'Checking Reddit chatter',
  get_reddit_ticker_sentiment: 'Reading Reddit sentiment',
};

function verbFor(toolName: string): string {
  if (VERBS[toolName]) return VERBS[toolName];
  const words = toolName.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Pull the most human-meaningful detail out of a tool call's arguments. */
function detailFor(t: ToolCallStatus): string | null {
  const a = t.arguments || {};
  if (typeof a.query === 'string' && a.query) {
    return `“${truncate(a.query, 64)}”`;
  }
  const filename: string | undefined = a.filename || a.params?.filename;
  if (typeof filename === 'string' && filename) {
    return filename.split('/').pop() || filename;
  }
  if (typeof a.url === 'string' && a.url) {
    return truncate(a.url.replace(/^https?:\/\/(www\.)?/, ''), 56);
  }
  if (t.tool_name === 'delegate') {
    const task = (a.task_id as string) || t.task_id;
    if (task) return task;
  }
  if (typeof a.symbol === 'string' && a.symbol) return a.symbol.toUpperCase();
  return null;
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s;
}

interface ActivityEntry {
  id: string;
  verb: string;
  detail: string | null;
  isError: boolean;
}

function toEntry(t: ToolCallStatus): ActivityEntry {
  // The model narrates its own calls via the injected `intent` argument
  // (see backend modules/tools/models.py). Prefer that; fall back to a
  // label derived from the tool name + arguments.
  const intent = typeof t.arguments?.intent === 'string' ? t.arguments.intent.trim() : '';
  const isActive = t.status === 'detected' || t.status === 'calling';
  // While running, append the live sub-step from inside the tool
  // ("Starting sandbox…") if one has been reported.
  const subStep = isActive && t.statusMessage && t.statusMessage !== t.tool_name
    ? truncate(t.statusMessage, 48)
    : null;
  return {
    id: t.tool_call_id,
    verb: intent ? truncate(intent, 72) : verbFor(t.tool_name),
    detail: intent ? subStep : (detailFor(t) ?? subStep),
    isError: t.status === 'error' || !!t.error,
  };
}

// Opacity of trail rows by distance from the current action (1 = most recent)
const TRAIL_OPACITY = [0.55, 0.3, 0.14];

export default function ActivityTicker({
  tools,
  elapsedLabel,
  estimateLabel,
  thinkingLabel = 'Thinking…',
  onExpand,
}: ActivityTickerProps) {
  // The current action is the last still-running tool; if everything has
  // finished, the model is deciding its next move → show "Thinking…".
  const activeIdx = tools.map(t => t.status === 'detected' || t.status === 'calling').lastIndexOf(true);
  const current = activeIdx >= 0 ? toEntry(tools[activeIdx]) : null;

  const settled = tools
    .filter((t, i) => i !== activeIdx && (t.status === 'completed' || t.status === 'error'))
    .map(toEntry);
  const trail = settled.slice(-TRAIL_OPACITY.length);

  const currentLabel = current
    ? current.detail ? `${current.verb} ${current.detail}` : `${current.verb}…`
    : thinkingLabel;

  return (
    <div
      onClick={onExpand}
      className="group cursor-pointer select-none py-1 -mx-1 px-1 rounded-lg transition-colors hover:bg-stone-50"
      role="button"
      aria-label="Show all steps"
    >
      <div className="flex flex-col gap-[5px]">
        {/* Evaporating trail of finished actions */}
        {trail.map((e, i) => (
          <div
            key={e.id}
            style={{ opacity: TRAIL_OPACITY[trail.length - 1 - i] }}
            className="flex items-center gap-2 min-w-0 transition-opacity duration-700 ease-out"
          >
            <span className="w-3 flex justify-center flex-shrink-0">
              {e.isError ? (
                <svg className="w-3 h-3 text-red-400" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-3 h-3 text-emerald-500" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              )}
            </span>
            <span className="text-[13px] leading-5 text-stone-500 truncate min-w-0">
              {e.verb}
              {e.detail && <span className="text-stone-400"> · {e.detail}</span>}
            </span>
          </div>
        ))}

        {/* Current action — live dot + shimmering light text */}
        <div key={current?.id ?? 'thinking'} className="flex items-center gap-2 min-w-0 animate-activity-in">
          <span className="relative w-3 h-3 flex items-center justify-center flex-shrink-0">
            <span className="absolute inset-0 rounded-full bg-emerald-400 animate-halo" />
            <span className="relative w-[7px] h-[7px] rounded-full bg-emerald-500" />
          </span>
          <span className="text-[13px] leading-5 activity-shimmer-text truncate min-w-0 flex-1">
            {currentLabel}
          </span>

          {/* Meta: estimate + elapsed + expand affordance */}
          <span className="flex items-center gap-2 flex-shrink-0 pl-2">
            {estimateLabel && (
              <span className="hidden xs:inline text-[11px] text-stone-400">{estimateLabel}</span>
            )}
            {elapsedLabel && (
              <span className="text-[11px] text-stone-400 tabular-nums">{elapsedLabel}</span>
            )}
            <svg
              className="w-3.5 h-3.5 text-stone-300 group-hover:text-stone-400 transition-colors"
              fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
            >
              <path d="M9 5l7 7-7 7" />
            </svg>
          </span>
        </div>
      </div>
    </div>
  );
}
