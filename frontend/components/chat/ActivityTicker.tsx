'use client';

import React from 'react';
import type { ToolCallStatus } from '@/lib/types';
import type { ThoughtEntry } from '@/hooks/useChatStream';

// ═══════════════════════════════════════════════════════════════════════════
// Activity ticker building blocks.
//
// Tool calls AND reasoning fragments (thoughts) interleave chronologically via
// their shared _insertionOrder. ToolCallSummary owns the layout (anchor line +
// collapsible history); this module knows how to turn the raw stream into
// display items and renders the evaporating trail.
// ═══════════════════════════════════════════════════════════════════════════

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

/** Collapse whitespace and keep the trailing n chars — a rolling "live tail". */
export function liveTail(s: string, n: number): string {
  const flat = s.replace(/\s+/g, ' ').trim();
  return flat.length > n ? '…' + flat.slice(-n) : flat;
}

/** First non-empty line, clipped — for settled thoughts in the trail. */
function thoughtHead(s: string, n: number): string {
  const line = s.split('\n').map(l => l.trim()).find(Boolean) || '';
  return truncate(line, n);
}

export interface TickerItem {
  id: string;
  order: number;
  isThought: boolean;
  isError: boolean;
  active: boolean;
  /** Display text: intent/verb for tools, head line for thoughts */
  label: string;
  detail: string | null;
  rawThought?: string;
  tool?: ToolCallStatus;
  thought?: ThoughtEntry;
}

function toolItem(t: ToolCallStatus): TickerItem {
  const intent = typeof t.arguments?.intent === 'string' ? t.arguments.intent.trim() : '';
  const isActive = t.status === 'detected' || t.status === 'calling';
  // While running, append the live sub-step from inside the tool
  // ("Starting sandbox…") if one has been reported.
  const subStep = isActive && t.statusMessage && t.statusMessage !== t.tool_name
    ? truncate(t.statusMessage, 48)
    : null;
  return {
    id: t.tool_call_id,
    order: t._insertionOrder ?? 0,
    isThought: false,
    isError: t.status === 'error' || !!t.error,
    active: isActive,
    label: intent ? truncate(intent, 72) : verbFor(t.tool_name),
    detail: intent ? subStep : (detailFor(t) ?? subStep),
    tool: t,
  };
}

function thoughtItem(th: ThoughtEntry): TickerItem {
  return {
    id: th.id,
    order: th._insertionOrder,
    isThought: true,
    isError: false,
    active: th.live,
    label: thoughtHead(th.text, 80),
    detail: null,
    rawThought: th.text,
    thought: th,
  };
}

/** Interleave tools and thoughts chronologically. */
export function buildTickerItems(tools: ToolCallStatus[], thoughts?: ThoughtEntry[]): TickerItem[] {
  return [
    ...tools.map(toolItem),
    ...(thoughts ?? []).map(thoughtItem),
  ].sort((a, b) => a.order - b.order);
}

/** The current item is the last still-active one; the rest are history. */
export function splitCurrent(items: TickerItem[]): { current: TickerItem | null; settled: TickerItem[] } {
  const activeIdx = items.map(i => i.active).lastIndexOf(true);
  return {
    current: activeIdx >= 0 ? items[activeIdx] : null,
    settled: items.filter((it, i) => i !== activeIdx && !it.active),
  };
}

/** Shimmering anchor-line text for the in-flight item. */
export function currentLabelOf(current: TickerItem | null, fallback: string): { text: string; isThought: boolean } {
  if (!current) return { text: fallback, isThought: false };
  if (current.isThought) return { text: liveTail(current.rawThought || '', 110), isThought: true };
  return {
    text: current.detail ? `${current.label} ${current.detail}` : `${current.label}…`,
    isThought: false,
  };
}

export const SparkleIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 3l1.7 4.8L18.5 9.5l-4.8 1.7L12 16l-1.7-4.8L5.5 9.5l4.8-1.7L12 3zM19 14l.9 2.6L22.5 17.5l-2.6.9L19 21l-.9-2.6-2.6-.9 2.6-.9L19 14z" />
  </svg>
);

// Opacity of trail rows by recency (index 0 = most recent, right under the anchor)
const TRAIL_OPACITY = [0.55, 0.3, 0.14];
export const TRAIL_LENGTH = TRAIL_OPACITY.length;

/** The evaporating trail — hangs below the live anchor line like a comet
    tail: newest settled item on top at the strongest opacity, fading
    downward into the past. */
export function ActivityTrail({ items }: { items: TickerItem[] }) {
  const trail = items.slice(-TRAIL_LENGTH).reverse();
  return (
    <div className="flex flex-col gap-[5px] pt-[5px] pl-5">
      {trail.map((e, i) => (
        <div
          key={e.id}
          style={{ opacity: TRAIL_OPACITY[i] }}
          className="flex items-center gap-2 min-w-0 transition-opacity duration-700 ease-out"
        >
          <span className="w-3 flex justify-center flex-shrink-0">
            {e.isThought ? (
              <SparkleIcon className="w-3 h-3 text-stone-400" />
            ) : e.isError ? (
              <svg className="w-3 h-3 text-red-400" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-3 h-3 text-emerald-500" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            )}
          </span>
          <span className={`text-[13px] leading-5 truncate min-w-0 ${e.isThought ? 'italic text-stone-400' : 'text-stone-500'}`}>
            {e.label}
            {e.detail && <span className="text-stone-400"> · {e.detail}</span>}
          </span>
        </div>
      ))}
    </div>
  );
}
