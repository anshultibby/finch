'use client';

import React, { useState, useEffect, useRef } from 'react';
import ToolCall from './ToolCall';
import { buildTickerItems, splitCurrent, currentLabelOf, ActivityTrail, SparkleIcon } from './ActivityTicker';
import SubAgentGroup, { isLimitSkipped } from './SubAgentGroup';
import TodoChecklist from './TodoChecklist';
import type { ToolCallStatus, TodoItem } from '@/lib/types';
import type { TimeEstimate, ThoughtEntry } from '@/hooks/useChatStream';

interface ToolCallSummaryProps {
  toolCalls: ToolCallStatus[];
  /** Live reasoning fragments (streaming only), interleaved with tools by _insertionOrder */
  thoughts?: ThoughtEntry[];
  isStreaming?: boolean;
  startTime?: number | null;
  timeEstimate?: TimeEstimate | null;
  /** Live task-phase checklist (streaming only) */
  todos?: TodoItem[];
  onSelectTool?: (tool: ToolCallStatus) => void;
  onPeekAgent?: (agentId: string, chatId: string, name: string) => void;
}

// Tools that are always shown outside the collapsed summary
const ALWAYS_VISIBLE_TOOLS = new Set(['create_agent', 'place_trade']);

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return sec > 0 ? `${min}m ${sec}s` : `${min}m`;
}

function formatEstimate(seconds: number): string {
  if (seconds <= 30) return '~30s';
  if (seconds <= 60) return '~1 min';
  if (seconds <= 90) return '~1-2 min';
  const min = Math.round(seconds / 60);
  return `~${min} min`;
}

// Past-tense labels for the completed receipt line ("Searched the web, ran code")
const RECEIPT_VERBS: Record<string, string> = {
  bash: 'Ran code',
  execute_code: 'Ran code',
  run_python: 'Ran code',
  web_search: 'Searched the web',
  news_search: 'Scanned the news',
  scrape_url: 'Read pages',
  write_chat_file: 'Wrote files',
  read_chat_file: 'Read files',
  replace_in_chat_file: 'Edited files',
  get_portfolio: 'Checked your portfolio',
  get_brokerage_status: 'Checked your brokerage',
  get_fmp_data: 'Pulled market data',
  build_custom_etf: 'Built your ETF',
  connect_brokerage: 'Connected your brokerage',
  finish_execution: 'Wrapped up',
  get_reddit_trending_stocks: 'Checked Reddit chatter',
  get_reddit_ticker_sentiment: 'Read Reddit sentiment',
};

/** "Searched the web, ran code, +2 more" — what actually happened, deduped, in order. */
function receiptSummary(tools: ToolCallStatus[]): string {
  const labels: string[] = [];
  for (const t of tools) {
    if (t.tool_name === 'delegate') continue; // shown separately as "· N sub-agents"
    const label = RECEIPT_VERBS[t.tool_name]
      || t.tool_name.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
    if (!labels.includes(label)) labels.push(label);
  }
  if (labels.length === 0) return `Ran ${tools.length} step${tools.length !== 1 ? 's' : ''}`;
  const shown = labels.slice(0, 3).map((l, i) => i === 0 ? l : l.charAt(0).toLowerCase() + l.slice(1));
  const extra = labels.length - 3;
  return shown.join(', ') + (extra > 0 ? `, +${extra} more` : '');
}

export default function ToolCallSummary({
  toolCalls,
  thoughts,
  isStreaming = false,
  startTime,
  timeEstimate,
  todos,
  onSelectTool,
  onPeekAgent,
}: ToolCallSummaryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const treeRef = useRef<HTMLDivElement>(null);
  const historyOuterRef = useRef<HTMLDivElement>(null);
  const historyInnerRef = useRef<HTMLDivElement>(null);

  // Accordion with real pixel heights: a grid 0fr/1fr trick can't animate
  // between two non-zero contents (expanded tree ↔ collapsed trail), which
  // made closing snap. Track the inner content's height and transition to it.
  useEffect(() => {
    const inner = historyInnerRef.current;
    const outer = historyOuterRef.current;
    if (!inner || !outer) return;
    const sync = () => { outer.style.height = `${inner.offsetHeight}px`; };
    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(inner);
    return () => ro.disconnect();
  }, []);

  // Sort tools by insertion order, then partition into special vs regular
  // and compute status counts in a single pass
  const sortedTools = [...toolCalls].sort(
    (a, b) => (a._insertionOrder ?? 0) - (b._insertionOrder ?? 0)
  );

  const specialTools: ToolCallStatus[] = [];
  const regularTools: ToolCallStatus[] = [];   // top-level (main-agent) tools, incl. delegate parents
  const tickerTools: ToolCallStatus[] = [];    // everything the live ticker narrates, in order
  const childrenByTask = new Map<string, ToolCallStatus[]>();  // sub-agent tools keyed by task_id
  let errorCount = 0;

  for (const t of sortedTools) {
    // Sub-agent tools (emitted by `delegate`) are nested under their parent, not
    // counted as top-level steps. Group them by task_id for rendering below.
    if (t.sub_agent_id && t.task_id) {
      const arr = childrenByTask.get(t.task_id) ?? [];
      arr.push(t);
      childrenByTask.set(t.task_id, arr);
      tickerTools.push(t);
      continue;
    }
    if (ALWAYS_VISIBLE_TOOLS.has(t.tool_name)) {
      specialTools.push(t);
    } else {
      regularTools.push(t);
      tickerTools.push(t);
      if (t.status === 'error') errorCount++;
    }
  }

  // Sub-agents that actually ran (delegates not rejected by the per-chat cap).
  const subAgentCount = regularTools.filter(t => t.tool_name === 'delegate' && !isLimitSkipped(t)).length;

  /** Render a top-level tool; a `delegate` becomes a rich sub-agent card with its tools + result. */
  const renderTool = (tool: ToolCallStatus) => {
    if (tool.tool_name === 'delegate') {
      const taskId = (tool.arguments?.task_id as string) || tool.task_id || '';
      return (
        <SubAgentGroup
          key={tool.tool_call_id}
          parent={tool}
          childTools={childrenByTask.get(taskId) ?? []}
          onSelectTool={onSelectTool}
          onPeekAgent={onPeekAgent}
        />
      );
    }
    return (
      <ToolCall
        key={tool.tool_call_id}
        toolCall={tool}
        onShowOutput={() => onSelectTool?.(tool)}
        onPeekAgent={onPeekAgent}
      />
    );
  };

  // Elapsed time ticker — captures final value when streaming ends
  useEffect(() => {
    if (!startTime) {
      setElapsedSeconds(0);
      return;
    }
    if (!isStreaming) {
      // Capture final elapsed time once when streaming stops
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
      return;
    }
    const tick = () => setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [isStreaming, startTime]);

  const shouldAutoExpand = false;

  // Keep the expanded tree pinned to its newest rows while work streams in
  useEffect(() => {
    if (isExpanded && isStreaming && treeRef.current) {
      treeRef.current.scrollTop = treeRef.current.scrollHeight;
    }
  }, [isExpanded, isStreaming, toolCalls, thoughts]);

  // If there are no regular tools, just render special tools
  if (regularTools.length === 0 && specialTools.length === 0) return null;

  if (regularTools.length === 0) {
    return (
      <div className="flex flex-col gap-1">
        {specialTools.map(tool => (
          <ToolCall
            key={tool.tool_call_id}
            toolCall={tool}
            onShowOutput={() => onSelectTool?.(tool)}
            onPeekAgent={onPeekAgent}
          />
        ))}
      </div>
    );
  }

  // Simple time-based countdown from initial estimate
  let estimateLabel = '';
  if (isStreaming && timeEstimate) {
    const remaining = Math.max(0, timeEstimate.seconds - elapsedSeconds);
    if (remaining > 0) {
      estimateLabel = `${formatEstimate(remaining)} left`;
    }
  }

  const expanded = isExpanded || shouldAutoExpand;
  const elapsedLabel = elapsedSeconds > 0 ? formatDuration(elapsedSeconds) : undefined;

  // Interleaved chronology of tools + thoughts (ticker items)
  const items = buildTickerItems(tickerTools, isStreaming ? thoughts : undefined);
  const { current, settled } = splitCurrent(items);
  const anchorLive = currentLabelOf(
    current,
    tickerTools.length === 0 && timeEstimate?.description ? timeEstimate.description : 'Thinking…'
  );

  // Expanded tree: top-level tools + thoughts in order (sub-agent tools render
  // nested inside their delegate's SubAgentGroup, not as top-level rows).
  const treeItems = ([
    ...regularTools.map(t => ({ order: t._insertionOrder ?? 0, tool: t, thought: null as ThoughtEntry | null })),
    ...(isStreaming ? (thoughts ?? []) : []).map(th => ({ order: th._insertionOrder, tool: null as ToolCallStatus | null, thought: th })),
  ]).sort((a, b) => a.order - b.order);

  return (
    <div className="flex flex-col">
      {/* Special tools always visible */}
      {specialTools.map(tool => (
        <ToolCall
          key={tool.tool_call_id}
          toolCall={tool}
          onShowOutput={() => onSelectTool?.(tool)}
          onPeekAgent={onPeekAgent}
        />
      ))}

      {/* Anchor line — always present, identical position collapsed/expanded,
          streaming or done. Streaming: live dot + current action shimmering.
          Done: receipt of what happened. */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="group flex items-center gap-2 py-1 -mx-1 px-1 rounded-lg cursor-pointer select-none transition-colors hover:bg-stone-50 min-w-0"
        role="button"
        aria-label={expanded ? 'Hide steps' : 'Show all steps'}
      >
        <span className="w-3 flex justify-center flex-shrink-0">
          {isStreaming ? (
            <span className="relative w-3 h-3 flex items-center justify-center">
              <span className="absolute inset-0 rounded-full bg-emerald-400 animate-halo" />
              <span className="relative w-[7px] h-[7px] rounded-full bg-emerald-500 block" />
            </span>
          ) : errorCount > 0 ? (
            <svg className="w-3.5 h-3.5 text-red-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <svg className="w-3 h-3 text-emerald-500" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          )}
        </span>

        {isStreaming ? (
          <span className={`flex-1 min-w-0 text-[13px] leading-5 activity-shimmer-text truncate ${anchorLive.isThought ? 'italic' : ''}`}>
            {anchorLive.text}
          </span>
        ) : (
          <span className="flex-1 min-w-0 text-[13px] leading-5 text-stone-500 truncate">
            {receiptSummary(regularTools)}
            {subAgentCount > 0 && (
              <span className="text-indigo-400/80">
                {' '}· {subAgentCount} sub-agent{subAgentCount !== 1 ? 's' : ''}
              </span>
            )}
            {errorCount > 0 && (
              <span className="text-red-400">
                {' '}· {errorCount} failed
              </span>
            )}
          </span>
        )}

        <span className="flex items-center gap-2 flex-shrink-0 pl-2">
          {isStreaming && estimateLabel && (
            <span className="hidden xs:inline text-[11px] text-stone-400">{estimateLabel}</span>
          )}
          {elapsedLabel && startTime && (
            <span className="text-[11px] text-stone-400 tabular-nums">{elapsedLabel}</span>
          )}
          <svg
            className={`w-3.5 h-3.5 text-stone-300 group-hover:text-stone-400 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
            fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
          >
            <path d="M9 5l7 7-7 7" />
          </svg>
        </span>
      </div>

      {/* History region — unrolls BELOW the anchor line, so the line the user
          taps never moves. Collapsed while streaming: evaporating trail
          (newest on top, fading downward). Expanded: the full thought/tool
          tree. Height is measured and transitioned so open, close, AND
          mid-stream growth all animate smoothly. */}
      <div
        ref={historyOuterRef}
        className="overflow-hidden transition-[height] duration-300 ease-out"
        style={{ height: 0 }}
      >
        <div ref={historyInnerRef}>
          {expanded ? (
            <div
              ref={treeRef}
              className="flex flex-col gap-1 pl-4 pr-1 pb-1 pt-1 max-h-80 overflow-y-auto chat-scrollbar"
            >
              {treeItems.map(item =>
                item.tool ? renderTool(item.tool) : (
                  <div key={item.thought!.id} className="flex gap-2 py-0.5 px-1 min-w-0">
                    <SparkleIcon className="w-3 h-3 mt-1 flex-shrink-0 text-stone-300" />
                    <p className="text-xs italic leading-5 text-stone-400 line-clamp-3 whitespace-pre-line min-w-0">
                      {item.thought!.text.length > 400
                        ? item.thought!.text.slice(0, 400).trimEnd() + '…'
                        : item.thought!.text}
                    </p>
                  </div>
                )
              )}
            </div>
          ) : isStreaming && settled.length > 0 ? (
            <ActivityTrail items={settled} />
          ) : null}
        </div>
      </div>

      {/* Live task-phase checklist — only while working; the receipt line covers history */}
      {isStreaming && todos && todos.length > 0 && <TodoChecklist items={todos} />}
    </div>
  );
}
